# Framework 16 LED Matrix System Monitoring Application

This software is intended for use on a Framework 16 laptop with LED Matrix Panels installed. It's a clone of the [LED System Monitor](https://code.karsttech.com/jeremy/FW_LED_System_Monitor.git) project, with certain modifications and extensions applied.

## Compatibility

**Hardware:** Framework 16 laptops with LED Matrix Panels  
**Operating Systems:** Linux distributions (Ubuntu, Fedora, NixOS, Debian, CentOS, RHEL, and others)  
**Dependencies:** Python 3.7+ with numpy, psutil, pyserial, and evdev

## Quick Start

For most users, the fastest way to get started:

```bash
# Clone the repository
git clone <repository-url>
cd led-matrix-monitoring

# Run with automatic dependency installation
chmod +x run.sh
./run.sh
```

The `run.sh` script will automatically detect your Linux distribution and install the required dependencies.

## Original Capabilities
Display system performance characteristics in real-time
* Top Left: CPU utilization
* Bottom Left: Battery charge level and plug status + memory utilization
* Top Right: Disk Input/Output rates
* Bottom Right: Network Upload/Download rates

## Enhanced Capabilities
* Pre-defined applications can be displayed on any quadrant
  * Top or bottom of left or right panel
  * Specified via program arguments
* Additional system performance applications
  * Temperature sensor values (average of sensors on each of up to eight devices)
  * Fan speeds (max 2 supported)
* Keyboard shortcut identifies apps running in each quadrant by displaying abbeviated name 
* Plugin framework supports simplified development of addiitonal LED Panel applications
* Automatic detection of left and right LED panels
## Installation

### Option 1: System Package Installation (Recommended)

#### For Ubuntu/Debian users:
```bash
sudo apt update
sudo apt install -y python3-numpy python3-psutil python3-serial python3-evdev
cd led-matrix-monitoring
python3 led_system_monitor.py
```

#### For Fedora users:
```bash
sudo dnf install -y python3-numpy python3-psutil python3-pyserial python3-evdev
cd led-matrix-monitoring
python3 led_system_monitor.py
```

#### For NixOS users:
```bash
# Using the Nix flake (recommended)
nix run github:your-repo/led-matrix-monitoring

# Or build locally
nix build
./result/bin/led-matrix-monitor
```

### Option 2: Python Virtual Environment
* Install [PyEnv](https://github.com/pyenv/pyenv) or any other python virtual environment package
* Commands below work with PyEnv:
```bash
cd led-matrix-monitoring
pyenv install 3.11
pyenv virtualenv 3.11 led-matrix-env
pyenv activate led-matrix-env
pip install -r requirements.txt
```
## Run
```
cd led-matrix
python led-sysyem-monitor.py [--help] [--top-left {cpu,net,disk,mem-bat,none,temp,fan}] [--bottom-left {cpu,net,disk,mem-bat,none,temp,fan}] [--top-right {cpu,net,disk,mem-bat,none,temp,fan}]
                             [--bottom-right {cpu,net,disk,mem-bat,none,temp,fan}] [--no-key-listener] [--disable-plugins]
python led-sysyem-monitor.py --help #For more verbose help info
```
## Run as a Linux service
```
cd led-matrix
./install_as_service.sh [...args] #program args to be applied when starting or restarting the service
sudo systemctl start|stop|restart|status fwledmonitor
```
## Keyboard Shortcut
* Alt+I: displays app names in each quadrant while keys are pressed
* Disable key listener with `--no-key-listener` program arg
* To use the key listener, the app must have read permission on the keyboard device (e.g /dev/input/event7). The service runs as root, and therefore has the required access. If you want toi use the key listener while running the app directly, you need to add your user account to the `input` group and ensure there is a group read permission on the keyboard device. **NB:** Consider the implications of this. Any program running as a user in the `input` group will be able to capture your keystrokes.
## Plugin Development
* Add a file in the `plugins` dir with a name that matches the blob pattern `*_plugin.py`
* See `temp_fan_plugin.py` for an implementation example
## Notes
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
