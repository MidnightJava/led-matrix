# Built In Dependencies
from collections import namedtuple
import requests
import os
import time
from zoneinfo import ZoneInfo
from datetime import datetime, timedelta
import numpy as np
from functools import cache
from threading import Timer
import logging
from enum import Enum

# Internal dependencies
from led_mon.patterns import icons, letters_5_x_6
from led_mon import drawing

Weather = namedtuple('Weather', ['Weather', 'temp', 'wind_chill', 'wind_speed', 'wind_speed_symbol', 'wind_dir', 'temp_symbol', 'condition'])

OPENWEATHER_HOST = 'https://api.openweathermap.org'
IPIFY_HOST = 'https://api.ipify.org'

log = logging.getLogger(__name__)
LOG_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
}

log_level = LOG_LEVELS[os.environ.get("LOG_LEVEL", "warning").lower()]
log.setLevel(log_level)

class Measures(Enum):
    TEMP_COND = 'temp_condition'
    WIND_CHILL = 'wind_chill'
    WIND = 'wind'
    



### Helper functions ###

@cache
# Cache results so we avoid exceeding the API rate limit
# No need to invalidate cache since location per given zip is fixed
def get_location_by_zip(zip_info, weather_api_key):
    zip_code, country = zip_info
    result = requests.get(f"{OPENWEATHER_HOST}/geo/1.0/zip?zip={zip_code},{country}&appid={weather_api_key}").json()
    lat = result['lat']
    lon = result['lon']
    loc = lat, lon
    return loc

@cache
# Cache results so we avoid exceeding the API rate limit
# No need to invalidate cache since location per given IP address is generally fixed
def get_location_by_ip(ip_api_key, ip):
    from iplocate import IPLocateClient
    client = IPLocateClient(api_key=ip_api_key)
    result = client.lookup(ip)
    loc = result.latitude, result.longitude
    try:
        log.debug(f"Getting weather for {result.city}, {result.subdivision}, {result.country_code}, geo coordinates: {loc}")
    except:
        pass
    return loc

####  Monitor functions ####

class TimeMonitor:

    @staticmethod
    def get(**kwargs):
        """
        Return the current time as a tuple (HHMM, is_pm). is_pm is False if 24-hour format is used.
        Represent in local time or specified timezone, and in 24-hour or 12-hour format, based on configuration.
        """
        timezone = kwargs.get('timezone', None)
        format_24_hour = 'fmt_24_hour' in kwargs and kwargs['fmt_24_hour']
        now = datetime.now(ZoneInfo(timezone)) if timezone else datetime.now().astimezone()
        if format_24_hour:
            return (now.strftime("%H%M"), False)
        else:
            return (now.strftime("%I%M"), now.strftime("%p") == 'PM')

        
class WeatherMonitor:

    @staticmethod
    @cache
    # Cache results so we avoid exceeding the API rate limit
    def get(fs_dict):
        ip = requests.get(IPIFY_HOST).text
        ip_api_key = os.environ.get("IP_LOCATE_API_KEY", None)
        weather_api_key = os.environ.get("OPENWEATHER_API_KEY", None)

        # https://ipapi.co/ip/ is a simpler location API (no api key needed for free version),
        # but it applies rate limits arbitrarily and is not be reliable for production use.
        args_dict = dict(fs_dict)
        zip_info = args_dict.get('zip_info', None)
        lat_lon = args_dict.get('lat_lon', None)
        units = args_dict.get('units', 'metric')
        forecast = args_dict.get('forecast', False)
        forecast_day = args_dict.get('forecast_day', 1)
        forecast_hour = args_dict.get('forecast_hour', 12)
        mist_like = ['Mist', 'Fog', 'Dust', 'Haze', 'Smoke', 'Squall', 'Ash', 'Sand', 'Tornado']

        try:
            if lat_lon:
                loc = lat_lon
            elif zip_info:
                loc = get_location_by_zip(zip_info, weather_api_key)
            elif ip_api_key:
                loc = get_location_by_ip(ip_api_key, ip)
            else:
                raise Exception("No location method configured")
            
            temp_symbol = 'degC'if units == 'metric' else 'degF' if units == 'imperial' else 'degK'

            if forecast:
                forecast = requests.get(f"{OPENWEATHER_HOST}/data/2.5/forecast?lat={loc[0]}&lon={loc[1]}&appid={weather_api_key}&units={units}").json()
                target_date = (datetime.now(ZoneInfo('GMT')).date() + timedelta(days=forecast_day))
                for fc in forecast['list']:
                    dt = datetime.strptime(fc['dt_txt'], '%Y-%m-%d %H:%M:%S')
                    if dt.date() == target_date and dt.hour >= forecast_hour:
                        temp, feels_like, wind_speed, wind_speed_symbol, wind_dir, temp_symbol, condition = fc['main']['temp'], fc['main']['feels_like'], fc['wind']['speed'], 'mi' if units == 'imperial' else 'km', fc['wind']['deg'], temp_symbol, fc['weather'][0]['main']
                        if condition in mist_like: condition= 'mist-like'
                        # Convert m/sec to km/hr (* 3,600 / 1,000)
                        if units != 'imperial': wind_speed *= 3.6
                        forecast = Weather('Forecast', temp, feels_like, wind_speed, wind_speed_symbol, wind_dir, temp_symbol, condition)
                        # print(f"Forecast weather for time {fc['dt_txt']}")
                        return forecast
                forecast = forecast['list'][-1]
                # print(f"Forecast weather for latest time availabe: {forecast['dt_txt']}")
                temp, feels_like, wind_speed, wind_speed_symbol, wind_dir, temp_symbol, condition = forecast['main']['temp'], forecast['main']['feels_like'], forecast['wind']['speed'], 'mi' if units == 'imperial' else 'km', forecast['wind']['deg'], temp_symbol, forecast['weather'][0]['main']
                # Convert m/sec to km/hr (* 3,600 / 1,000)
                if units != 'imperial': wind_speed *= 3.6
                if condition in mist_like: condition= 'mist-like'
                forecast = Weather('Forecast', temp, feels_like, wind_speed, wind_speed_symbol, wind_dir, temp_symbol, condition)
                return forecast
            else:
                current = requests.get(f"{OPENWEATHER_HOST}/data/2.5/weather?lat={loc[0]}&lon={loc[1]}&appid={weather_api_key}&units={units}").json()

                temp, feels_like, wind_speed, wind_speed_symbol, wind_dir, temp_symbol, condition = current['main']['temp'], current['main']['feels_like'], current['wind']['speed'], 'mi' if units == 'imperial' else 'km', current['wind']['deg'], temp_symbol, current['weather'][0]['main']
                # Convert m/sec to km/hr (* 3,600 / 1,000)
                if units != 'imperial': wind_speed *= 3.6
                if condition in mist_like: condition= 'mist-like'
                weather = Weather('Current', temp, feels_like, wind_speed, wind_speed_symbol, wind_dir, temp_symbol, condition)
                return weather
        except Exception as e:
            log.error(f"Error getting weather: {e}")
            return None
        
    
time_monitor = TimeMonitor()
weather_monitor = WeatherMonitor()

#### Implement high-level drawing functions to be called by app functions below ####

draw_app = getattr(drawing, 'draw_app')

VALID_MEASURES = ['temp_condition', 'wind_chill', 'wind']

def get_next_measure(measures, duration):
    measures = list(filter(lambda m: m in VALID_MEASURES, measures))
    base_time = time.monotonic()
    measure_idx = 0
    while True:
        if time.monotonic() - base_time > duration:
            measure_idx = (measure_idx + 1) % len(measures)
            base_time = time.monotonic()
        yield measures[measure_idx]
        
def get_weather_values(weather: Weather, measure):
    if measure == Measures.TEMP_COND.value:
        return  list(str(round(weather.temp))) + [weather.temp_symbol] + [weather.condition.lower()]
    elif measure == Measures.WIND_CHILL.value:
        return ['wc', ' '] + list(str(round(weather.wind_chill))) + [weather.temp_symbol]
    elif measure == Measures.WIND.value:
        # Convert wind direction in degrees to compass direction
        dirs = ['n', 'ne', 'e', 'se', 's', 'sw', 'w', 'nw']
        ix = round(weather.wind_dir / (360. / len(dirs)))
        wind_dir = dirs[ix % len(dirs)]
        return ['wd', ' '] + list(str(round(weather.wind_speed))) + [weather.wind_speed_symbol] + [f"wind-{wind_dir}"]
    else:
        return "?", "?"
    
def draw_fc_period_indicator(grid, foreground_value, day, hour):
    """Draw vertical bars at the bottom left and right mafrix edges, to indicate
        the Forecast Day (left edge) and Forecast Hours (right edge) settings"""
    day = max(1, min(day, 5))
    hours = [0, 3, 6, 9, 12, 15, 18, 21]
    hours_idx = 8
    for idx, _hour in enumerate(hours):
        if hour >= _hour: hours_idx = idx
    # We count from the bottom pixel with a 1-based index
    hours_idx += 1
    day_y_vals = range(33 -day +1, 34)
    hour_y_vals = range(33 -hours_idx + 1, 34)
    grid[0, day_y_vals[0]: day_y_vals[-1]+1] = foreground_value
    grid[8, hour_y_vals[0]: hour_y_vals[-1]+1] = foreground_value
    # Draw a hash mark next to the fourht pixel from bottom if needed, for ease of reading
    grid[7, 30] = grid[8, 30]
    
@cache
def get_generator(**kwargs):
    return get_next_measure( kwargs.get('measures', [Measures.TEMP_COND.value]), kwargs.get('measures-duration', 10))
        
def draw_weather(arg, grid, foreground_value, idx, **kwargs):
    # Make kwargs hashable for caching
    fs_dict = frozenset(kwargs.items())
    weather = weather_monitor.get(fs_dict)
    if weather:
        gen = get_generator(**kwargs)
        weather_values = get_weather_values(weather, next(gen))
        draw_app(arg, grid, weather_values, foreground_value, idx)
        # log.debug(f"Weather: {weather_values}")
        if kwargs.get("forecast", None):
            draw_fc_period_indicator(grid, foreground_value, kwargs.get("forecast_day", 1), kwargs.get("forecast_hour", 12))
    else:
        draw_app(arg, grid, ["?", "?"], foreground_value, idx)
        log.debug(f"Weather: No data available")

    
def draw_time(arg, grid, foreground_value, idx, **kwargs):
    hhmm, is_pm = time_monitor.get(**kwargs)
    hhmm = list(hhmm)
    time_values = hhmm[:2] + ["horiz_colon"] + hhmm[2:]
    draw_app(arg, grid, time_values, foreground_value, idx)
    if is_pm:
        grid.T[32:34, 7:9] = icons['pm_indicator'] * foreground_value


def repeat_function(interval, func, *args, **kwargs):
    def wrapper():
        func(*args, **kwargs)
        Timer(interval, wrapper).start()

    Timer(interval, wrapper).start()


# Get fresh weather data every 30 secs. Two calls per minute will be well within the openweather API
# free tierlimit of 60 calls/minute and 1,000,000 calls/month
repeat_function(30, weather_monitor.get.cache_clear)

draw_chars = getattr(drawing, 'draw_chars_list')

#### Implement low-level drawing functions ####
# These functions will be dynamically imported by drawing.py and called by their corresponding app function
direct_draw_funcs = {
    "time": {
        "fn": draw_chars,
        "border": lambda *x: None  # no border
    },
    "weather": {
        "fn": draw_chars,
        "border": lambda *x: None  # no border
    }
}

# Implement app functions that call your direct_draw functions
# These functions will be dynamically imported by led_system_monitor.py. They call the direct_draw_funcs
# defined above, providing additional capabilities that can be targeted to panel quadrants

app_funcs = [
    {
        "name": "time",
        "fn": draw_time
    },
    {
        "name": "weather",
        "fn": draw_weather
    }
]

# Provide id patterns that identify your apps
# These items will be dynamically imported by drawing.py

id_patterns = {
    "time": np.concatenate((np.zeros((2,9)), letters_5_x_6["T"], np.zeros((2,9)), letters_5_x_6["I"], np.zeros((2,9)),letters_5_x_6["M"], np.zeros((2,9)), letters_5_x_6["E"], np.zeros((2,9)))).T,
    "weather_current": np.concatenate((np.zeros((2,9)), letters_5_x_6["W"], np.zeros((2,9)), letters_5_x_6["T"], np.zeros((2,9)),letters_5_x_6["R"], np.zeros((2,9)), letters_5_x_6["C"], np.zeros((2,9)))).T,
    "weather_forecast": np.concatenate((np.zeros((2,9)), letters_5_x_6["W"], np.zeros((2,9)), letters_5_x_6["T"], np.zeros((2,9)),letters_5_x_6["R"], np.zeros((2,9)), letters_5_x_6["F"], np.zeros((2,9)))).T
}
