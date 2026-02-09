# How to Develop LED System Monitor Plugins

## Overview
To extend the capabilities of the LED System Monitor app, you can develop plugins. A plugin consists of a single python script, placed in the `plugins` dir, with a file name corresponding to the pattern `<name>_plugin.py`, where name is whatever name you choose, so long as it's not already taken by a file in the `plugins` dir. Your plugin script needs to comply with certain requirements, to ensure the app can discover it and integrate it seamlessly into itself. The purpose of this document is to describe those requirements, using the `temp_fan_plugin.py` file as an example.

## Built In Dependencies (if applicable)
```
from statistics import mean
```

## Internal dependencies (if applicable)
```
from led_mon.patterns import letters_small
from led_mon import drawing
```

## External dependencies (if applicable)
```
import psutil
import numpy as np
```

## Class variables (if applicable)
```
TEMP_REF = 120

MAX_FAN_SPEED = 6_000
```

## Monitor functions
These are not required by the app, but may be called by other functions in your plugin. It's a recommended 
pattern to follow, especially for plugins that provide additional system performance widgets
```
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
```
## Specify app functions.

The main app (`led_system_monitor.py`) will discover the `app_funcs` list in every plugin and register all the functions described there, combining them with its own list of `app_funcs`. It will parse the `app_funcs` entries, which are pointers to other functions, as described velow.

- The `name` key should match the name for each app specified in the config file. For example, in the default `config.yaml`, one of the `app` items in the `top-right` list has the name `temp`. The app therefore expects to find a `name` key with the value `temp` in `app_funcs`. It will introspect the `app_funcs` list in the main app as well as in every contributed plugin. Therefore, the name chosen must be unique among all plugins and the app itself. It's easier to ensure there are no name conflicts if all developers choose app names at least loosely tied to their plugin function.

- The main app will invoke the function specified by the `fn` key. This function should most likely be provided in your plugin script, but you could import it from another script if you need to for some reason. If you do, be sure to guard against circular imports.
```
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
```

## Specify high-level drawing functions

- These functions correspond to the `fn` keys in the `app_funcs` list described above.

- The main app will invoke these functions disovered in `app_funcs`, passing the positional arguments you see specified below. Thus, your app must include these positional arguments, whether you intend to use them or not. You can rename them (or use `_`) if desired. If your app an `args` mapping in the config file, those key-value pairs will be passed as **kwargs as shown below (although in these examples, we don't make use of keyword args)

- Note that here we import `draw_app` from the `drawing` module and invoke it in the functions we define here. The first argument (`arg`) passed to the functions below is the name of your app (i.e. the value of the `name` key from `app_funcs`), and it is typically passed along to `draw_app` as shown below. Whatever value you pass, `draw_app` will expect to find a key with that name in the `direct_draw_funcs ` dictionary object given below, and it will invoke the corresponding function.

- You do not have to use `draw_app` as described here. You can define helper fuunctions in your plugin script and invoke those directly instead of using the `draw_app` -> `direct_draw_funcs` indirection. The main reason for doing the latter is to take advantage of predefined functions for drawing on the grid, as illustratred below in information about `direct_draw_funcs`.

- Here is the meaning of the args passed by the main app to the app functions below:
    - arg: the name of the app, as specified in `config.yaml` and in the `name` key in `app_funcs`
    - grid: the drawing grid. Update this numpy array with the values to be rendered. The main app will then submit it to the drawing queue for rendering on the LED panel.
    - foreground_value: the brightness level at which all pixels in `grid` will be rendered for this function iteration.
    - idx: the vertical index at which the app will be rendered. For half-panel apps, it will be 0 for the top quadrant and 16 for the bottom. For full-panel apps, it will be 0.
    - kwargs: the app arguments specified in the `args` mapping for the app in `config.yaml`.
```
draw_app = getattr(drawing, 'draw_app')

def draw_temps(arg, grid, foreground_value, idx, **kwargs):
    temp_values = temperature_monitor.get()
    draw_app(arg, grid, temp_values, foreground_value, idx)
        
def draw_fans(arg, grid, foreground_value, idx, **kwargs):
    fan_speeds = fan_speed_monitor.get()
    draw_app(arg, grid, fan_speeds[0], foreground_value, bar_x_offset=1, y=idx)
    draw_app(arg, grid, fan_speeds[1], foreground_value, bar_x_offset=5, y=idx)
```
# Speficy Direct-Draw apps (optional)

- As explained above, functions specified here will be called by the imported `draw_app` function, if you choose to take advantage of predefined low-level drawing apps. Below you see that we import some functions that draw specific patterns. These functions are then specified in `direct_draw_funcs` and invoked by `draw_app`. The arguments passed to `draw_app` as shown above will be passed to the corresponding function specified in `direct_draw_funcs`.

- The function specified by the `fn` key will be called to draw the widget values, and the function specified by the `border` key will be called to draw the widget's border. You must provide a `border` entry even if you don't want your widget to draw a border. In that case, specify `lambda *x: None` for the `border` value.
```
draw_spiral_vals = getattr(drawing, 'draw_spiral_vals')
draw_8_x_8_grid = getattr(drawing, 'draw_8_x_8_grid')
draw_bar = getattr(drawing, 'draw_bar')
draw_2_x_1_horiz_grid = getattr(drawing, 'draw_2_x_1_horiz_grid')


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
```
## Specify ID patterns to be displayed in place of your widget's rendering when you press the ID key combo (i.e. Alt-I)

- The key values here should match the name of your app, as defined in the config file. However, see comments in `confg.yaml` for a way to override the key values if you want your app to support multiple ID values depending on its current configuration.

- ID patterns are specified as a numpy array. You can build that array any way you like, but the imported `letters_small` object is a convenient way to do it. That is, if your widget takes up a half-panel. For full-panel widgets, you may want to use the `letters_5_x_6` object from the `patterns` module.

- The array you return must be no more than 34 rows high and 9 columns wide. The syntax used below is (row, col). Thus you can provide the desired vertical spacing by inserting zero-filled array between the numbers with the desired height. The `(1,7)` tuples inserted below provide one-row vertical spacing for the letters of the ID.
```
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
```
## Summary

The indirection in the scheme described above may be hard to follow. Here is a succint recapitulation of the function invocation flow.

- The `name` value for a given app is read from the config file. This will be used to invoke the function with that `name` key in `app_funcs`.

- The function thus invoked may either:
    - call helper functions in your plugin, or
    - Call `draw_app` imported from the `drawing` module
    - If `drap_app` is called, it will call the function from `direct_draw_funcs` whose `name` key matches the first positional argument (`arg`) passed to `draw_app`. The main reason to do this is to take advantage of pre-defined low-level fdrawing functions.

- Specify the ID charatcers to be displayed for the app in the `id_patterns` object.