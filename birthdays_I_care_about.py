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
from typing import Any

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


def people_i_care_about_from_file() -> set[str]:
    people_i_care_about: set[str] = set()
    if not os.path.exists(people_i_care_about_file):
        print(f"Cannot find people file ({people_i_care_about_file})")
        exit(1)
    with open(people_i_care_about_file) as file:
        people_i_care_about = set(line.strip() for line in file)
    return people_i_care_about


def people_i_care_about_from_contacts(creds: Credentials) -> set[str]:
    labels_i_care_about: set[str] = {f"contactGroups/{string}" for string in people_i_care_about_labels}
    people_i_care_about: set[str] = set()
    try:
        people_client: Any = build("people", "v1", credentials=creds)

        results: Any = (
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
        connections: list[dict[str, Any]] = results.get("connections", [])

        for person in connections:
            names = person.get("names", [])
            if names:
                name = names[0].get("displayName")
                if name:
                    memberships = person.get("memberships", [])
                    membershipz: list[str | None] = [
                        member.get("contactGroupMembership", {}).get("contactGroupResourceName")
                        for member in memberships
                    ]
                    if not labels_i_care_about.isdisjoint(membershipz):
                        people_i_care_about.add(name)
        return people_i_care_about
    except HttpError as error:
        print(f"An error occurred: {error}")
        return set()


def main() -> None:
    creds: Credentials | None = None
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
        if creds is None:
            print("Failed to obtain credentials")
            exit(1)
        with open(token_file, "w") as token:
            token.write(creds.to_json())

    if creds is None:
        print("Failed to obtain credentials")
        exit(1)

    people_i_care_about = people_i_care_about_from_contacts(creds)

    try:
        calendar_client: Any = build("calendar", "v3", credentials=creds)

        print("CALENDAR LIST")
        calendar_list_response: Any = calendar_client.calendarList().list().execute()
        calendars: list[Any] = calendar_list_response.get("items", [])

        print("GET CUSTOM CALENDAR")
        cal: str | None = None
        try:
            cal = next(d for d in calendars if d.get("summary") == calendar_name).get("id")
        except StopIteration:
            print("Custom calendar not found. Now creating it")
            calendar: Any = {"summary": calendar_name}
            calendar_response: Any = calendar_client.calendars().insert(body=calendar).execute()
            cal = calendar_response.get("id")
            if cal is None:
                print("Failed to get calendar ID from response")
                return
            print(f"Calendar {calendar_name} created")

        if cal is None:
            print("Failed to get or create calendar")
            return

        print("INSPECT CUSTOM CALENDAR")
        events_response: Any = calendar_client.events().list(calendarId=cal).execute()
        cal_events: list[Any] = events_response.get("items", [])
        events_to_remove: list[Any] = []
        people_to_remove: set[str] | str = set()
        existing_birthdays: set[str] = set()
        if "--clean" in argv:
            events_to_remove = cal_events
            people_to_remove = "everyone"
        else:
            for cal_event in cal_events:
                summary = cal_event.get("summary", "")
                person_name: str = summary.removeprefix("🎂 ")
                if person_name not in people_i_care_about:
                    events_to_remove.append(cal_event)
                    if isinstance(people_to_remove, set):
                        people_to_remove.add(person_name)
                else:
                    existing_birthdays.add(person_name)
        print(f"Removing birthdays of {people_to_remove}")
        for event_to_delete in events_to_remove:
            event_id = event_to_delete.get("id")
            if event_id:
                calendar_client.events().delete(calendarId=cal, eventId=event_id).execute()

        print("GET BIRTHDAY EVENTS")
        birthcal_id = "addressbook#contacts@group.v.calendar.google.com"

        current_year = datetime.now().year
        time_lower = datetime(current_year, 1, 1).isoformat() + "Z"
        time_upper = datetime(current_year + 1, 1, 1).isoformat() + "Z"

        birthdays_response: Any = calendar_client.events().list(calendarId=birthcal_id, timeMin=time_lower, timeMax=time_upper, orderBy="startTime", singleEvents=True).execute()
        birthdays: list[Any] = birthdays_response.get("items", [])
        print("ADD BIRTHDAYS TO NEW CAL")
        people_i_may_add = people_i_care_about - existing_birthdays
        for birthday in birthdays:
            gadget = birthday.get("gadget", {})
            preferences = gadget.get("preferences", {})
            birthday_person = preferences.get("goo.contactsFullName")
            if birthday_person and birthday_person in people_i_may_add:
                print(f"Adding {birthday_person}'s birthday")
                new_event: Any = {
                    "summary": "🎂 " + birthday_person,
                    "start": birthday.get("start", {}),
                    "end": birthday.get("end", {}),
                    "recurrence": ["RRULE:FREQ=YEARLY;WKST=TU"],
                }
                calendar_client.events().insert(calendarId=cal, body=new_event).execute()

    except HttpError as error:
        print(f"An error occurred: {error}")


if __name__ == "__main__":
    main()
