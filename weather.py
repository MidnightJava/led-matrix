import os, sys
import requests
from zoneinfo import ZoneInfo
from iplocate import IPLocateClient
from datetime import datetime, timedelta

OPENWEATHER_HOST = 'https://api.openweathermap.org'
IPIFY_HOST = 'https://api.ipify.org'

TEST_CONFIG = {
    'zip_info': ('10001', 'US'),  # New York, NY
    'lat_lon': (40.7128, -74.0060),  # New York, NY
    'units': 'metric',
    'forecast_day': 1,  # 1=tomorrow, 2=day after tomorrow, etc.
    'forecast_hour': 12,  # Hour of the day for forecast (0-23)
}

def get_weather(forecast):
    zip_info = TEST_CONFIG['zip_info']
    lat_lon =TEST_CONFIG['lat_lon']
    units =TEST_CONFIG['units']
    forecast_day = TEST_CONFIG['forecast_day']
    forecast_hour =TEST_CONFIG['forecast_hour']
    mist_like = ['Mist', 'Fog', 'Dust', 'Haze', 'Smoke', 'Squall', 'Ash', 'Sand', 'Tornado']

    ip = requests.get(IPIFY_HOST).text
    ip_api_key = os.environ.get("IP_LOCATE_API_KEY", None)
    weather_api_key = os.environ.get("OPENWEATHER_API_KEY", None)

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
            fc = forecast['list'][0]
            temp = fc['main']['temp']
            cond = fc['weather'][0]['main']
            target_date = (datetime.now(ZoneInfo('GMT')).date() + timedelta(days=forecast_day))
            for fc in forecast['list']:
                dt = datetime.strptime(fc['dt_txt'], '%Y-%m-%d %H:%M:%S')
                if dt.date() == target_date and dt.hour >= forecast_hour:
                    temp = fc['main']['temp']
                    cond = fc['weather'][0]['main']
                    if cond in mist_like: cond = 'mist-like'
                    _forecast = [temp, temp_symbol, cond]
                    print(f"Forecast weather for time {fc['dt_txt']}")
                    return _forecast
            temp = forecast['list'][-1]['main']['temp']
            cond = forecast['list'][-1]['weather'][0]['main']
            if cond in mist_like: cond = 'mist-like'
            _forecast = [temp, temp_symbol, cond]
            print(f"Forecast weather for time {fc['dt_txt']}")
            return _forecast
        else:
            current = requests.get(f"{OPENWEATHER_HOST}/data/2.5/weather?lat={loc[0]}&lon={loc[1]}&appid={weather_api_key}&units={units}").json()

            _current = [current['main']['temp'], temp_symbol, current['weather'][0]['main']]
            if _current[2] in mist_like: _current[2] = 'mist-like'
            return _current
    except Exception as e:
        print(f"Error getting weather: {e}")
        return None

    

def get_time():
    """
    Return the current time as a tuple (HHMM, is_pm). is_pm is False if 24-hour format is used.
    Represent in local time or GMT, and in 24-hour or 12-hour format, based on configuration.
    """
    from datetime import datetime
    # TODOD get from config file
    format_24_hour =  False
    use_gmt = False
    now = datetime.now(ZoneInfo("GMT")) if use_gmt else datetime.now().astimezone()
    if format_24_hour   :
        return (now.strftime("%H%M"), False)
    else:
        return (now.strftime("%I%M"),now.strftime("%p") == 'PM' )

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
    if result.country: print(f"Country: {result.country}")
    if result.city: print(f"City: {result.city}")
    if result.privacy.is_vpn: print(f"VPN: {result.privacy.is_vpn}")
    if result.privacy.is_proxy: print(f"Proxy: {result.privacy.is_proxy}")
    loc = result.latitude, result.longitude
    return loc

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    current_time = get_time()
    print(f"Time: {current_time[0]} {'PM' if current_time[1] else 'AM/24-hour'}")
    fc = get_weather(forecast=True)
    current = get_weather(forecast=False)
    print(f"Weather: Current: {current}, Forecast: {fc}")