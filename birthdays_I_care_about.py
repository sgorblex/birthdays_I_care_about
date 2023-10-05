#!/usr/bin/env python3

from datetime import datetime
import os.path
from sys import argv

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

calendar_name = "🎂"
people_I_care_about_file = "people_I_care_about.txt"

credentials_file = "credentials.json"
token_file = "token.json"

gapi_perms = ["https://www.googleapis.com/auth/calendar"]

people_I_care_about = set()
if not os.path.exists(people_I_care_about_file):
    print(f"Cannot find whitelist file ({people_I_care_about_file})")
    exit(1)
with open(people_I_care_about_file, 'r') as file:
    people_I_care_about = set(line.strip() for line in file)


def main():
    creds = None
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, gapi_perms)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(credentials_file):
                print(f"You need to put your Google API credentials in {credentials_file}")
                exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, gapi_perms)
            creds = flow.run_local_server(port=0)
        with open(token_file, 'w') as token:
            token.write(creds.to_json())

    try:
        service = build("calendar", "v3", credentials=creds)

        print("CALENDAR LIST")
        calendars = service.calendarList().list().execute()["items"]

        print("GET CUSTOM CALENDAR")
        cal = None
        try:
            cal = next((d for d in calendars if d["summary"] == calendar_name))["id"]
        except StopIteration:
            print("Custom calendar not found. Now creating it")
            calendar = {"summary": calendar_name}
            cal = service.calendars().insert(body=calendar).execute()["id"]
            print(f"Calendar {calendar_name} created")

        print("INSPECT CUSTOM CALENDAR")
        cal_events = service.events().list(calendarId=cal).execute()["items"]
        events_to_remove = []
        people_to_remove = set()
        existing_birthdays = set()
        if "--clean" in argv:
            events_to_remove = cal_events
            people_to_remove = "everyone"
        else:
            for event in cal_events:
                person = event["summary"].removeprefix("🎂 ")
                if person not in people_I_care_about:
                    events_to_remove.append(event)
                    people_to_remove.add(person)
                else:
                    existing_birthdays.add(person)
        print(f"Removing birthdays of {people_to_remove}")
        for event in events_to_remove:
            service.events().delete(calendarId=cal, eventId=event["id"]).execute()

        print("GET BIRTHDAY EVENTS")
        birthcal_id = "addressbook#contacts@group.v.calendar.google.com"

        current_year = datetime.now().year
        time_lower = datetime(current_year, 1, 1).isoformat()+'Z'
        time_upper = datetime(current_year+1, 1, 1).isoformat()+'Z'

        birthdays = service.events().list(calendarId=birthcal_id, timeMin=time_lower, timeMax=time_upper, orderBy="startTime", singleEvents=True).execute()["items"]
        print("ADD BIRTHDAYS TO NEW CAL")
        people_I_may_add = people_I_care_about-existing_birthdays
        for birthday in birthdays:
            person = birthday["gadget"]["preferences"]["goo.contactsFullName"]
            if person in people_I_may_add:
                print(f"Adding {person}'s birthday")
                event = {
                    "summary": "🎂 "+person,
                    "start": birthday["start"],
                    "end": birthday["end"],
                    "recurrence": ["RRULE:FREQ=YEARLY;WKST=TU"],
                }
                service.events().insert(calendarId=cal, body=event).execute()

    except HttpError as error:
        print("An error occurred: %s" % error)


if __name__ == "__main__":
    main()
