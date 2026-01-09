# Framework 16 LED Matrix System Monitoring Application

This software is intended for use on a Framework 16 laptop with LED Matrix Panels installed. It's a clone of the [LED System Monitor](https://code.karsttech.com/jeremy/FW_LED_System_Monitor.git) project, with certain modifications and extensions applied.

## Compatibility

**Hardware:** Framework 16 laptops with LED Matrix Panels  
**Operating Systems:** Linux distributions (Ubuntu, Fedora, NixOS, Debian, CentOS, RHEL, and others)  
**Dependencies:** Python 3.7+ with numpy, psutil, pyserial, and evdev

## Quick Start

For most users, the fastest way to get started. This installs dependencies, builds the app, installs it as a service, and starts the service:

```bash
# Clone the repository
git clone <repository-url>
cd led-matrix-monitoring

# Run with automatic dependency installation
chmod +x build_and_install.sh
./build_and_install.sh
./dist/led_mon/led_mon #optionally run manually
```

The `build_and_install.sh` script will automatically detect your Linux distribution, install the required dependencies, build an executable file of the python application, and install it as a systemd service fwledmonitor.service.

## Capabilities
* Display system performance characteristics in real-time
  * CPU utilization
  * Battery charge level and plug status + memory utilization
  * Disk Input/Output rates
  * Network Upload/Download rates
  * Temperature sensor readings
  * Fan speeds
* Display any system monitoring app on any quadrant
  * Top or bottom of left or right panel
  * Assign multiple apps to any quadrant and cycle throiugh them at specified time intervals
  * Turn on animation and define command arguments for apps
  * Specified via a yaml config file
* Display a "snapshot" from specified json file(s) on either or both panels.
* Keyboard shortcut `ALT` + `I` identifies apps running in each quadrant by displaying abbreviated name
* Plugin framework supports simplified development of addiitonal LED Panel applications
* Automatic detection of left and right LED panels
* Automatic detection of keyboard device (for keyboard shortcut use)
## Capabilities added to the original implementation
 * Temp sensor and fan speed apps
 * Metrics apps configurable to any matrix quadrant, with optional time multiplexing
 * Configuration of apps via yaml config file
 * LED panel animation
 * Plugin capability
 * Automatic device and keyboard detection
 * Snapshot app
## Installation
In case you want to develop on the code (otherwise follow the *Quick Start* above).
### System Package and Python Library Installation (For running manually, e.g. in an IDE)

#### For Ubuntu/Debian users:
* Install [PyEnv](https://github.com/pyenv/pyenv) or any other python virtual environment package
* Commands below work with PyEnv:
```bash
sudo apt update
sudo apt install -y python3-numpy python3-psutil python3-serial python3-evdev python3-pynput python3-yaml python3-pip
cd led-matrix-monitoring
pyenv install 3.11 # or higher (tested up to 3.14)
pyenv virtualenv 3.11 led-matrix-env
pyenv activate led-matrix-env
python3 -m pip install -r requirements.txt
python3 led_system_monitor.py
```

#### For Fedora users:
```bash
sudo yum install -y python3-numpy python3-psutil python3-pyserial python3-evdev python3-pynput python3-pyyaml python3-pip
cd led-matrix-monitoring\
pyenv install 3.11 # or higher (tested up to 3.14)
pyenv virtualenv 3.11 led-matrix-env
pyenv activate led-matrix-env
python3 led_system_monitor.py
```

#### For NixOS users:
```bash
# Using the Nix flake (recommended)
nix run github:MidnightJava/led-matrix

# Or build locally
nix build
./result/bin/led-matrix-monitor
```

#### NixOS System Integration

For NixOS users who want to run LED matrix monitoring as a system service, additional configuration is required:

**1. Add to your flake.nix inputs:**
```nix
{
  inputs = {
    # ... other inputs
    led-matrix-monitoring.url = "github:MidnightJava/led-matrix";
  };
}
```

**2. Import the module in your NixOS configuration:**
```nix
{
  imports = [
    inputs.led-matrix-monitoring.nixosModules.led-matrix-monitoring
  ];
}
```

**3. Enable and configure the service:**
```nix
services.led-matrix-monitoring = {
  enable = true;
  topLeft = "cpu";
  bottomLeft = "mem-bat";
  topRight = "disk";
  bottomRight = "net";
  disableKeyListener = true;  # Recommended for system service
  user = "your-username";
};
```

**4. Add systemd service environment override (Required):**

The service needs access to the display server. Add this to your NixOS configuration:

```nix
# Override the LED matrix monitoring service to add DISPLAY environment variable
systemd.services.led-matrix-monitoring = {
  environment = {
    DISPLAY = ":0";  # Adjust if using different display
  };
  serviceConfig = {
    # Ensure the service waits for the graphical session
    After = [ "graphical-session.target" ];
    Wants = [ "graphical-session.target" ];
  };
};
```

**5. Rebuild your system:**
```bash
sudo nixos-rebuild switch
```

**Troubleshooting NixOS Service Issues:**

If the service fails to start with display connection errors:

```bash
# Check service status
systemctl status led-matrix-monitoring

# View logs
journalctl -u led-matrix-monitoring -f

# Common error: "failed to acquire X connection: Bad display name"
# Solution: Ensure DISPLAY environment variable is set in service override
```

**Alternative: Systemd Service (Advanced)**

For automated continuous execution, you can run as a systemd service instead:

```bash
# The service runs as system user led_mon (created by the script if needed)
./build_andOnstall.sh
# manage the service
systemctl start|stop|status fwledmatrix.service
# The service config file is at /etc/systemd/system/led_mon.service.
# The service executable is at /opt/led_mon/led_mon (sym-linked to /usr/local/bin/led_mon)
```

## Required Permissions

### LED Matrix Device Access

By default, LED Matrix devices appear as serial devices (e.g., `/dev/ttyACM0`, `/dev/ttyACM1`) that are typically owned by root with restricted permissions. To allow your user to access these devices, you have several options:

#### Option 1: Add User to dialout Group (Recommended for running under user account, not needed for service execution)
```bash
# Add your user to the dialout group
sudo usermod -a -G dialout $USER

# Log out and log back in, or use:
newgrp dialout

# Verify group membership
groups $USER

# This is done by install_service.sh for the led_mon system account that executes the service
```

#### Option 2: Create Custom udev Rules
Create a udev rule file to automatically set proper permissions:

```bash
# Create the udev rule file
sudo tee /etc/udev/rules.d/99-framework-led-matrix.rules <<EOF
# Framework 16 LED Matrix Input Modules
SUBSYSTEM=="tty", ATTRS{idVendor}=="32ac", ATTRS{idProduct}=="0020", MODE="0666", GROUP="dialout"
SUBSYSTEM=="usb", ATTRS{idVendor}=="32ac", ATTRS{idProduct}=="0020", MODE="0666", GROUP="dialout"
EOF

# Reload udev rules
sudo udevadm control --reload-rules
sudo udevadm trigger
```

#### Option 3: Run as Root (Not Recommended)
While running as root will bypass permission issues, this is not recommended for security reasons:
```bash
sudo python3 led_system_monitor.py
```

### Keyboard Input Access (Optional)

For the Alt+I keyboard shortcut feature to work, the application needs read access to keyboard input devices:

```bash
# Add user to input group (be aware of security implications)
sudo usermod -a -G input $USER

# Log out and log back in, then verify
groups $USER

# This is done by install_servce.sh for the led_mon system account that executes the service
```

**Security Note:** Adding your user to the `input` group allows any program running as your user to potentially capture keystrokes. Consider the security implications before doing this, or do not add your user to the group, and use `--no-key-listener` to disable this feature.

### Modifying the Apps Configuration
* Edit config.yaml. See example settings and comments for help.
* When running as a service, the config file will be at /opt/led_mon/_internal/config.yaml (unless overriden by --config-file arg)

### Verifying Device Access

To check if your LED Matrix devices are properly accessible:

```bash
# List LED Matrix devices
ls -la /dev/ttyACM*

# Check if they're accessible by your user
python3 -c "from serial.tools import list_ports; [print(f'{p.device}: {p.description}') for p in list_ports.comports() if 'LED Matrix' in str(p)]"
```

### Linux Service Dependencies

If you want to run the code as a Linux service, you need to install the python dependencies as the root user:
```bash
cd led-matrix
sudo pip install -r requirements.txt
```
## Run
```
cd led-matrix
python led-sysyem-monitor.py [--help] [--top-left {cpu,net,disk,mem-bat,none,temp,fan}]
                             [--config file <path/to/config/file> (default ./config.yaml]
                             [--list-apps]
python led-sysyem-monitor.py --help #For more verbose help info
```
## Run as a Linux service
```
cd led-matrix
./build_and_install.sh
sudo systemctl start|stop|restart|status fwledmonitor
```
## Keyboard Shortcut
* Alt+I: displays app names in each quadrant while keys are pressed
* Disable key listener with `--no-key-listener` program arg
* To use the key listener, the app must have read permission on the keyboard device (e.g /dev/input/event7). The service runs under a system account that has the required access. If you want to use the key listener while running the app manually, you need to add your user account to the `input` group and ensure there is a group read permission on the keyboard device. **NB:** Consider the implications of this. Any program running as a user in the `input` group will be able to capture your keystrokes.
## Plugin Development
* Add a file in the `plugins` dir with a name that matches the blob pattern `*_plugin.py`
* See `temp_fan_plugin.py` for an implementation example
## Notes
* See https://github.com/FrameworkComputer/inputmodule-rs for info about the LED matrix device. Be sure to run the code that installs the udev rules for accessing the devices.
* To list your input devices, use the following python code after installing [Python-evdev](https://python-evdev.readthedocs.io/en/latest/index.html)
```
>>> import evdev

>>> devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
>>> for device in devices:
>>>     print(device.path, device.name, device.phys)
/dev/input/event1    Dell Dell USB Keyboard   usb-0000:00:12.1-2/input0
/dev/input/event0    Dell USB Optical Mouse   usb-0000:00:12.0-2/input0
```
* The baseline reference for calculating the ratio used to display temperature and fan speed readings were arbitarily defined. See `TEMP_REF` and `MAX_FAN_SPEED` in `temp_fan_plugin.py`.  
* To examine system performance measures manually and in detail, run `python ps-util-sensors.py`
* To use a different key combination for identifying the running apps, see `KEY_I` and `MODIFIER_KEYS` in `led_system_monitor.py`
