# Framework 16 LED Matrix Monitoring - NixOS Integration

This repository provides a NixOS package and service for the Framework 16 LED Matrix System Monitor. It includes robustness improvements and easy NixOS integration.

## Features

- **Complete NixOS Integration**: Flake with module support for easy system integration
- **Robust Error Handling**: Graceful degradation when hardware is unavailable or permissions are denied
- **Configurable Service**: Systemd service with full configuration options
- **Plugin Support**: Extensible plugin framework for additional functionality
- **Framework Hardware Support**: Specifically designed for Framework 16 LED Matrix panels

## Quick Start

### Method 1: Direct Package Installation

Add this to your NixOS configuration:

```nix
# configuration.nix or any imported module
{ config, pkgs, ... }:

let
  led-matrix-monitoring = pkgs.callPackage (pkgs.fetchFromGitHub {
    owner = "timoteuszelle";
    repo = "led-matrix";
    rev = "fix/robustness-and-permission-handling";  # Use latest commit hash
    sha256 = "sha256-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=";  # Replace with actual hash
  } + "/default.nix") {};
in
{
  environment.systemPackages = [ led-matrix-monitoring ];
}
```

Then run manually:
```bash
led-matrix-monitor --help
led-matrix-monitor --top-left cpu --bottom-left mem-bat --top-right disk --bottom-right net
```

### Method 2: Using Flakes (Recommended)

#### Step 1: Add as flake input

Add to your `flake.nix`:

```nix
{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    # ... your other inputs
    led-matrix-monitoring = {
      url = "github:timoteuszelle/led-matrix/fix/robustness-and-permission-handling";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { self, nixpkgs, led-matrix-monitoring, ... }:
  {
    nixosConfigurations.your-hostname = nixpkgs.lib.nixosSystem {
      system = "x86_64-linux";
      modules = [
        ./configuration.nix
        led-matrix-monitoring.nixosModules.led-matrix-monitoring
      ];
    };
  };
}
```

#### Step 2: Configure the service

Add to your `configuration.nix`:

```nix
{ config, lib, pkgs, ... }:

{
  # Enable the LED Matrix Monitoring service
  services.led-matrix-monitoring = {
    enable = true;
    
    # Configure what shows in each quadrant
    topLeft = "cpu";          # CPU utilization
    bottomLeft = "mem-bat";   # Memory usage + battery status
    topRight = "disk";        # Disk I/O rates
    bottomRight = "net";      # Network upload/download
    
    # Optional: disable keyboard listener (Alt+I shortcut)
    # disableKeyListener = true;
    
    # Optional: disable plugins
    # disablePlugins = true;
    
    # Optional: run as different user (default: root)
    # user = "your-username";
  };
}
```

#### Step 3: Rebuild your system

```bash
sudo nixos-rebuild switch --flake .#your-hostname
```

## Configuration Options

### Display Metrics

Each quadrant can display:
- `cpu`: CPU utilization percentage
- `mem-bat`: Memory usage and battery charge/status
- `disk`: Disk read/write I/O rates
- `net`: Network upload/download rates
- `temp`: Temperature sensor readings (plugin)
- `fan`: Fan speed readings (plugin)
- `none`: Disabled/blank

### Service Options

```nix
services.led-matrix-monitoring = {
  enable = true;                    # Enable the service
  topLeft = "cpu";                 # Top-left quadrant
  bottomLeft = "mem-bat";          # Bottom-left quadrant
  topRight = "disk";               # Top-right quadrant  
  bottomRight = "net";             # Bottom-right quadrant
  disableKeyListener = false;      # Disable Alt+I app identification
  disablePlugins = false;          # Disable plugin system
  user = "root";                   # User to run service as
};
```

## Manual Usage

Run directly with custom options:

```bash
# Show help
led-matrix-monitor --help

# Custom configuration
led-matrix-monitor \
  --top-left cpu \
  --bottom-left mem-bat \
  --top-right temp \
  --bottom-right fan \
  --no-key-listener
```

## Keyboard Shortcuts

- **Alt+I**: Display application names in each quadrant while pressed
- Use `--no-key-listener` or `disableKeyListener = true` to disable

## Permissions

For keyboard functionality:
- Service runs as `root` by default (recommended)
- If running as user, they'll be added to `input` group automatically
- Consider security implications of `input` group membership

## Troubleshooting

### Check service status
```bash
systemctl status led-matrix-monitoring
```

### View logs
```bash
journalctl -u led-matrix-monitoring -f
```

### Test without hardware
```bash
# Should show help even without LED matrices
led-matrix-monitor --help
```

### Common issues

1. **"No LED devices found"**: LED Matrix panels not detected
   - Check USB connections
   - Verify Framework 16 with LED Matrix input modules

2. **Permission errors**: Input device access denied
   - Service automatically handles this when running as root
   - For user mode, automatic `input` group membership is configured

3. **Module import errors**: Missing dependencies
   - All dependencies are automatically handled by Nix
   - Try rebuilding: `nix build github:timoteuszelle/led-matrix/fix/robustness-and-permission-handling`

## Development

### Local development

```bash
git clone https://github.com/timoteuszelle/led-matrix.git
cd led-matrix
nix develop  # Enter development shell with all dependencies
python led_system_monitor.py --help
```

### Building locally

```bash
nix build github:timoteuszelle/led-matrix/fix/robustness-and-permission-handling
./result/bin/led-matrix-monitor --help
```

## Contributing

This is a fork of the original [FW_LED_System_Monitor](https://code.karsttech.com/jeremy/FW_LED_System_Monitor.git) with NixOS packaging and robustness improvements.

- Original upstream: MidnightJava/led-matrix  
- NixOS integration: timoteuszelle/led-matrix

Contributions welcome for:
- Additional plugins
- NixOS module improvements
- Bug fixes and robustness improvements
- Documentation updates

## License

MIT License (assuming - verify with original project)

## Hardware Requirements

- Framework 16 laptop
- LED Matrix Input Module(s) installed
- NixOS operating system

