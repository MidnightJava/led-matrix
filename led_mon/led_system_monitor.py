# Built In Dependencies
import time
import queue
import sys
import re
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
import importlib.util
import sys
import os
from collections import defaultdict
import logging
import traceback

# Internal Dependencies
from led_mon.drawing import draw_outline_border, draw_ids, draw_id, draw_app, draw_app_border, DrawingThread
from led_mon.monitors import CPUMonitor, MemoryMonitor, BatteryMonitor, DiskMonitor, NetworkMonitor, get_monitor_brightness

# External Dependencies
import numpy as np
import evdev
from yaml import safe_load

# Optional cross-platform keyboard input; on some Linux Wayland setups this may be unavailable
try:
    from pynput.keyboard import Key, Listener
    PYNPUT_AVAILABLE = True
except Exception:
    Key = None
    Listener = None
    PYNPUT_AVAILABLE = False
from serial.tools import list_ports

log = logging.getLogger(__name__)

LOG_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
}

log_level = LOG_LEVELS[os.environ.get("LOG_LEVEL", "warning").lower()]
log.setLevel(log_level)

def is_frozen():
    """Return True if running from a PyInstaller bundle."""
    return hasattr(sys, "_MEIPASS")

# The pyinstaller-frozen code runs as a service, with the env var file specified in the service configfuration
if not is_frozen():
    from dotenv import load_dotenv
    load_dotenv()

KEY_I = ('KEY_I', 23)
MODIFIER_KEYS = [('KEY_RIGHTALT', 100), ('KEY_LEFTALT', 56)]

def find_keyboard_device():
    """Auto-detect keyboard input device from /dev/input/event*"""
    try:
        devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
        for device in devices:
            # Look for devices with keyboard capabilities (EV_KEY with standard keys)
            capabilities = device.capabilities(verbose=False)
            if evdev.ecodes.EV_KEY in capabilities:
                keys = capabilities[evdev.ecodes.EV_KEY]
                # Check if device has typical keyboard keys (letters and modifiers)
                has_letters = any(k in keys for k in range(evdev.ecodes.KEY_Q, evdev.ecodes.KEY_P + 1))
                has_modifiers = any(k in keys for k in [evdev.ecodes.KEY_LEFTALT, evdev.ecodes.KEY_RIGHTALT])
                if has_letters and has_modifiers:
                    return device.path
    except Exception as e:
        log.warning(f"Warning: Could not auto-detect keyboard device: {e}")
    return None

def get_config():
    # Check for CONFIG_FILE environment variable first (used by NixOS module)
    config_file = os.environ.get('CONFIG_FILE', None)
    if config_file:
        log.debug(f"Using config file from CONFIG_FILE env var: {config_file}")
    else:
        # Fall back to config-local.yaml or config.yaml in current directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        config_file_name = 'config-local.yaml'
        config_file = os.path.join(current_dir, config_file_name)
        if os.path.exists(config_file):
            log.debug(f"Using local config file {config_file}")
        else:
            config_file_name = 'config.yaml'
            config_file = os.path.join(current_dir, config_file_name)
            log.debug(f"Using default config file {config_file}")
    with open(config_file, 'r') as f:
        return safe_load(f)

def discover_led_devices():
    locations = []
    try:
        device_list = list_ports.comports()
        for device in device_list:
            if 'LED Matrix Input Module' in str(device):
                locations.append((device.location, device.device))
        #location is of form: <bus>-<port>[-<port>]  (port is of form x.y:n.m)
        # Example: 1-3.3:1.0 (right device) , 1-3.2:1.0 (left device)
        # Sort by y:n.m to get the devices in left-right order
        return sorted(locations, key = lambda x: re.sub(r'^\d+\-\d+\.', '', x[0]))
    except Exception as e:
        log.error(f"An Exception occured while tring to locate LED Matrix devices. {e}")

def list_apps(base_apps, plugin_apps, quads):
    max_len = max(map(lambda x: len(x), base_apps + plugin_apps))
    print("Installed Apps:")
    print("   " + "Name".ljust(max_len+3, ' ') + "Source".ljust(12, " ") + "Configuration")
    configured_apps = defaultdict(list)
    for quad in quads.values():
        for app in quad:
            del app["app"] # Just the list name in the yaml file, value will be set to None
            configured_apps[app["name"]].append(app)
    for app in [*base_apps , *plugin_apps]:
        if not app in configured_apps:
            print(f"   {app.ljust(max_len+3, ' ')}", end='')
            print(f"{'plugin app'.ljust(12, ' ')if app in plugin_apps else 'base app'.ljust(12, ' ')}", end='')
            print(f"None")
        for _app in configured_apps[app]:
            print(f"   {app.ljust(max_len+3, ' ')}", end='')
            print(f"{'plugin app'.ljust(12, ' ')if app in plugin_apps else 'base app'.ljust(12, ' ')}", end='')
            print(f"{_app}")
        
device = None
def app(args, base_apps, plugin_apps):    
    # Initialize evdev device for key listening if not disabled
    global device
    if not args.no_key_listener:
        # Try to auto-detect keyboard device first
        kbd_path = find_keyboard_device()
        if kbd_path:
            try:
                device = evdev.InputDevice(kbd_path)
                log.info(f"Using keyboard device: {kbd_path}")
            except (PermissionError, FileNotFoundError, OSError) as e:
                log.warning(f"Warning: Cannot access keyboard device {kbd_path}: {e}")
                log.warning("Try running: sudo usermod -a -G input $USER (then log out and back in)")
                log.warning("Or use --no-key-listener to disable keyboard monitoring.")
                args.no_key_listener = True
                device = None
        else:
            log.warning("Warning: Could not find a suitable keyboard device for evdev monitoring.")
            log.warning("Key listening will be limited to pynput only (if available).")
            device = None

    ################################################################################
    ### Parse config file to enable control of apps by quadrant and by time slice ##
    ################################################################################
    config = get_config()
    duration = config['duration'] #Default config to be applied if not set in an app
    quads = config['quadrants']
    top_left,  bottom_left, top_right, bottom_right, = \
        quads['top-left'], quads['bottom-left'], quads['top-right'], quads['bottom-right']
    
    # Track index of active app, for cycling through apps in a quadrant by time slice
    app_idx = defaultdict(int)
    for quad in quads:
        app_idx[quad] = 0
        
    # Each app optionally specifes how long it stays active before cycling to the next one
    app_duration = defaultdict(int)
    for quad in quads.items():
        for app in quad[1]:
            app_duration[app["name"]] = int(app.get("duration", duration))

    if args.list_apps:
        list_apps(base_apps, plugin_apps, quads)
        sys.exit()

    led_devices = discover_led_devices()
    if not len(led_devices):
        log.error("No LED devices found")
        sys.exit(0)
    elif len(led_devices) == 1:
        log.warning(f"Only one LED device found ({led_devices[0]}). Right panel args will be ignored")
    else:
        log.info(f"Found LED devices: Left: {led_devices[0]}, Right: {led_devices[1]}")
    locations = list(map(lambda x: x[0], led_devices))
    drawing_queues = []
    
    # Track key presses to reveal app ID in each quadrant or panel
    global alt_pressed
    alt_pressed = False
    global i_pressed
    i_pressed = False
    
    # Set up monitors and brightness parameters
    min_background_brightness = 12
    max_background_brightness = 35
    min_foreground_brightness = 24
    max_foreground_brightness = 160

    cpu_monitor = CPUMonitor()
    memory_monitor = MemoryMonitor()
    battery_monitor = BatteryMonitor()
    disk_monitor = DiskMonitor()
    network_monitor = NetworkMonitor()

    # Setup left panel drawing queue
    left_drawing_queue = queue.Queue(2)
    left_drawing_thread = DrawingThread(locations[0], left_drawing_queue)
    left_drawing_thread.set_animate(False)
    left_drawing_thread.start()    
    drawing_queues.append(left_drawing_queue)

    # Setup right panel drawing queue (if panel is present)
    if len(locations) == 2:
        right_drawing_queue = queue.Queue(2)
        right_drawing_thread = DrawingThread(locations[1], right_drawing_queue)
        right_drawing_thread.set_animate(False)
        right_drawing_thread.start()
        drawing_queues.append(right_drawing_queue)
    
    def draw_cpu(arg, grid, foreground_value, idx):
        last_cpu_values = cpu_monitor.get()
        draw_app(arg, grid, last_cpu_values, foreground_value, idx)
        
    def draw_mem_bat(arg, grid, foreground_value, idx):
        last_memory_values = memory_monitor.get()
        last_battery_values = battery_monitor.get()
        draw_app("mem", grid, last_memory_values, foreground_value, idx)
        draw_app("bat", grid, last_battery_values[0], last_battery_values[1], foreground_value, idx+3)
        
    def draw_disk(arg, grid, foreground_value, idx):
        last_disk_read, last_disk_write = disk_monitor.get()
        draw_app(arg, grid, last_disk_read, foreground_value, bar_x_offset=1, y=idx) # Read
        draw_app(arg, grid, last_disk_write, foreground_value, bar_x_offset=5, y=idx) # Write
        
    def draw_net(arg, grid, foreground_value, idx):
        last_network_upload, last_network_download = network_monitor.get()
        draw_app(arg, grid, last_network_upload, foreground_value, bar_x_offset=1, y=idx)
        draw_app(arg, grid, last_network_download, foreground_value, bar_x_offset=5, y=idx)
        
    def draw_snap(arg, grid, foreground_value, idx, **kwargs):
        draw_app(arg, grid, foreground_value, **kwargs)
        
    app_functions = {
        "cpu": draw_cpu,
        "mem-bat": draw_mem_bat,
        "disk": draw_disk,
        "net": draw_net,
        "snap": draw_snap,
        "none": lambda *x: x # noop
    }
    
    def on_press(key):
        global alt_pressed, i_pressed
        # If pynput is unavailable, this callback will not be used; guard anyway
        if not PYNPUT_AVAILABLE:
            return
        try:
            if getattr(key, 'char', None) == 'i':
                i_pressed = True
            elif Key is not None and key == Key.alt:
                alt_pressed = True
        except Exception:
            # Be defensive; ignore unexpected pynput key objects
            pass

    def on_release(key):
        global alt_pressed, i_pressed
        if not PYNPUT_AVAILABLE:
            return
        try:
            if getattr(key, 'char', None) == 'i':
                i_pressed = False
            elif Key is not None and key == Key.alt:
                alt_pressed = False
            if Key is not None and key == Key.esc:
                # Stop listener
                return False
        except Exception:
            pass
        
    #################################################
    ###      Load app functions from plugins      ###
    #################################################
    if not re.search(r"--disable-plugins|-dp", str(sys.argv)):
        # Try to find plugins directory - either in current dir or installed location
        import os.path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        plugins_dir = os.path.join(current_dir, 'plugins')
        if not os.path.exists(plugins_dir):
            plugins_dir = './plugins/'
        for file in os.listdir(plugins_dir):
            if file.endswith('_plugin.py'):
                module_name = re.sub("_plugin.py", "", file)
                file_path = os.path.join(plugins_dir, file)
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)

                for obj in module.app_funcs:
                    app_functions[obj["name"]] = obj["fn"]


    # Track last draw time, to enable cycling through them for each quadrannt
    base_time_map = {
        # Each dict stores last draw time for each app
        'top-left': defaultdict(lambda: time.monotonic()),
        'bottom-left': defaultdict(lambda: time.monotonic()),
        'top-right': defaultdict(lambda: time.monotonic()),
        'bottom-right': defaultdict(lambda: time.monotonic()),
    }

    # Used to detect that the key listener was activated, for restoring anination mode after ID display
    global latch_key_combo
    latch_key_combo = False
    def render_iteration(args):
        global latch_key_combo
        try:
            screen_brightness = get_monitor_brightness()
            background_value = int(screen_brightness * (max_background_brightness - min_background_brightness) + min_background_brightness)
            foreground_value = int(screen_brightness * (max_foreground_brightness - min_foreground_brightness) + min_foreground_brightness)

            # Clamp brightness values to the valid byte range
            background_value = max(0, min(255, background_value))
            foreground_value = max(0, min(255, foreground_value))

            grid = np.zeros((9,34), dtype = int)
            
            # Check for key combo using both evdev (if available) and pynput
            active_keys = device.active_keys(verbose=True) if device else []
            evdev_key_pressed = True if (MODIFIER_KEYS[0] in active_keys or MODIFIER_KEYS[1] in active_keys) and KEY_I in active_keys and device else False
            pynput_key_pressed = i_pressed and alt_pressed
            key_combo_active = (evdev_key_pressed or pynput_key_pressed) and not args.no_key_listener

            # Track when an app is changed in either panel, used to manage animation state
            idx_changed = {
                left_drawing_queue: False,
                right_drawing_queue: False
            }
            for quadrant,apps in quads.items():
                    app = apps[app_idx[quadrant]]
                    if time.monotonic() - base_time_map[quadrant][app['name']] >= int(app_duration[app['name']]):
                        if 'left' in quadrant:
                            idx_changed[left_drawing_queue] = True
                        else:
                            idx_changed[right_drawing_queue] = True
                        app_idx[quadrant] = (app_idx[quadrant] + 1) % len(quads[quadrant])
                        app = apps[app_idx[quadrant]]
                        base_time_map[quadrant][app['name']] = time.monotonic()

            left_args = [
                top_left[app_idx['top-left']],
                bottom_left[app_idx['bottom-left']],
            ]

            right_args = [
                top_right[app_idx['top-right']],
                bottom_right[app_idx['bottom-right']]
            ]

            # Capture animating state so we can restart it if necessary after stopping it for ID display
            animating_left = left_args[0].get("animate", False) or left_args[1].get("animate", False)
            animating_right = right_args[0].get("animate", False) or right_args[1].get("animate", False)
            
            if key_combo_active:
                # Show app IDs for each quadrant or panel
                draw_outline_border(grid, background_value)
                #If app takes up entire panel, we draw the ID differently
                if left_args[0].get("scope", None) == "panel":
                    draw_id(grid, left_args[0]['name'], foreground_value, args=left_args[0].get('args', None))
                else:
                    draw_ids(grid, left_args[0]['name'], left_args[1]['name'], foreground_value,
                        targs=left_args[0].get('args', None), bargs=left_args[1].get('args', None))
                left_drawing_queue.put((grid, False))
                
                if len(drawing_queues) > 1:  # Right panel exists
                    grid = np.zeros((9,34), dtype = int)
                    draw_outline_border(grid, background_value)
                    if right_args[0].get("scope", None) == "panel":
                        draw_id(grid, right_args[0]['name'], foreground_value, args=right_args[0].get('args', None))
                    else:
                        draw_ids(grid, right_args[0]['name'], right_args[1]['name'], foreground_value,
                            targs=right_args[0].get('args', None), bargs=right_args[0].get('args', None))
                    right_drawing_queue.put((grid, False))
                time.sleep(0.1)
                latch_key_combo = True
                return
            
            for i, draw_queue in enumerate(drawing_queues):
                grid = np.zeros((9,34), dtype = int)
                if i == 0:
                    panel = 'left'
                    _args = left_args
                else:
                    panel = 'right'
                    _args = right_args
                for j, arg in enumerate(_args):
                    arg_name = arg['name']
                    if arg.get("display", True) == False: continue
                    if j == 0:
                        idx = 0
                        loc = 'top'
                    else:
                        idx = 16
                        loc = 'bottom'
                    try:
                        func = app_functions[arg_name]
                        func_args = [arg_name, grid, foreground_value, idx]
                        kwargs = {}
                        if 'args' in arg:
                            #Args must be hashable, to support function caching, so convert any list values in dicts to tuples
                            kwargs = {k: tuple(v) if isinstance(v, list) else v for k, v in arg['args'].items()}
                        func(*func_args, **kwargs)
                        animate = arg.get("animate", False)
                    except KeyError:
                        log.error(f"Unrecognized app {arg_name} for {loc} {panel}")
                    except Exception as e:
                        log.error(f"Error {e} with app {arg_name} for {loc} {panel}")
                        traceback.print_exc()
                    # Single border draw for mem and bat together
                    if arg_name == 'mem-bat': arg_name = 'mem'
                    draw_app_border(arg_name, grid, background_value, idx)
                do_animate = None
                if idx_changed[draw_queue]:
                    do_animate = animate
                    idx_changed[draw_queue] = False
                # Restart animation if it was stopped for ID display
                if latch_key_combo:
                    if (animating_left and panel == 'left') or (animating_right and panel == 'right'):
                        do_animate = True
                draw_queue.put((grid, do_animate))
            latch_key_combo = False
            time.sleep(0.1)     
        except KeyboardInterrupt:
            raise
        except Exception as e:
            log.error(f"Error in main loop: {e}")
            traceback.print_exc()
            time.sleep(1.0)
            
    # Informative message if pynput is not available
    if not PYNPUT_AVAILABLE and not args.no_key_listener:
        log.warning("Info: pynput is unavailable; running in evdev-only mode. Use Ctrl+C to exit.")

    # Prefer pynput if available; fall back silently if it fails to start (common on Wayland)
    if PYNPUT_AVAILABLE and not args.no_key_listener:
        try:
            with Listener(on_press=on_press, on_release=on_release):
                while True:
                    render_iteration(args)
        except Exception as e:
            log.error(f"Warning: pynput listener could not be started ({e}). Falling back to evdev-only mode.")
            while True:
                render_iteration(args)
    else:
        while True:
            render_iteration(args)

    log.info("Exiting")

def main(args):
    base_apps = ["cpu", "net", "disk", "mem-bat", "snap"]
    plugin_apps = []
    ###############################################################
    ###  Load additional app names from plugins for listing insalled apps  ###
    if not re.search(r"--disable-plugins|-dp", str(sys.argv)):
        # Try to find plugins directory - either in current dir or installed location
        import os.path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        plugins_dir = os.path.join(current_dir, 'plugins')
        if not os.path.exists(plugins_dir):
            plugins_dir = './plugins/'
        for file in os.listdir(plugins_dir):
            if file.endswith('_plugin.py'):
                module_name = re.sub("_plugin.py", "", file)
                file_path = os.path.join(plugins_dir, file)
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
                plugin_apps += map(lambda o: o["name"], module.app_funcs)
    #################################################################
    parser = ArgumentParser(prog="FW LED System Monitor", add_help=False,
                            description="Displays system performance metrics in the Framework 16 LED Matrix input module",
                            formatter_class=ArgumentDefaultsHelpFormatter)
    mode_group = parser.add_argument_group()
    mode_group.add_argument("--help", "-h", action="help",
        help="Show this help message and exit")
    
    mode_group.add_argument("--no-key-listener", "-nkl", action="store_true", help="Do not listen for key presses")
    mode_group.add_argument("--disable-plugins", "-dp", action="store_true", help="Do not load any plugin code")
    mode_group.add_argument("--list-apps", "-la", action="store_true", help="List the installed apps, and exit")
    
    args = parser.parse_args()
    if args.no_key_listener: print("Key listener disabled")
    app(args, base_apps, plugin_apps)

if __name__ == "__main__":
    level = logging.WARNING
    if os.getenv("LOG_LEVEL", "").lower() == "debug":
        level = logging.DEBUG
    elif os.getenv("LOG_LEVEL", "").lower() == "error":
        level = logging.ERROR
    elif os.getenv("LOG_LEVEL", "").lower() == "info":
        level = logging.INFO

    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    main(sys.argv)

