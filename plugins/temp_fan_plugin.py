from statistics import mean
import psutil
import numpy as np
from patterns import letters_small

# Reference for fractional measure of sensor temps (in degrees Celcius)
TEMP_REF = 120

# Reference for fractional measure of fan speeds (in rpm)
MAX_FAN_SPEED = 6_000

#### Implement monitor functions ####

class TemperatureMonitor:
    @staticmethod
    def get():
        temps = []
        sensors = psutil.sensors_temperatures()
        for _, entries in sensors.items():
            temps.append(mean([entry.current for entry in entries if entry.current > 0]))
        # We can handle up to eight temps on the matrix display
        _temps = list(map(lambda x: x / TEMP_REF, temps))
        return list(map(lambda x: x / TEMP_REF, temps))[:8]
    
class FanSpeedMonitor:
    @staticmethod
    def get():
        fans = psutil.sensors_fans()
        speeds = []
        for _, entries in fans.items():
            for entry in entries:
                speeds.append(entry.current)
        # We can handle up to two fan speeds on the matrix display
        return list(map(lambda x: x / MAX_FAN_SPEED, speeds))[:2]
    
temperature_monitor = TemperatureMonitor()
fan_speed_monitor = FanSpeedMonitor()

#### Implement high-level drawing functions to be called by app functions below ####

import drawing
draw_app = getattr(drawing, 'draw_app')

def draw_temps(arg, grid, foreground_value, idx):
    temp_values = temperature_monitor.get()
    draw_app(arg, grid, temp_values, foreground_value, idx)
        
def draw_fans(arg, grid, foreground_value, idx):
    fan_speeds = fan_speed_monitor.get()
    draw_app(arg, grid, fan_speeds[0], foreground_value, bar_x_offset=1, y=idx)
    draw_app(arg, grid, fan_speeds[1], foreground_value, bar_x_offset=5, y=idx)
    

draw_spiral_vals = getattr(drawing, 'draw_spiral_vals')
draw_8_x_8_grid = getattr(drawing, 'draw_8_x_8_grid')
draw_bar = getattr(drawing, 'draw_bar')
draw_2_x_1_horiz_grid = getattr(drawing, 'draw_2_x_1_horiz_grid')

#### Implement low-level drawing functions ####
# These functions will be dynamically imported by drawing.py and called by their correcsponding app function

direct_draw_funcs = {
    "temp": {
        "fn": draw_spiral_vals,
        "border": draw_8_x_8_grid
    },
    "fan": {
        "fn": draw_bar,
        "border": draw_2_x_1_horiz_grid
    }
}

# Implement app functions that call your direct_draw functions
# These functions will be dynamically imported by led_system_monitor.py. They call the direct_draw_funcs
# defined above, providing additional capabilities that can be targeted to panel quadrants

app_funcs = [
    {
        "name": "temp",
        "fn": draw_temps
    },
    {
        "name": "fan",
        "fn":   draw_fans
    }
]

# Provide id patterns that identify your apps
# These items will be dynamically imported by drawing.py

id_patterns = {
    "temp": np.concatenate((
        letters_small["T"],
        np.zeros((1,7)),
        letters_small["M"],
        np.zeros((1,7)),
        letters_small["P"])).T,
    "fan": np.concatenate((
        letters_small["F"],
        np.zeros((1,7)),
        letters_small["A"],
        np.zeros((1,7)),
        letters_small["N"],
        np.zeros((1,7)))).T,
}