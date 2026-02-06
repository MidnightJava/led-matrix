# Built In Dependencies
from statistics import mean
import requests
import os
from zoneinfo import ZoneInfo
from datetime import datetime, timedelta
import numpy as np
import threading
import logging
from collections import defaultdict

# Internal dependencies
from led_mon.patterns import icons, letters_5_x_6
from led_mon import drawing
from led_mon.equalizer_files.visualize import Equalizer
from led_mon.led_system_monitor import discover_led_devices

log = logging.getLogger(__name__)
LOG_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
}

log_level = LOG_LEVELS[os.environ.get("LOG_LEVEL", "warning").lower()]
log.setLevel(log_level)


### Helper functions ###



####  Monitor functions ####

equalizers = {}

def run_equalizer(_, grid, foreground_value, idx, **kwargs):
    external_filter = kwargs['external-filter']
    device = kwargs['device']
    # device = ('<port>', '<name>')
    devices: tuple[str, str] = discover_led_devices()
    if device == 'left':
        channel = 0
        device_name = devices[0][1]
    elif kwargs['device'] == 'right':
        channel = 1
        device_name = devices[1][1]
    else:
        log.error(f"Unexpected device arg {kwargs['device']}")
    if not device in equalizers:
        equalizers[device] = Equalizer()
        eq_thread = threading.Thread(target=lambda: equalizers[device].run(channel=channel, external_filter=external_filter, device_name=device_name), daemon=True)
        eq_thread.start()
    
def dispose_equalizer(**kwargs):
    device = kwargs
    equalizers[device].stop()
    del equalizers[device]

#### Implement high-level drawing functions to be called by app functions below ####

draw_app = getattr(drawing, 'draw_app')

    
def run_equaizer(arg, grid, foreground_value, idx, **kwargs):
    panel = kwargs['panel']
    use_external_filter = kwargs['external-filter']

#### Implement low-level drawing functions ####
# These functions will be dynamically imported by drawing.py and called by their corresponding app function

# No implementations needed since scrit draws continuoulsy on grid until dispose function is called
direct_draw_funcs = {
    "equalizer": {
        "fn": lambda *x: None,
        "border":lambda *x: None
    }
}

# Implement app functions that call your direct_draw functions
# These functions will be dynamically imported by led_system_monitor.py. They call the direct_draw_funcs
# defined above, providing additional capabilities that can be targeted to panel quadrants

app_funcs = [
    {
        "name": "equalizer",
        "fn": run_equalizer
    },
    {
        "name": "equalizer_dispose",
        "fn": dispose_equalizer
    }
]

# Provide id patterns that identify your apps
# These items will be dynamically imported by drawing.py

id_patterns = {
    "time": np.concatenate((np.zeros((2,9)), letters_5_x_6["T"], np.zeros((2,9)), letters_5_x_6["I"], np.zeros((2,9)),letters_5_x_6["M"], np.zeros((2,9)), letters_5_x_6["E"], np.zeros((2,9)))).T,
    "weather_current": np.concatenate((np.zeros((2,9)), letters_5_x_6["W"], np.zeros((2,9)), letters_5_x_6["T"], np.zeros((2,9)),letters_5_x_6["R"], np.zeros((2,9)), letters_5_x_6["C"], np.zeros((2,9)))).T,
    "weather_forecast": np.concatenate((np.zeros((2,9)), letters_5_x_6["W"], np.zeros((2,9)), letters_5_x_6["T"], np.zeros((2,9)),letters_5_x_6["R"], np.zeros((2,9)), letters_5_x_6["F"], np.zeros((2,9)))).T
}
