# Built In Dependencies
import time
import math
import threading
import importlib.util
import sys
import os
import re
import json
import logging

# Internal Dependencies
from commands import Commands, send_command, do_animate
from patterns import lightning_bolt_bot, lightning_bolt_top, lookup_table, id_patterns, symbols, numerals, icons

# External Dependencies
import numpy as np
import serial # pyserial
from serial.tools import list_ports

log = logging.getLogger(__name__)

# Correct table orientation for visual orientation when drawn
for i in range(lookup_table.shape[0]):
    lookup_table[i] = lookup_table[i].T


def spiral_index(fill_ratio):
    return int(round(fill_ratio * 9.999999 - 0.5))

## App Draw Functions ##

# Takes up 15 rows, 7 columns, starting at y,1
# For bottom segment, the 16th row will be empty
def draw_spiral_vals(grid, cpu_values, fill_value, y):
    y += 1
    for i, v in enumerate(cpu_values):
        column_number = i % 2
        row_number = i // 2
        fill_grid = lookup_table[spiral_index(v)]
        grid[1+column_number*4:4+column_number*4, y+row_number*4:y+3+row_number*4] = fill_grid * fill_value

# Takes up 2 rows, 7 columns, starting at y, 1
def draw_memory(grid, memory_ratio, fill_value, y):
    lit_pixels = 7 * 2 * memory_ratio
    pixels_bottom = int(round(lit_pixels / 2))
    pixels_top = int(round((lit_pixels - 0.49) / 2))
    grid[1:1+pixels_top,y+1] = fill_value
    grid[1:1+pixels_bottom,y+2] = fill_value

# Takes up 12 (top segment) or 13 (bottom segment) rows, 7 columns, starting at y,1
def draw_battery(grid, battery_ratio, battery_plugged, fill_value, y,
        battery_low_thresh = 0.07, battery_low_flash_time = 2, charging_pulse_time = 3):
    if y == 19: # Placement on bottom
        bot = 33
        num_rows = 13
        lightning_bolt = lightning_bolt_bot
    else: # Placement on top (y == 3)
        bot = 16
        num_rows = 12
        lightning_bolt = lightning_bolt_top
    bat_top = y + 1
    bat_bot = bat_top + num_rows
    lit_pixels = int(round(num_rows * 7 * battery_ratio))
    pixels_base = lit_pixels // 7
    remainder = lit_pixels % 7
    if battery_ratio <= battery_low_thresh and not battery_plugged:
        if time.time() % battery_low_flash_time * 2 < battery_low_flash_time: # This will flash the battery indicator if too low
            return
    for i in range(7):
        pixels_col = pixels_base
        if i < remainder:
            pixels_col += 1
        grid[i+1,bot-pixels_col:bot] = fill_value
    if battery_plugged:
        pulse_amount = math.sin(time.time() / charging_pulse_time)
        grid[1:8,bat_top:bat_bot][lightning_bolt] -= np.rint(fill_value + 10 * pulse_amount).astype(int)
        indices = grid[1:8,bat_top:bat_bot] < 0
        grid[1:8,bat_top:bat_bot][indices] = -grid[1:8,bat_top:bat_bot][indices]
    
# Takes up 16 (top segment) or 17 (bottom segment) rows, 3 columns, starting at y,1
def draw_bar(grid, bar_ratio, bar_value, bar_x_offset = 1, y=0):
    bar_width = 3
    bar_height = 16
    lit_pixels = int(round(bar_height * bar_width * bar_ratio))
    pixels_base = lit_pixels // bar_width
    remainder = lit_pixels % bar_width
    for i in range(bar_width):
        pixels_col = pixels_base
        if i < remainder:
            pixels_col += 1
        if y == 16:
            grid[bar_x_offset+i,33-pixels_col:33] = bar_value
        else:
            grid[bar_x_offset+i,1:1+pixels_col] = bar_value
            
warned = set()
def draw_snapshot(grid, fill_value, **kwargs):
    global warned
    path = kwargs.get('path', None)
    panel = kwargs.get('panel', None)
    file = kwargs.get('file', None)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(current_dir, path)
    subdirs = [ f.name for f in os.scandir(path) if f.is_dir() and f.name in ['left', 'right']]
    subdir = panel if panel in subdirs else ''
    try:
        with open(os.path.join(path, subdir, file)) as f:
            snap = json.load(f)
            grid[:,:] = np.array(snap).T * fill_value
    except FileNotFoundError as e:
        if not file in warned:
            print(f"File {file} not found")
            warned.add(file)

def draw_chars(grid: np.ndarray, chars: list[str], fill_value: int, y: int):
    char_map = {**numerals, **symbols, **icons}
    grid = grid.T
    for char in chars:
        if char in char_map:
            try:
                l = len(char_map[char])
                # For three-digit temps (e.g. with Kelvin) only part of the condition icon can be rendered
                grid[y:y+l, :] = char_map[char][:34-y] * fill_value
                y += l + 1 # +1 for spacing
            except KeyError:
                raise Exception(f"Character {char} not found in numerals, symbols, or icons dictionary")
            except Exception as e:
                raise e
    grid = grid.T
    
    
## Border Draw Functions ##
    
# Draws a border around a 16 (top segment) or a 17 (bottom segment)
# x 9 grid, divided into a 2 x 4 grid. For the bottom segment,
# the last grid will have an extra row
def draw_8_x_8_grid(grid, border_value, y):
    height = 16 if y == 0 else 17
    grid[:, y] = border_value # Top
    grid[:, y+height] = border_value # Bottom
    
    grid[0, y:y+height] = border_value # Left
    grid[8, y:y+height] = border_value # Right
    grid[4, y:y+height] = border_value # Middle
    
    # Horizontal grid borders
    grid[:, y+4] = border_value
    grid[:, y+8] = border_value
    grid[:, y+12] = border_value
    
# Draws a border around a 16 (top segment) or a 17 (bottom segment)
# x 9 grid, split horizontally into two sections at the specified column
def draw_2_x_1_horiz_grid(grid, border_value, y, x_split_idx=4):
    height = 16 if y == 0 else 17
    grid[:, y] = border_value # Top
    grid[:, y+height] = border_value # Bottom

    grid[0, y:y+height] = border_value # Left
    grid[8, y:y+height] = border_value # Right
    grid[x_split_idx, y:y+height] = border_value # Middle
    
# Draws a border around a 16 (top segment) or a 17 (bottom segment),
# row section, split vertically into two sections at the specified row
def draw_1_x_2_vert_grid(grid, border_value, y, y_split_idx = 3):
    height = 16 if y == 0 else 17
    grid[:, y] = border_value # Top
    grid[:, y+height] = border_value # Bottom
    grid[:, y+y_split_idx] = border_value # Middle

    grid[0, y:y+height] = border_value # Left
    grid[8, y:y+height] = border_value # Right
    
# Draws a border around the entire panel, split
# vertically into two equal segments
def draw_outline_border(grid, border_value):
    grid[:, 0] = border_value # Top
    grid[:, 16] = border_value # Middle
    grid[:, 33] = border_value # Bottom
    grid[0, :] = border_value # Left
    grid[8, :] = border_value # Right
    
# Maps an app arg value to abstract app and border draw functions
direct_draw_funcs = {
    "cpu": {
        "fn": draw_spiral_vals,
        "border": draw_8_x_8_grid
    },
    "disk": {
        "fn": draw_bar,
        "border": draw_2_x_1_horiz_grid
    },
    "net": {
        "fn": draw_bar,
        "border": draw_2_x_1_horiz_grid
    },
    "mem": {
        "fn": draw_memory,
        "border": draw_1_x_2_vert_grid
    },
    "bat": {
        "fn": draw_battery,
        "border": draw_1_x_2_vert_grid
    },
    "snap": {
        "fn": draw_snapshot,
        "border": lambda *x: None # No border
    },
    #noop
    "none": {
        "fn": lambda *x: x,
        "border": lambda *x: x
    }
}

# Draws the app for the specified arg value
def draw_app(app, *arguments, **kwargs):
    direct_draw_funcs[app].get('fn')(*arguments, **kwargs)
    
# Draws the border for the specified arg value
def draw_app_border(app, *arguments):
    direct_draw_funcs[app].get('border')(*arguments)
            
# Draw the IDs of apps currently assigned to the top and bottom of a panel
def draw_ids(grid, top, bottom, fill_value, targs=None, bargs=None):
    if isinstance(targs, list):
        t_merged_dict = {k: v for d in targs if isinstance(d, dict) for k, v in d.items()}
        id_override = t_merged_dict.get('id_key_override', None)
        if id_override:
            if t_merged_dict.get(id_override[0], False):
                top = id_override[1]
            else:
                top = id_override[2]
        b_merged_dict = {k: v for d in bargs if isinstance(d, dict) for k, v in d.items()}
        id_override = b_merged_dict.get('id_key_override', None)
        if id_override:
            if b_merged_dict.get(id_override[0], False):
                bottom = id_override[1]
            else:
                bottom = id_override[2]
    fill_grid_top = id_patterns[top]
    fill_grid_bot = id_patterns[bottom]
    grid[1:8, 1:16] = fill_grid_top * fill_value
    grid[1:8, 18:-1] = fill_grid_bot * fill_value
    
# Draw the ID of the app currently assigned to the full panel
def draw_id(grid, id, fill_value, args=None):
    id_override = args.get('id_key_override', None)
    if id_override:
        if args.get(id_override[0], False):
            id = id_override[1]
        else:
            id = id_override[2]
    fill_grid = id_patterns[id]
    grid[:,:] = fill_grid * fill_value

def draw_to_LEDs(s, grid):
    # Ensure all values are valid bytes before sending
    safe_grid = np.clip(grid, 0, 255).astype(np.uint8)
    for i in range(safe_grid.shape[0]):
        params = bytearray([i]) + bytearray(safe_grid[i, :].tolist())
        send_command(s, Commands.StageCol, parameters=params)
    send_command(s, Commands.FlushCols)


def init_device(location = "1-3.2"):
    try:
        # VID = 1234
        # PID = 5678
        device_list = list_ports.comports()
        for device in device_list:
            if device.location and device.location.startswith(location):
                s = serial.Serial(device.device, 115200)
                return s
        log.error('Error getting comm ports for LED panel USB devices')
        sys.exit(1)
    except Exception as e:
        print(e)


class DrawingThread(threading.Thread):
    def __init__(self, port_location, input_queue):
        super().__init__()
        self.daemon = True
        self.port_location = port_location
        self.serial_port = init_device(self.port_location)
        self.input_queue = input_queue
        self.animate_active= False

    def set_animate(self, animate):
        do_animate(self.serial_port, animate=animate)
    
    def run(self):
        while True:
            try:
                grid, animate = self.input_queue.get()
                if not self.animate_active:
                    draw_to_LEDs(self.serial_port, grid)
                if animate is not None:
                    self.animate_active = animate
                    do_animate(self.serial_port, animate)

            except Exception as e:
                print(f"Error in DrawingThread: {e}")
                del self.serial_port
                time.sleep(1.0)
                self.serial_port = init_device(self.port_location)
                
###############################################################
###           Load metrics functions from plugins           ###
###############################################################
# Keep this at the end of the module to avoid circular imports
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

            for k,v in module.direct_draw_funcs.items():
                direct_draw_funcs[k] = v
                
            from drawing import id_patterns
            for k,v in module.id_patterns.items():
                id_patterns[k] = v
            
################################################################

