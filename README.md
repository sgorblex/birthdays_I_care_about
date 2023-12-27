# Birthdays I Care About
Google Contacts automatically sets up a Google Calendar with the birthdays of your contacts. But what if I don't care about someone's birthday but I still want to save it in the contacts?

This is where Birthdays I Care About comes in. It creates a custom Calendar with only the contacts you Care About, as listed in the file `people_I_care_about.txt`. You can also customize the way the birthdays are displayed (the default is already way cuter than the original calendar). This way you can have your Google Calendar free of bloat birthdays of boring people and full of fantastic birthdays of awesome people!


## How to use it
Clone the repo
```sh
git clone https://github.com/sgorblex/birthdays_I_care_about
cd birthdays_I_care_about
```

Install the Python dependencies (and Python if you don't have it)
```sh
pip install -r requirements.txt
```

Set up a [Google Cloud](https://console.cloud.google.com/) project and install the Google Calendar API on it. You may also follow guides like the "Set up your environment" section from [this one](https://developers.google.com/calendar/api/quickstart/python?hl=en). It's full of them on the Internet.

Once you have `credentials.json` put it in the current directory.

The game is done! On the first run it should let you log in with a Google account.

Remember to hide from your calendars the ugly default one and show off your shiny new one :)
