# Built In Dependencies
from statistics import mean
import os
import numpy as np
import threading
import logging

# Internal dependencies
from led_mon.patterns import letters_5_x_6, numerals
from led_mon import drawing
from led_mon.equalizer_files.visualize import Equalizer
from led_mon.shared_state import discover_led_devices

log = logging.getLogger(__name__)
LOG_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
}

log_level = LOG_LEVELS[os.environ.get("LOG_LEVEL", "warning").lower()]
log.setLevel(log_level)

####  Monitor functions ####

equalizers = {}

def run_equalizer(_, grid, foreground_value, idx, **kwargs):
    external_filter = kwargs['external-filter']
    side = kwargs['side']
    # device => ('<port>', '<name>')
    devices: tuple[str, str] = discover_led_devices()
    if side == 'left':
        channel = 0
        device = devices[0]
    elif side == 'right':
        channel = 1
        device = devices[1]
    else:
        log.error(f"Unexpected device arg {kwargs['device']}")
    if not side in equalizers:
        equalizers[side] = Equalizer(device_location = device[0])
        eq_thread = threading.Thread(target=lambda: equalizers[side].run(channel=channel, external_filter=external_filter, device_name=device[1]), daemon=True)
        eq_thread.start()
    if len(equalizers) > 2:
        log.info(f"run_equalizer: Active equalizers: {len(equalizers)}")
    
def dispose_equalizer(**kwargs):
    side = kwargs['side']
    if side in equalizers:
        equalizers[side].stop()
        # Optional (if resource leak found): Join to ensure clean exit
        # But since daemon, not strictly needed; helps for debugging
        # equalizers[side].drawing_thread.join(timeout=2)
        del equalizers[side]
    if len(equalizers) > 2:
        log.info(f"dispose_equalizer: Active equalizers: {len(equalizers)}")

#### Implement high-level drawing functions to be called by app functions below ####

draw_app = getattr(drawing, 'draw_app')

#### Implement low-level drawing functions ####
# These functions will be dynamically imported by drawing.py and called by their corresponding app function

# No implementations needed since the script draws continuoulsy on grid until dispose function is called
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
    "equalizer": np.concatenate((np.zeros((10,9)), letters_5_x_6["E"], np.zeros((2,9)), letters_5_x_6["Q"], np.zeros((10,9)))).T,
    "equalizer_paused": np.concatenate((np.zeros((5,9)), letters_5_x_6["E"], np.zeros((2,9)), letters_5_x_6["Q"],  np.zeros((3,9)), numerals["0"], np.zeros((5,9)))).T,

}
