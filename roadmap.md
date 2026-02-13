# LED Matrix Web Control - Implementation Options

## Current State

Two mature codebases exist:

- **led-matrix** (Python): Background service with system monitoring, plugin architecture, config management, systemd integration
- **dotmatrixtool** (Web): Browser-based drawing tool with Web Serial API, import/export JSON, direct hardware communication

## Hardware Configuration

**Framework 16 LED Matrix Panels:**

- Each panel: 9 columns (width) × 34 rows (height) 
- Typical setup: 2 panels (left and right)
- Total logical display when both present: 18 wide × 34 tall
- Physical placement: Can flank keyboard OR sit side-by-side
- Backend always treats as 2 independent 9×34 panels
- Frontend can show "unified view" for drawing alignment (UX only)

**Quadrant Layout (when 2 panels present):**

- Top-Left: 9×17 (top half of left panel)
- Bottom-Left: 9×17 (bottom half of left panel)
- Top-Right: 9×17 (top half of right panel)
- Bottom-Right: 9×17 (bottom half of right panel)

**Single Panel Setup:**

- Only 2 sections available: top (9×17) and bottom (9×17)

## Option A: Hybrid Architecture (Python Backend + React Frontend)

### Architecture Overview

Python service runs continuously as systemd service. React web app provides control interface and communicates via API.

### Components to Build

#### Backend Development (Python)

1. **FastAPI Server Layer**

- REST API endpoints for control operations
  - WebSocket endpoint for real-time state updates
  - Serve React frontend as static files
  - CORS configuration for development

1. **Mode Management System** (Critical - see problem statement)

- ModeController class with state machine (AUTO | MANUAL | MIXED)
  - Hardware access locking (threading.Lock or asyncio.Lock)
  - Transition handlers (pause auto mode, resume auto mode)
  - Watchdog timer for manual mode timeout
  - Per-quadrant locking for MIXED mode (optional)

1. **API Endpoints**

- POST /mode/manual - Request manual control
  - POST /mode/auto - Release manual control
  - GET /mode/status - Current mode and locked quadrants
  - POST /manual/draw/left - Send left panel pattern (9×34 array)
  - POST /manual/draw/right - Send right panel pattern (9×34 array)
  - POST /manual/quadrant - Control specific quadrant
  - GET /config - Read current config.yaml
  - PUT /config - Update config.yaml
  - GET /apps/list - Available apps and plugins
  - GET /metrics - Current system metrics
  - GET /panels - Detect connected panels (1 or 2)
  - WebSocket /ws - Live LED matrix state

1. **Modified Auto Mode Loop**

- Check mode_controller.current_mode before drawing
  - Pause app cycling when mode == MANUAL
  - Resume from correct position when returning to AUTO

1. **Hardware Access Serialization**

- Modify DrawingThread to use mode_controller.hardware_lock
  - Single point of hardware access
  - Queue management during mode transitions

#### Frontend Development (React)

1. **Project Setup**

- Vite + React + TypeScript
  - API client library (axios or fetch)
  - WebSocket client
  - State management (Zustand or React Context)

1. **Mode Control Interface**

- Toggle between Auto/Manual modes
  - Visual indicator of current mode
  - Timeout countdown when in manual mode
  - Warning dialog before switching modes

1. **Auto Mode Configuration Panel**

- Quadrant selector (4 quadrants: top-left, top-right, bottom-left, bottom-right)
  - App dropdown per quadrant (populated from /apps/list)
  - Duration slider per app
  - Animation toggle per app
  - Add/remove apps for time-multiplexing
  - Save/load config.yaml

1. **Manual Control Interface**

- Quadrant selector for targeted control
  - App selector with live application
  - Quick preset buttons

1. **Free Draw Canvas** (from dotmatrixtool)

- Refactor dotmatrixtool app.js to React component
  - Two 9×34 LED grid components (left and right panels)
  - Optional "unified view" toggle - displays both as single 18×34 canvas for alignment (UX only)
  - Mouse/touch drawing (left click draw, ctrl+click erase)
  - Brightness slider
  - Color/grayscale picker
  - Export to snapshot_files/
  - Send directly to backend API (not Web Serial)
  - Always exports/sends as two separate panel arrays (left 9×34, right 9×34)

1. **System Metrics Dashboard**

- Real-time display via WebSocket
  - CPU utilization graph
  - Memory usage
  - Disk I/O rates
  - Network traffic
  - Temperature sensors
  - Fan speeds

1. **System Alerts Configuration** (from notification API design)

- Define alert triggers
  - Route alerts to system tray OR LED matrix
  - Priority levels
  - Icon/pattern selection per alert type

1. **Live Preview**

- Visual representation of LED matrix
  - Shows left panel (9×34) and right panel (9×34) if present
  - Optional unified view (18×34 when both panels present)
  - Updates via WebSocket from Python backend
  - Shows actual hardware state

### Deployment

- Python service runs as systemd unit
- React app built to static files
- FastAPI serves static files at /
- Access via <http://localhost:8000>
- Optional: nginx reverse proxy for production

### Advantages

- Leverages existing Python codebase (system monitoring, plugins, hardware control)
- Python's psutil provides accurate system metrics
- Service runs independently of browser
- Systemd integration for auto-start
- NixOS flake already exists
- Can reuse dotmatrixtool canvas component

### Disadvantages

- Need to build FastAPI layer
- Need to refactor dotmatrixtool jQuery to React
- More complexity (two languages)

## Option B: Enhanced Python Service + Embedded dotmatrixtool

### Architecture Overview

Python service runs continuously. Serve dotmatrixtool (mostly as-is) with minimal modifications to communicate with Python backend.

### Components to Build

#### Backend Development (Python)

1. **FastAPI Server Layer**

- Same as Option A
  - Serve dotmatrixtool HTML/JS/CSS as static files

1. **Mode Management System**

- Same as Option A
  - Critical for preventing conflicts

1. **API Endpoints**

- POST /mode/manual - Request manual control
  - POST /mode/auto - Release manual control
  - POST /manual/draw - Receive pattern from dotmatrixtool
  - POST /config/quadrant - Configure quadrant app
  - GET /config - Current configuration
  - GET /metrics - System metrics
  - WebSocket /ws - Live state updates

1. **Modified Auto Mode Loop**

- Same as Option A

1. **Hardware Access Serialization**

- Same as Option A

#### Frontend Development (Minimal Modifications)

1. **Modify dotmatrixtool app.js**

- Add mode selector UI (auto/manual)
  - Replace Web Serial API calls with fetch to Python API
  - Add quadrant configuration form (4 quadrants across both panels)
  - Add app selector dropdowns per quadrant
  - Keep existing drawing canvas (left 9×34 and right 9×34)
  - Add optional "unified view" toggle for drawing alignment (displays as 18×34)
  - Always send data as two separate panel arrays to backend

1. **Add Control Interface (vanilla JS or minimal framework)**

- Mode toggle button (Auto/Manual)
  - Quadrant configuration panel (4 quadrants: TL, BL, TR, BR)
  - App selector per quadrant with duration and animation settings
  - Panel detection display (shows 1 or 2 panels connected)
  - Save config button

1. **System Metrics Display** (optional)

- Basic dashboard using Chart.js or similar
  - WebSocket connection to Python backend

### Deployment

- Python service runs as systemd unit
- Serves dotmatrixtool files at /
- Access via <http://localhost:8000>

### Advantages

- Less frontend development (reuse dotmatrixtool mostly as-is)
- No need to refactor jQuery to React
- Simpler tech stack
- Faster to implement
- Still leverages Python backend strengths

### Disadvantages

- Limited UI/UX capabilities (jQuery vs React)
- Harder to build complex configuration interface
- Less maintainable frontend code
- System alerts configuration would be basic

## Comparison Matrix

### Development Effort

- **Option A**: Higher (full React app, refactor dotmatrixtool)
- **Option B**: Lower (minimal modifications to dotmatrixtool)

### User Experience

- **Option A**: Modern, polished UI with advanced features
- **Option B**: Functional but basic UI

### Maintainability

- **Option A**: Better (React component architecture)
- **Option B**: Mixed (Python good, frontend dated)

### Extensibility

- **Option A**: Excellent (easy to add features in React)
- **Option B**: Limited (jQuery codebase harder to extend)

### System Alerts Integration

- **Option A**: Full implementation of notification API design
- **Option B**: Basic implementation

### Time to MVP

- **Option A**: 3-4 weeks
- **Option B**: 1-2 weeks

## Recommendation

**Start with Option B, migrate to Option A later:**

1. Implement Mode Management System (critical for both)
2. Build FastAPI layer with minimal endpoints
3. Modify dotmatrixtool to call Python API instead of Web Serial
4. Add basic quadrant configuration UI
5. Test and validate architecture
6. Later: Migrate frontend to React incrementally

This approach:

- Validates the architecture quickly
- Solves the mode management problem first
- Provides working system faster
- Allows React migration when UI needs justify effort

## Common Requirements (Both Options)

### Critical Components

1. **Mode Management System** - Prevents auto/manual conflicts
2. **Hardware Access Locking** - Serializes LED matrix access
3. **API Layer** - Communication between frontend and Python service
4. **Auto Mode Pause/Resume** - Clean state transitions
5. **Manual Mode Timeout** - Safety mechanism

### Configuration Management

- Read/write config.yaml via API
- Validate configuration before applying
- Backup previous config on changes
- Reload service configuration without restart

### Integration with Existing Code

- led-matrix/monitors.py - Already provides system metrics
- led-matrix/plugins/ - Plugin architecture works as-is
- led-matrix/drawing.py - Needs locking modification for mode management
- led-matrix/config.yaml - Becomes API-editable, already has 4-quadrant structure
- led-matrix/led_system_monitor.py - Already detects 1 or 2 panels via discover_led_devices()
- dotmatrixtool/app.js - Canvas reused in both options (left/right already separate)

### Panel Configuration Notes

- Backend always treats panels independently (2× 9×34)
- No "unified mode" in backend code - always 4 quadrants (to be decided)
- "Unified view" is purely a frontend UX feature for drawing alignment
- When drawing spans both panels, frontend sends left data + right data separately (to be decided)
- Existing config.yaml structure already supports this (top-left, bottom-left, top-right, bottom-right)

### Future development 
- dotmatrixtool/app.js / led-matrix/plugins/  Plugin and icon / animation management and installation through API  and dotmatixtool. UX friendly