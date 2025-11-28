#!/usr/bin/env python3

# Copyright (C) 2023 Alessandro "Sgorblex" Clerici Lorenzini
#
# This file is part of birthdays_I_care_about.
#
# birthdays_I_care_about is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# birthdays_I_care_about is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with birthdays_I_care_about. If not, see <https://www.gnu.org/licenses/>.

import os.path
from datetime import datetime
from sys import argv

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

calendar_name = "🎂"
people_i_care_about_file = "people_I_care_about.txt"
people_i_care_about_labels = ["7e5ebbbd08286e82"]

credentials_file = "credentials.json"
token_file = "token.json"

gapi_scopes = ["https://www.googleapis.com/auth/calendar", "https://www.googleapis.com/auth/contacts.readonly"]


def people_i_care_about_from_file():
    people_i_care_about = set()
    if not os.path.exists(people_i_care_about_file):
        print(f"Cannot find people file ({people_i_care_about_file})")
        exit(1)
    with open(people_i_care_about_file) as file:
        people_i_care_about = set(line.strip() for line in file)
    return people_i_care_about


def people_i_care_about_from_contacts(creds):
    labels_i_care_about = {f"contactGroups/{string}" for string in people_i_care_about_labels}
    people_i_care_about = set()
    try:
        people_client = build("people", "v1", credentials=creds)

        results = (
            people_client.people()
            .connections()
            .list(
                resourceName="people/me",
                pageSize=1000,
                personFields="names,memberships",
                sortOrder="FIRST_NAME_ASCENDING",
            )
            .execute()
        )
        connections = results.get("connections", [])

        for person in connections:
            names = person.get("names", [])
            if names:
                name = names[0].get("displayName")
                membershipz = [member.get("contactGroupMembership", []).get("contactGroupResourceName") for member in person.get("memberships", [])]
                if not labels_i_care_about.isdisjoint(membershipz):
                    people_i_care_about.add(name)
        return people_i_care_about
    except HttpError as error:
        print(f"An error occurred: {error}")
        return set()


def main():
    creds = None
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, gapi_scopes)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(credentials_file):
                print(f"You need to put your Google API credentials in {credentials_file}")
                exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, gapi_scopes)
            creds = flow.run_local_server(port=0)
        with open(token_file, "w") as token:
            token.write(creds.to_json())

    people_i_care_about = people_i_care_about_from_contacts(creds)

    try:
        calendar_client = build("calendar", "v3", credentials=creds)

        print("CALENDAR LIST")
        calendars = calendar_client.calendarList().list().execute()["items"]

        print("GET CUSTOM CALENDAR")
        cal = None
        try:
            cal = next(d for d in calendars if d["summary"] == calendar_name)["id"]
        except StopIteration:
            print("Custom calendar not found. Now creating it")
            calendar = {"summary": calendar_name}
            cal = calendar_client.calendars().insert(body=calendar).execute()["id"]
            print(f"Calendar {calendar_name} created")

        print("INSPECT CUSTOM CALENDAR")
        cal_events = calendar_client.events().list(calendarId=cal).execute()["items"]
        events_to_remove = []
        people_to_remove = set()
        existing_birthdays = set()
        if "--clean" in argv:
            events_to_remove = cal_events
            people_to_remove = "everyone"
        else:
            for event in cal_events:
                person = event["summary"].removeprefix("🎂 ")
                if person not in people_i_care_about:
                    events_to_remove.append(event)
                    people_to_remove.add(person)
                else:
                    existing_birthdays.add(person)
        print(f"Removing birthdays of {people_to_remove}")
        for event in events_to_remove:
            calendar_client.events().delete(calendarId=cal, eventId=event["id"]).execute()

        print("GET BIRTHDAY EVENTS")
        birthcal_id = "addressbook#contacts@group.v.calendar.google.com"

        current_year = datetime.now().year
        time_lower = datetime(current_year, 1, 1).isoformat() + "Z"
        time_upper = datetime(current_year + 1, 1, 1).isoformat() + "Z"

        birthdays = calendar_client.events().list(calendarId=birthcal_id, timeMin=time_lower, timeMax=time_upper, orderBy="startTime", singleEvents=True).execute()["items"]
        print("ADD BIRTHDAYS TO NEW CAL")
        people_i_may_add = people_i_care_about - existing_birthdays
        for birthday in birthdays:
            person = birthday["gadget"]["preferences"]["goo.contactsFullName"]
            if person in people_i_may_add:
                print(f"Adding {person}'s birthday")
                event = {
                    "summary": "🎂 " + person,
                    "start": birthday["start"],
                    "end": birthday["end"],
                    "recurrence": ["RRULE:FREQ=YEARLY;WKST=TU"],
                }
                calendar_client.events().insert(calendarId=cal, body=event).execute()

    except HttpError as error:
        print(f"An error occurred: {error}")


if __name__ == "__main__":
    main()
