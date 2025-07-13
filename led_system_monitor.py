# Built In Dependencies
import time
import queue
import sys
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from serial.tools import list_ports


# Internal Dependencies
from drawing import draw_outline_border, draw_ids_left, draw_ids_right, draw_app, draw_app_border, DrawingThread
from monitors import CPUMonitor, MemoryMonitor, BatteryMonitor, DiskMonitor, NetworkMonitor, \
    TemperatureMonitor, FanSpeedMonitor, get_monitor_brightness

# External Dependencies
import numpy as np
from pynput.keyboard import Key, Listener

def discover_led_devices():
    locations = []
    try:
        device_list = list_ports.comports()
        for device in device_list:
            if 'LED Matrix Input Module' in str(device):
                locations.append((device.location, device.device))
        return sorted(locations, key = lambda x: x[0])
    except Exception as e:
        print(f"An Exception occured while tring to locate LED Matrix devices. {e}")


def main(args):    
    led_devices = discover_led_devices()
    if not len(led_devices):
        print("No LED devices found")
        sys.exit(0)
    print(f"Found LED devices: Left: {led_devices[0][1]}, Right: {led_devices[1][1]}")
    locations = list(map(lambda x: x[0], led_devices))
    
    # Track key presses to reveal metrics ID in each panel section
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
    temperature_monitor = TemperatureMonitor()
    fan_speed_monitor = FanSpeedMonitor()
    disk_monitor = DiskMonitor()
    network_monitor = NetworkMonitor()

    # Setuop left panel drawing queue
    left_drawing_queue = queue.Queue(2)
    left_drawing_thread = DrawingThread(locations[0], left_drawing_queue)
    left_drawing_thread.start()    

    # Setup right panel drawing queue
    right_drawing_queue = queue.Queue(2)
    right_drawing_thread = DrawingThread(locations[1], right_drawing_queue)
    right_drawing_thread.start()
    
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
        
    def draw_temps(arg, grid, foreground_value, idx):
        temp_values = temperature_monitor.get()
        draw_app(arg, grid, temp_values, foreground_value, idx)
        
    def draw_fans(arg, grid, foreground_value, idx):
        fan_speeds = fan_speed_monitor.get()
        draw_app(arg, grid, fan_speeds[0], foreground_value, bar_x_offset=1, y=idx)
        draw_app(arg, grid, fan_speeds[1], foreground_value, bar_x_offset=5, y=idx)
    
        
    app_functions = {
        "cpu": draw_cpu,
        "temp": draw_temps,
        "mem-bat": draw_mem_bat,
        "fan": draw_fans,
        "disk": draw_disk,
        "net": draw_net
    }
        
    def on_press(key):
        global alt_pressed
        global i_pressed
        if type(key).__name__ == 'KeyCode':
            if key.char == 'i':
                i_pressed = True
        elif key == Key.alt:
            alt_pressed = True

    def on_release(key):
        global alt_pressed
        global i_pressed
        if type(key).__name__ == 'KeyCode':
            if key.char == 'i':
                i_pressed = False
        elif key == Key.alt:
            alt_pressed = False
        if key == Key.esc:
            # Stop listener
            return False
        
    with Listener(
        on_press=on_press,
        on_release=on_release):
        while True:
            try:
                screen_brightness = get_monitor_brightness()
                background_value = int(screen_brightness * (max_background_brightness - min_background_brightness) + min_background_brightness)
                foreground_value = int(screen_brightness * (max_foreground_brightness - min_foreground_brightness) + min_foreground_brightness)
                grid = np.zeros((9,34), dtype = int)
                if i_pressed and alt_pressed:
                    draw_outline_border(grid, background_value)
                    draw_ids_left(grid, args.top_left, args.bottom_left, foreground_value)
                    left_drawing_queue.put(grid)
                    grid = np.zeros((9,34), dtype = int)
                    draw_outline_border(grid, background_value)
                    draw_ids_right(grid, args.top_right, args.bottom_right, foreground_value)
                    right_drawing_queue.put(grid)
                    grid = np.zeros((9,34), dtype = int)
                    time.sleep(0.1)
                    continue

                # Draw by quadrants (i.e. to top and bottom of left and right panels)
                for i, draw_queue in enumerate([left_drawing_queue, right_drawing_queue]):
                    if i == 0:
                        panel = 'left'
                        _args = [args.top_left, args.bottom_left]
                    else:
                        panel = 'right'
                        _args = [args.top_right, args.bottom_right]
                    grid = np.zeros((9,34), dtype = int)
                    for j, arg in enumerate(_args):
                        if j == 0:
                            idx = 1
                            loc = 'top'
                        else:
                            idx = 17
                            loc = 'bottom'
                        try:
                            app_functions[arg](arg, grid, foreground_value, idx)
                        except KeyError:
                            print(f"Unrecognized display option {arg} for {loc} {panel}")
                        if arg == 'mem-bat': arg = 'mem' # Single border draw for mem and bat together
                        draw_app_border(arg, grid, background_value, idx)
                    draw_queue.put(grid)
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                import traceback
                print(f"Error in main loop: {e}")
                traceback.print_exc()
                time.sleep(1.0)
            time.sleep(0.1)
            
        print("Exiting")
        
if __name__ == "__main__":
    parser = ArgumentParser(prog="FW LED System Monitor", add_help=False,
                            description="Displays system performance metrics in the Framework 16 LED Matrix input module",
                            formatter_class=ArgumentDefaultsHelpFormatter)
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("-h", "--help", action="help",
                         help="Show this help message and exit")
    
    addGroup = parser.add_argument_group(title = "Metrics Display Options")
    addGroup.add_argument("-tl", "--top-left", type=str, default="cpu", choices=["cpu", "net","fan", "temp", "disk", "mem-bat"],
                         help="Metrics to display in the top section of the left matrix panel")
    addGroup.add_argument("-bl", "--bottom-left", type=str, default="mem-bat", choices=["cpu", "net","fan", "temp", "disk", "mem-bat"],
                         help="Metrics to display in the bottom section of the left matrix panel")
    addGroup.add_argument("-tr", "--top-right", type=str, default="disk", choices=["cpu", "net","fan", "temp", "disk", "mem-bat"],
                         help="Metrics to display in the top section of the right matrix panel")
    addGroup.add_argument("-br", "--bottom-right", type=str, default="net", choices=["cpu", "net","fan", "temp", "disk", "mem-bat"],
                         help="Metrics to display in the bottom section of the right matrix panel")
    
    args = parser.parse_args()
    print(f"top left {args.top_left}")
    print(f"bottom left {args.bottom_left}")
    print(f"top right {args.top_right}")
    print(f"bottom right {args.bottom_right}")
    
    main(args)
    
""" 
options for reading keyboard (see https://stackoverflow.com/questions/24072790/how-to-detect-key-presses):

pynput: Uses x-server and was failing to connect as root. Resolved this with changes to run.sh and install_as_service
Other options conisdered, all had show-stopping drawbacks:
- evdev: No Windows support. Causes keyboard reboot with rapid typing in Linux
- sshkeyboard: Does not support multiple keypresses (will consider one released when the other is pressed) and does not read ctrl, alt, etc
- keyboard: Requires root access just to call the library, regardless of permissions on keyboard device. Does not hook keyboard globally.
"""