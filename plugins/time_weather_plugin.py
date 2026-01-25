from statistics import mean
import psutil
import requests
import os
from zoneinfo import ZoneInfo
from datetime import datetime, timedelta, date
from iplocate import IPLocateClient
import numpy as np
from functools import cache
from threading import Timer
from patterns import icons, letters
import math
import logging

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
@cache
# Cache results so we avoid exceeding the API rate limit
def get_location_by_zip(zip_info, weather_api_key):
    zip_code, country = zip_info
    result = requests.get(f"http://api.openweathermap.org/geo/1.0/zip?zip={zip_code},{country}&appid={weather_api_key}").json()
    lat = result['lat']
    lon = result['lon']
    loc = lat, lon
    return loc


def get_location_by_ip(ip_api_key, ip):
    client = IPLocateClient(api_key=ip_api_key)
    result = client.lookup(ip)
    loc = result.latitude, result.longitude
    log.debug(f"Location: {loc}")
    return loc

####  Monitor functions ####


class TimeMonitor:

    @staticmethod
    def get(*args):
        """
        Return the current time as a tuple (HHMM, is_pm). is_pm is False if 24-hour format is used.
        Represent in local time or GMT, and in 24-hour or 12-hour format, based on configuration.
        """
        # args is a tuple of dicts, each containing a configuration option
        from datetime import datetime
        args_dict = {}
        for arg in args:
            if isinstance(arg, dict):
                args_dict.update(arg)
        timezone = args_dict.get('timezone', None)
        format_24_hour = 'fmt_24_hour' in args_dict and args_dict['fmt_24_hour']
        now = datetime.now(ZoneInfo(timezone)) if timezone else datetime.now().astimezone()
        if format_24_hour:
            return (now.strftime("%H%M"), False)
        else:
            return (now.strftime("%I%M"), now.strftime("%p") == 'PM')

        
class WeatherMonitor:

    @staticmethod
    @cache
    # Cache results so we avoid exceeding the API rate limit
    def get(*args):
        ip = requests.get('https://api.ipify.org').text
        ip_api_key = os.environ.get("IP_LOCATE_API_KEY", None)
        weather_api_key = '1a39e21cebbba98fad2014d4fe4af96f'

        # https://ipapi.co/ip/ is a simpler location API (no api key needed for free version),
        # but it applies rate limits arbitrarily and is not be reliable for production use.
        args_dict = dict((k, v) for fs in args for k, v in fs)

        # zip_info = ("20191", "US")
        # lat_lon = (38.9318, -77.3527)
        zip_info = args_dict.get('zip_info', None)
        lat_lon = args_dict.get('lat_lon', None)
        units = args_dict.get('units', 'metric')
        forecast = args_dict.get('forecast', False)
        forecast_day = args_dict.get('forecast_day', 1)
        forecast_hour = args_dict.get('forecast_hour', 12)

        try:
            if zip_info:
                loc = get_location_by_zip(zip_info, weather_api_key)
            elif lat_lon:
                loc = lat_lon
            elif ip_api_key:
                loc = get_location_by_ip(ip_api_key, ip)
            else:
                raise Exception("No location method configured")
            
            temp_symbol = 'degC'if units == 'metric' else 'degF' if units == 'imperial' else 'degK'

            if forecast:
                forecast = requests.get(f"http://api.openweathermap.org/data/2.5/forecast?lat={loc[0]}&lon={loc[1]}&appid={weather_api_key}&units={units}").json()
                fc = forecast['list'][0]
                temp = fc['main']['temp']
                cond = fc['weather'][0]['main']
                target_date = (datetime.now(ZoneInfo('GMT')).date() + timedelta(days=forecast_day))
                for fc in forecast['list']:
                    dt = datetime.strptime(fc['dt_txt'], '%Y-%m-%d %H:%M:%S')
                    if dt.date() == target_date and dt.hour >= forecast_hour:
                        temp = fc['main']['temp']
                        cond = fc['weather'][0]['main']
                        log.debug(f"Forecast weather: {fc['dt_txt']} {temp} degC, {cond}")
                        _forecast = [temp, temp_symbol, cond]
                        return _forecast
                temp = forecast['list'][-1]['main']['temp']
                cond = forecast['list'][-1]['weather'][0]['main']
                _forecast = [temp, temp_symbol, cond]
                log.debug(f"Forecast weather: {fc['dt_txt']} {temp } {temp_symbol}, {cond}")
                return _forecast
            else:
                current = requests.get(f"http://api.openweathermap.org/data/2.5/weather?lat={loc[0]}&lon={loc[1]}&appid={weather_api_key}&units={units}").json()

                _current = [current['main']['temp'], temp_symbol, current['weather'][0]['main']]
                log.debug(f"Current weather: {_current}")
                return _current
        except Exception as e:
            log.error(f"Error getting weather: {e}")
            return None
        
    
time_monitor = TimeMonitor()
weather_monitor = WeatherMonitor()

#### Implement high-level drawing functions to be called by app functions below ####

import drawing
draw_app = getattr(drawing, 'draw_app')

        
def draw_weather(arg, grid, foreground_value, idx, *args):
    # Make args dict hashable for caching
    frozenset_tuple = tuple(frozenset(d.items()) for d in args)
    current_weather = weather_monitor.get(*frozenset_tuple)
    if current_weather and current_weather[0] and current_weather[1]:
        temp_val = current_weather[0]
        temp = str(round(temp_val))
        weather_values = list(temp) + [current_weather[1]] + [current_weather[2].lower()]
        draw_app(arg, grid, weather_values, foreground_value, idx)
        # TODO if temp value was greater than 99, indicate with animation, such as pulsing, or draw a +
    else:
        draw_app(arg, grid, ["?", "?"], foreground_value, idx)

    
def draw_time(arg, grid, foreground_value, idx, *args):
    hhmm, is_pm = time_monitor.get(*args)
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


# Get fresh weather data every 30 secs
repeat_function(30, weather_monitor.get.cache_clear)

draw_chars = getattr(drawing, 'draw_chars')

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
    "time": np.concatenate((np.zeros((2,9)), letters["T"], np.zeros((2,9)), letters["I"], np.zeros((2,9)),letters["M"], np.zeros((2,9)), letters["E"], np.zeros((2,9)))).T,
    "weather_current": np.concatenate((np.zeros((2,9)), letters["W"], np.zeros((2,9)), letters["T"], np.zeros((2,9)),letters["R"], np.zeros((2,9)), letters["C"], np.zeros((2,9)))).T,
    "weather_forecast": np.concatenate((np.zeros((2,9)), letters["W"], np.zeros((2,9)), letters["T"], np.zeros((2,9)),letters["R"], np.zeros((2,9)), letters["F"], np.zeros((2,9)))).T
}
