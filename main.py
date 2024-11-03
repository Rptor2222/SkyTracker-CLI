from geopy.geocoders import Nominatim
import pandas as pd
from retry_requests import retry
import openmeteo_requests, requests_cache, datetime, pytz, pyfiglet, survey
from timezonefinder import TimezoneFinder
from termcolor import colored

cache_session = requests_cache.CachedSession('.cache', expire_after = 3600)
retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
openmeteo = openmeteo_requests.Client(session = retry_session)

def get_coordinates(city_name):
    geolocator = Nominatim(user_agent="my_weather_app")
    
    # Get location
    location = geolocator.geocode(city_name)
    
    if location:
        return location.latitude, location.longitude
    else:
        return None, None

print(pyfiglet.figlet_format("SkyTracker CLI"))
print(colored("Welcome to SkyTracker CLI!", "light_blue"))

city = survey.routines.input("Enter the name of the city: ")
lat, lon = get_coordinates(city)

def get_local_time(lat, lon):
    tf = TimezoneFinder()
    timezone_str = tf.timezone_at(lat=lat, lng=lon)
    
    if timezone_str is None:
        return "Timezone not found for these coordinates."

    local_tz = pytz.timezone(timezone_str)
    local_time = datetime.datetime.now(local_tz)
    
    return local_time.strftime("%H:%M")

if lat is not None and lon is not None:
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m",
        "current": "temperature_2m",
        "temperature_unit": "celsius",
        "timezone": "auto"
    }
    responses = openmeteo.weather_api(url, params=params)
    responses = openmeteo.weather_api(url, params=params)

    response = responses[0]
    utc_offset_seconds = response.UtcOffsetSeconds()

    offset_minutes_total = utc_offset_seconds // 60
    offset_hours = offset_minutes_total // 60
    offset_minutes = offset_minutes_total % 60

    if offset_hours == 0:
        offset = f"{offset_minutes} minutes"
    else:
        offset = f"{offset_hours} hours and {offset_minutes} minutes"
    print(f"City: {colored(city, "green")}")

    print(f"Coordinates are {colored(response.Latitude(), "green")}{colored("°N", "green")}, {colored(response.Longitude(), "green")}{colored("°E", "green")}")

    print(f"Timezone is {colored(str(response.Timezone()).replace("b'", "").replace("'", ""), "green")} {colored(str(response.TimezoneAbbreviation()).replace("b", "").replace("'", ""), "green")}")

    print(f"Timezone difference to GMT+0 is {colored(offset, "green")}")

    current = response.Current()
    current_temperature_2m = current.Variables(0).Value()

    print(f"Current time: {colored(get_local_time(lat, lon), "green")}")
    print(f"Current Temperature is {colored(round(current_temperature_2m), "green")}{colored("°C", "green")}")

    wh_hourly = survey.routines.select("Would you like the hourly data? ", options=["Yes", "No"])
    if wh_hourly == 0:
        hourly = response.Hourly()
        hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()

        hourly_data = {
            "Date & Time": pd.date_range(
                start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
                end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
                freq=pd.Timedelta(seconds=hourly.Interval()),
                inclusive="left"    
            ),
            "Temperature (°C)": hourly_temperature_2m
        }

        hourly_dataframe = pd.DataFrame(data=hourly_data)
        hourly_dataframe["Temperature (°C)"] = hourly_dataframe["Temperature (°C)"].round().astype(int)

        local_tz = pytz.timezone(TimezoneFinder().timezone_at(lat=lat, lng=lon))
        hourly_dataframe['Date & Time'] = hourly_dataframe['Date & Time'].dt.tz_convert(local_tz)
        hourly_dataframe['Date & Time'] = hourly_dataframe['Date & Time'].dt.strftime('%Y-%m-%d %H:%M')

        print(hourly_dataframe.to_string(index=False))

    else:
        print(colored("Thank you for using SkyTracker CLI!", "light_blue"))
        exit()

else:
    print(colored(f"Could not find the coordinates for {city}.", "red"))

print(colored("Thank you for using SkyTracker CLI!", "light_blue"))