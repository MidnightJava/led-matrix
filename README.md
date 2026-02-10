# Framework 16 LED Matrix System Monitoring Application

This software is intended for use on a Framework 16 laptop with LED Matrix Panels installed. It's based on the [LED System Monitor](https://code.karsttech.com/jeremy/FW_LED_System_Monitor.git) project, with extensive modifications and extensions applied.

## Compatibility

**Hardware:** Framework 16 laptops with LED Matrix Panels  
**Operating Systems:** Linux distributions (Ubuntu, Fedora, NixOS, Debian, CentOS, RHEL, and others)  
**Dependencies:** Python 3.7+ with numerous PyPi depednenceies (see requirements.txt)

## Quick Start (install the app and run it as a service)

For most users, the fastest way to get started. This installs dependencies, builds the app, installs it as a service, and starts the service:

```bash
# Clone the repository
git clone <repository-url>
cd led-matrix

# Run with automatic dependency installation
chmod +x build_and_install.sh
./build_and_install.sh
./dist/led_mon/led_mon #optionally run manually
```

The `build_and_install.sh` script will automatically detect your Linux distribution, install the required dependencies, build an executable file of the python application, and install it as a user-level systemd service fwledmonitor.service.

## Capabilities
* Display system performance characteristics in real-time
  * CPU utilization
  * Battery charge level and plug status + memory utilization
  * Disk Input/Output rates 
  * Network Upload/Download rates
  * Temperature sensor readings
  * Fan speeds
* Other apps
  * Current weather or weather forecast
  * Time
  * Display patterns saved in snapshot json files
  * Equalizer visualization of current audio source
* Display any system monitoring app on any quadrant
  * Top or bottom of left or right panel
  * Assign multiple apps to any quadrant and cycle throiugh them at specified time intervals
  * Turn on animation and define command arguments for apps
  * Specified via a yaml config file
* Keyboard shortcut `ALT` + `I` identifies apps running in each quadrant by displaying abbreviated name
* Plugin framework supports simplified development of addiitonal LED Panel applications
* Automatic detection of left and right LED panels
* Automatic detection of keyboard device (for keyboard shortcut use)

## Important note about Python environments
[Pep 668](https://peps.python.org/pep-0668/) provides a mechanism for a Python installation to communicate to tools such as Pip that the installation is externally managed. For Python installations that implement this notification, an attempt to install a package in the global context will be denied, with a message that the installation is externally managed. There are ways to override the PEP 668 constraint (such as using pipx or the --break-system-packages flag). The standard solution, however, is to use a Python Virtual Environment.

The build and installation instructions and scripts for this project assume that every Python installation action is done in a virtual environment. If you want to perform a global installation, it's up to you to make whatever changes are needed to make that work. Also, please note that a misconfigured virtual environment will result in either build-time or run-time failures. See installation notes below for instructions. In general, you should 1) Install package dependencies for the selected virtual environment tool 2) Install the tool 3) Configure the tool per instructions provided by the tool provider 3) Create a virtual environment and activate it 4) Ensure that the virtual environment is currently activated in any shell from which you perform a Python installation, whether launching python directly or invoking a build or installation script. The error message `python: command not found` is a likely indicator of a missing or misconfigured virtual environment.

## Plugins
Application capabilities can be extended by including plugins. See `plugins/plugins-README.md` for more info. See the plugin configuration near the bottom of this page for plugin-specific configuration instructions.

## Manual Installation (run the app from the command line in the foreground)

Install [PyEnv](https://github.com/pyenv/pyenv) or any other python virtual environment package (Commands below work with PyEnv)
### For Ubuntu/Debian users:
```bash
sudo apt update
sudo apt install -y python3-numpy python3-psutil python3-serial python3-evdev python3-pynput python3-yaml python3-pip
cd led-matrix-monitoring
pyenv install 3.11 # or higher (tested up to 3.14)
pyenv virtualenv 3.11 led-matrix-env
pyenv activate led-matrix-env
python -m pip install -r requirements.txt
python -m led_mon.led_system_monitor
```

### For Fedora users:
```bash
sudo yum install -y python3-numpy python3-psutil python3-pyserial python3-evdev python3-pynput python3-pyyaml python3-pip
cd led-matrix-monitoring\
pyenv install 3.11 # or higher (tested up to 3.14)
pyenv virtualenv 3.11 led-matrix-env
pyenv activate led-matrix-env
python -m pip install -r requirements.txt
python -m led_mon.led_system_monitor
```

### For NixOS users:
```bash
# Using the Nix flake (recommended)
nix run github:MidnightJava/led-matrix

# Or build locally
nix build
./result/bin/led-matrix-monitor
```

### NixOS System Integration

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
systemctl --user status led-matrix-monitoring

# View logs
journalctl --user -u led-matrix-monitoring -f

# Common error: "failed to acquire X connection: Bad display name"
# Solution: Ensure DISPLAY environment variable is set in service override
```

**Alternative: Systemd Service (Advanced)**

For automated continuous execution, you can run as a systemd service instead:

```bash
# The service runs as a user-level systemd service under the logged in user's account
./build_and_install.sh
# manage the service
systemctl --user start|stop|status fwledmatrix.service
# The service config file is at ~/.config/systemd/user/fwledmonitor.service.
# The service executable is at /opt/led_mon/led_mon (sym-linked to /usr/local/bin/led_mon)
```

## Required Permissions

### LED Matrix Device Access

By default, LED Matrix devices appear as serial devices (e.g., `/dev/ttyACM0`, `/dev/ttyACM1`) that are typically owned by root with restricted permissions. To allow your user to access these devices, you have several options:

#### Option 1: Add User to dialout Group
```bash
# Add your user to the dialout group
sudo usermod -a -G dialout $USER

# Log out and log back in, or use:
newgrp dialout

# Verify group membership
groups $USER
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
Since running as root will bypass permission issues, this is not recommended for security reasons. You also may have to work around PEP 668 restrictions on an externally managed Python environment, as discussed above.
```bash
sudo python3 -m led_mon.led_system_monitor
```

## Keyboard Input Access (Optional)

For the Alt+I keyboard shortcut feature to work, the application needs read access to keyboard input devices:

```bash
# Add user to input group (be aware of security implications)
sudo usermod -a -G input $USER

# Log out and log back in, then verify
groups $USER
```

**Security Note:** Adding your user to the `input` group allows any program running as your user to potentially capture keystrokes. Consider the security implications before doing this, or do not add your user to the group, and use `--no-key-listener` to disable this feature.

## Modifying the Apps Configuration
* The app is configured *out of the box* to cycle through most of the available widgets, switching to the next widget every 30 seconds.
* To customize the coonfiguration:
  * The file `led_mon/config.yaml` contains the default configuration, along with comments explaining the format and meaning of config settings.
  * Make a copy of `config.yaml`, named `config-local.yaml`, in the `led_mon` directory, and make any desired changes. This file is git-ignored, so it will not be shared or overwritten.
  * If `config-local.yaml` is present, it will be thhe active config, and `config.yaml` will be ignored.
  * When running as a service, both config files will be copied to `/opt/led_mon/_internal/`. Files in this directory will be completely overwritten for every installation, so you should maintain your local configuration in the project repo, not the application installation directory.
  * The `config.yaml` file may be updated when you run `git pull` in the repo. Check Pull Request comments for an explanation of what changed. Every effort will be made to avoid breaking changes, but they cannot be ruled out at this stage of dvelopment. When new widgets are added to the app, you'll need to manually copy the new widget config settings into your local config file if you have one.

## Verifying Device Access

To check if your LED Matrix devices are properly accessible:

```bash
# List LED Matrix devices
ls -la /dev/ttyACM*

# Check if they're accessible by your user
python3 -c "from serial.tools import list_ports; [print(f'{p.device}: {p.description}') for p in list_ports.comports() if 'LED Matrix' in str(p)]"
```

## Run from the command line
```
cd led-matrix
python -m led_mon.led_system_monitor [--help] [--no-key-listener] [--disable-plugins] [--list-apps]
python -m led_mon.led_system_monitor --help #For more verbose help info
```

## Run as a Linux service
Enter the top-level project directory, and ensure that a virtual environment is configured and activated.
```
./build_and_install.sh
systemctl --user start|stop|restart|status fwledmonitor
```

## Keyboard Shortcut
* Alt+I: displays app names in each quadrant while keys are pressed
* Disable key listener with `--no-key-listener` program arg
* To use the key listener, the app must have read permission on the keyboard device (e.g `/dev/input/event<n>`). T use the key listener, you need to add your user account to the `input` group and ensure there is a group read permission on the keyboard device. **NB:** Consider the implications of this. Any program running as a user in the `input` group will be able to capture your keystrokes.

## Plugin Development
* See `plugins/plugin-README.md` for instructions

## Plugin Configuration and Dependencies
See `config-README.md` for general configuration instructions. Here we provide plugin-specific configuration, dependency, and other information. Plugins that have no special configuration or depenency requirements are not adderssed here.

### Time (provided by `time_weather_plugin.py`):
Configure the following arguments in the config file (`app->args`)

`fmt_24_hour: true|false`

### Weather (provided by `time_weather_plugin.py`):
You must specify app arguments in the config file and set one or more environment variables, as described below.
Set arguments (`app -> ags`) for the `weather` app in the desired quadrant
  - To enable online lookup of local weather information, the app must know your location. Choose one or more of the options.

    1) Specify country-specific zip and [ISO 3166 digraph code](https://www.iban.com/country-codes)
    
         `zip_info: ["your zip", "country code"]`

    2) Specify latitude and longitude direclty

         `lat_lon: [<lat>, <lon>]`

    3) Set env var IP_LOCATE_API_KEY in `.env`. Get a free API key from https://iplocate.io
       
  - Display temperature in Celsius, Farenheit, or Kelinv. Default is metric

    `units: imperial|metric|standard`
  - Show current or forecast weather. Default is current

    `forecast: true|false`
  - Set day offset (GMT time) for forecast (max 5, default 1)

    `forecast_day: n`
  - Set Hour offset (GMT time) for forecast on selected day. One of 0, 3, 6, 9, 12, 15, 18, 21. default is 12
    If selected time is more than 5 * 24 hours from present time, the latest available forecast will be shown

    `forecast_hour: n`
  - Override the key used to display the app ID. This means if forecast is true, use weather_forecast, otherwise use weather_current

    `id_key_override: [forecast, weather_forecast, weather_current]`

### Snapshot (built-in app, not a plugin):
Configure the following arguments in the config file (`app -> args`)
- Name of the JSON file with a pattern to display

  `file: <file name>`
- The file path relative to the module dir (`led_mon`)

  `path: <path>`
- The sudbir of the file, relative to `path`

  `panel: left|right|<xxx>`

### Equalizer (provided by `equalizer_plugin.py`)
Set the following app settings. These are direct properties of the equalizer app, not args
- Set to true if the app will handle drawing to the grid the entire time it is active. If false, the app draws a static snapshot on every invocation. Default is false

  `persistent-draw: true|false`
- Since the equalizer draws continuously to the LED panel, this function (specified in `app_funcs`), is invoked to pause the equalizer when its duration peroiod expires

  `dispose-fn: equalizer_dispose`

Configure the following arguments in the config file (`app -> args`)
- Use the internal python 9-band filter or use an extenal filter. [EasyEffects](https://github.com/wwmm/easyeffects) is the recommended external filter to use. You can tune the equalizer dynamically as it runs, using the EasyEffects GUI.

  `external-filter: false|true`
- Identify device location by device or quandrant. Used for identifying the app instance if a dispose function is called

  `side: left|right|<quadrant>`

The equalizer relies on PulseAudio and Pipewire packages to receive and process the audio output of your computer. The following packages must be installed:
- Debian/Ubuntu: `sudo apt install pipewire pipewire-pulse wireplumber pulseaudio-utils`
- Fedora: `sudo dnf install pipewire pipewire-pulseaudio wireplumber`

You must add your user to the audio group
- `sudo usermod -Ag audio $USER`
- Then logout and login, run `newgrp audio`, or reboot. Verify with `sudo groups`

The Equalizer requires the Framework-provided Input Module Control binary to be intatlled somewhee on your executable path. If it's on the path, the app will find it. Otherwise, the equalizer will not run, and an error will be logged.
- [Project Info](https://github.com/FrameworkComputer/inputmodule-rs/tree/main) (with instructions to build from source)
- [Binary Downloads](https://github.com/FrameworkComputer/inputmodule-rs/releases)

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
