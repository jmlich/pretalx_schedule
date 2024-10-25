#!/usr/bin/python

import locale
import json
import os
import requests
from typing import List, Dict, Any
from datetime import datetime, timedelta

locale.setlocale(locale.LC_COLLATE, 'cs_CZ.UTF-8')
locale.setlocale(locale.LC_TIME, 'cs_CZ.UTF-8')

class ScheduleApp:

    CONF_SLUG = "openalt-2024"
    AUTHORIZATION = "Token 7711dade56ebd69ccc83fb9af052fc753759b74f"
    JSON_FILE = f"{CONF_SLUG}_sessions.json"
    API_URL = f"https://talks.openalt.cz/api/events/{CONF_SLUG}/talks/?limit=1000"

    ROOM_ORDER = ['D105', 'D0206', 'D0207', 'A112', 'A113' ]  # Define your rooms in the desired order here
    TIMESLOT = 5

    def __init__(self):
        self.sessions = self.load_or_download_json()


    def load_or_download_json(self) -> list:
        """Loads JSON data from a file if it exists; otherwise, downloads it."""
        if os.path.exists(self.JSON_FILE):
            with open(self.JSON_FILE, 'r', encoding='utf-8') as file:
                return json.load(file).get('results', [])
        else:
            headers = {"Authorization": self.AUTHORIZATION}
            response = requests.get(self.API_URL, headers=headers)
            response.raise_for_status()  # Ensure the request was successful

            data = response.json()
            with open(self.JSON_FILE, 'w', encoding='utf-8') as file:
                json.dump(data, file, ensure_ascii=False, indent=4)
            return data.get('results', [])

    def export_schedule(self):
        """Placeholder function for exporting the schedule."""

        days = {session['slot']['start'][:10] for session in self.sessions if session['slot']}  # Get unique days

        html = '<!DOCTYPE html>\n<html>\n<head>\n'
        html += '<link rel="stylesheet" type="text/css" href="styles.css">\n'
        html += '<title>Conference Schedule</title>\n    <link rel="stylesheet" href="./style.css" type="text/css"></head>\n<body>\n'


        for day in sorted(days):
            day_name = datetime.strptime(day, "%Y-%m-%d").strftime("%A, %-d. %B %Y")
            html += f'<h1>{day_name}</h1>\n'
            html += self.export_schedule_day(day)

        html += "</body></html>"
        print(html)

    def export_schedule_day(self, day: str):
        """Generates an HTML table for a single day's schedule."""
        # Filter and sort sessions by start time for the given day
        day_sessions = sorted(
            [s for s in self.sessions if s['slot'] and s['slot']['start'].startswith(day)],
            key=lambda s: s['slot']['start']
        )


        # Get all start and end times
        start_times = {s['slot']['start'][11:16] for s in day_sessions}
        end_times = {s['slot']['end'][11:16] for s in day_sessions}
        times = sorted(start_times | end_times)

        # Determine min and max time boundaries for the day's schedule
        min_time = datetime.strptime(min(times), "%H:%M")
        max_time = datetime.strptime(max(times), "%H:%M")

        rooms = {s['slot']['room']['en'] for s in day_sessions if 'room' in s['slot']}

        occupied = {room: None for room in self.ROOM_ORDER}

        missing_rooms = rooms - set(self.ROOM_ORDER)
        if missing_rooms:
            print(f"Error: The following rooms are not in ROOM_ORDER: {missing_rooms}")
            raise ValueError("Room verification failed; please update ROOM_ORDER with the missing rooms.")


        # Generate HTML table header
        html = '<table border="1">\n'
        html += '<tr><th></th>' + ''.join(f'<th>{room}</th>' for room in self.ROOM_ORDER) + '</tr>\n'


        current_time = min_time
        while current_time < max_time:
            time_str = current_time.strftime("%H:%M")
            html += f'<tr>'
            html += f'<td rowspan="1">{time_str}</td>'

            for room in self.ROOM_ORDER:
                # Check if the room is occupied

                if occupied[room] is None or occupied[room] <= current_time:
                    # Find a session that starts at this time in the current room
                    session = next((s for s in day_sessions if s['slot']['start'][11:16] == time_str and s['slot']['room']['en'] == room), None)

                    if session:
                        # Calculate the end time of the session
                        session_end = datetime.strptime(session['slot']['end'][11:16], "%H:%M")
                        duration = session.get('duration', 0)
                        rowspan = max(1, duration // self.TIMESLOT)

                        # Mark this room as occupied until the end of the session
                        occupied[room] = session_end

                        # Print the cell for the session with rowspan
                        html += self.print_one_cell(session, rowspan)
                    else:
                        # If no session, calculate rowspan for empty slots
                        next_session = next((s for s in day_sessions 
                                         if s['slot']['room']['en'] == room 
                                         and datetime.strptime(s['slot']['start'][11:16], "%H:%M") > current_time), None)
                        if next_session:
                            next_start_time = datetime.strptime(next_session['slot']['start'][11:16], "%H:%M")
                            empty_duration = (next_start_time - current_time).total_seconds() // 60
                            empty_rowspan = empty_duration // self.TIMESLOT
                            occupied[room] = current_time + timedelta(minutes=empty_duration)
                            html += f'<td rowspan="{empty_rowspan}"></td>'
                        else:
                            # If no further sessions, extend occupancy until max_time
                            empty_duration = (max_time - current_time).total_seconds() // 60
                            empty_rowspan = empty_duration // self.TIMESLOT
                            occupied[room] = max_time
                            html += f'<td rowspan="{empty_rowspan}"></td>'
            html += f'</tr>\n'
            current_time += timedelta(minutes=self.TIMESLOT)

        html += '</table>'
        return html

    def print_one_cell(self, session, rowspan = 1):
        """Generates the HTML for a cell based on session data."""
        if session:
            start = session['slot']['start'][11:16]
            end = session['slot']['end'][11:16]
            session['track_id']
            speakers = ", ".join(sp.get('name', '') for sp in session.get('speakers', []))

            display_text = f'<td rowspan="{rowspan}" class="track{session['track_id']}">{speakers + ': ' if speakers else ''}<span class="title">{session['title']}</span><br><span class="date">{start}-{end}</span></td>\n'
            return display_text
        else:
            # Return an empty cell for unoccupied time slots
            return ''



app = ScheduleApp()

app.export_schedule()