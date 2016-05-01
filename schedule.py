#!/usr/bin/python

# Weather forecast for Raspberry Pi w/Adafruit Mini Thermal Printer.
# Retrieves data from Yahoo! weather, prints current conditions and
# forecasts for next two days.  See timetemp.py for a different
# weather example using nice bitmaps.
# Written by Adafruit Industries.  MIT license.
#
# Required software includes Adafruit_Thermal and PySerial libraries.
# Other libraries used are part of stock Python install.
#
# Resources:
# http://www.adafruit.com/products/597 Mini Thermal Receipt Printer
# http://www.adafruit.com/products/600 Printer starter pack

from __future__ import print_function
import urllib2, time, json
from Adafruit_Thermal import *
from xml.dom.minidom import parseString
import dateutil.parser

# For Google API Client
import httplib2
import os

from apiclient import discovery
import oauth2client
from oauth2client import client
from oauth2client import tools

import datetime

try:
  import argparse
  flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
  flags = None

# Get weather from Weather Underground
def get_weather():
  class TempWeatherClass():
    pass
  weather = TempWeatherClass()
  weather_response =  urllib2.urlopen('http://api.wunderground.com/api/71f5b4292ef80a0f/geolookup/forecast/conditions/q/US/TX/Irving.json')
  weather_json_string = weather_response.read()
  parsed_weather_json = json.loads(weather_json_string)
  weather.city = parsed_weather_json['location']['city']
  weather.state = parsed_weather_json['location']['state']
  weather.temp_now = parsed_weather_json['current_observation']['temp_f']
  weather.feels_like_now = parsed_weather_json['current_observation']['feelslike_f']
  weather.weather_now = parsed_weather_json['current_observation']['weather']
  weather.precip_today = parsed_weather_json['current_observation']['precip_today_in']
  weather.icon_url_now = parsed_weather_json['current_observation']['icon_url']
  weather.weather_today = parsed_weather_json['forecast']['txt_forecast']['forecastday'][0]['fcttext']
  weather.weather_tonight = parsed_weather_json['forecast']['txt_forecast']['forecastday'][1]['fcttext']
  weather.weather_tomorrow = parsed_weather_json['forecast']['txt_forecast']['forecastday'][2]['fcttext']
  weather.weather_tomorrow_night = parsed_weather_json['forecast']['txt_forecast']['forecastday'][0]['fcttext']
  return weather

# Get Calendar Events
SCOPES = 'https://www.googleapis.com/auth/calendar.readonly'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Schedule Printer'

def get_credentials():
  """Gets valid user credentials from storage.

  If nothing has been stored, or if the stored credentials are invalid,
  the OAuth2 flow is completed to obtain the new credentials.

  Returns:
    Credentials, the obtained credential.
  """
  home_dir = os.path.expanduser('~')
  credential_dir = os.path.join(home_dir, '.credentials')
  if not os.path.exists(credential_dir):
    os.makedirs(credential_dir)
  credential_path = os.path.join(credential_dir, 'schedule-printer.json')

  store = oauth2client.file.Storage(credential_path)
  credentials = store.get()
  if not credentials or credentials.invalid:
    flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
    flow.user_agent = APPLICATION_NAME
    if flags:
      credentials = tools.run_flow(flow, store, flags)
    else: # Needed only for compatability with Python 2.6
      credentials = tools.run(flow, store)
      print('Storing credentials to ' + credential_path)
  return credentials

def get_events():
  credentials = get_credentials()
  http = credentials.authorize(httplib2.Http())
  service = discovery.build('calendar', 'v3', http=http)

  today = datetime.datetime.now().date().isoformat() + 'T05:00:00.00000Z' # 'Z' indicates UTC time
  tomorrow = (datetime.datetime.now().date() + datetime.timedelta(days=1)).isoformat() + 'T05:00:00.00000Z'

  # Get School Events
  school_events_response = service.events().list(
    calendarId='fbick@udallas.edu', timeMin=today, timeMax=tomorrow, singleEvents=True,
    orderBy='startTime').execute()
  school_events = school_events_response.get('items', [])

  # Get Personal Events
  personal_events_response = service.events().list(
    calendarId='fxb9500@gmail.com', timeMin=today, timeMax=tomorrow, singleEvents=True,
    orderBy='startTime').execute()
  personal_events = personal_events_response.get('items', [])

  # Get OrgSync Events
  orgsync_events_response = service.events().list(
    calendarId='d6j1a4rhfdlq0vedpcmlr7kc65ibf4u5@import.calendar.google.com', timeMin=today, timeMax=tomorrow, singleEvents=True,
    orderBy='startTime').execute()
  orgsync_events = orgsync_events_response.get('items', [])

  # Get Classes
  classes_response = service.events().list(
    calendarId='udallas.edu_0cmob30ann4uve0nupg51n3o5c@group.calendar.google.com', timeMin=today, timeMax=tomorrow, singleEvents=True,
    orderBy='startTime').execute()
  classes_events = classes_response.get('items', [])

  # Get SG Events
  sg_events_response = service.events().list(
    calendarId='udallas.edu_fgh4cdmckd6aerue7ifu8piicg@group.calendar.google.com', timeMin=today, timeMax=tomorrow, singleEvents=True,
    orderBy='startTime').execute()
  sg_events = sg_events_response.get('items', [])

  # Get Facebook Events
  fb_events_response = service.events().list(
    calendarId='qc539ste9s3cabf9uhq8lv3l2pdpdobs@import.calendar.google.com', timeMin=today, timeMax=tomorrow, singleEvents=True,
    orderBy='startTime').execute()
  fb_events = fb_events_response.get('items', [])

  all_events = school_events + personal_events + orgsync_events + classes_events + sg_events + fb_events
  todays_events = [e for e in all_events if "dateTime" in e["start"]]
  return sorted(todays_events, key = lambda e: e['start']['dateTime'])

def main():
  printer = Adafruit_Thermal("/dev/ttyAMA0", 19200, timeout=5)
  deg     = chr(0xf8) # Degree symbol on thermal printer
  events = get_events()

  # Print heading
  printer.setSize('M')
  printer.justify('C')
  printer.println( datetime.datetime.today().date().strftime("%A, %B %-d, %Y") )
  printer.justify('L')
  printer.setSize('S')

  # Print schedule
  printer.boldOn()
  printer.underlineOn()
  printer.justify('C')
  printer.println("Today's Schedule")
  printer.justify('L')
  printer.underlineOff()
  printer.boldOff()

  printer.feed(1)

  if not events:
    printer.println('No scheduled events today.')
    printer.feed(1)
  for event in events:
    start = dateutil.parser.parse(event['start'].get('dateTime', event['start'].get('date'))).strftime("%-I:%M%p")
    end = dateutil.parser.parse(event['end'].get('dateTime', event['end'].get('date'))).strftime("%-I:%M%p")
    location = event.get('location', '')
    printer.println(event['summary'])
    if start == end:
      if location:
        printer.println(start + ", " + location)
      else:
        printer.println(start)
    else:
      if location == "":
        printer.println(start + " - " + end)
      else:
        printer.println(start + " - " + end + ", " + location)
    printer.feed(1)

  printer.feed(1)

  # Print weather
  weather = get_weather()

  printer.boldOn()
  printer.underlineOn()
  printer.justify('C')
  printer.println("Today's Weather")
  printer.justify('L')
  printer.underlineOff()
  printer.boldOff()

  printer.feed(1)

  printer.println("Temperature: " + str(weather.temp_now) + ". Feels like " + str(weather.feels_like_now))
  printer.feed(1)

  printer.println("Today: " + weather.weather_today)
  printer.feed(1)

  printer.println("Tonight: " + weather.weather_tonight)
  printer.feed(1)

  downcase_first = lambda s: s[:1].lower() + s[1:] if s else ''
  printer.println("Tomorrow: " + weather.weather_tomorrow + " Tomorrow night, " + downcase_first(weather.weather_tomorrow_night))
  printer.feed(1)

  printer.feed(2)

if __name__ == '__main__':
  main()
