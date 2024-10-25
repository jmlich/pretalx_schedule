#!/usr/bin/python

import config
import sys
import locale
import json
import os
import requests
from typing import List, Dict, Any
from datetime import datetime, timedelta

locale.setlocale(locale.LC_COLLATE, 'cs_CZ.UTF-8')
locale.setlocale(locale.LC_TIME, 'cs_CZ.UTF-8')

class ScheduleApp:

    TIMESLOT = 5

    def __init__(self):
        self.AUTHORIZATION = config.AUTHORIZATION
        self.JSON_FILE = config.JSON_FILE
        self.API_URL = config.API_URL
        self.ROOM_ORDER = config.ROOM_ORDER

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
        start_times = {datetime.fromisoformat(s['slot']['start']) for s in day_sessions}
        end_times = {datetime.fromisoformat(s['slot']['end']) for s in day_sessions}
        times = sorted(start_times | end_times)

        # Determine min and max time boundaries for the day's schedule

        min_time = min(times)
        max_time = max(times)

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

#            html += f'<td rowspan="1">{time_str}</td>'
            if current_time.minute == 0:
                rowspan = 60 // self.TIMESLOT
                next_hour = (current_time + timedelta(minutes=60)).strftime("%H:%M")
                html += f'<td rowspan="{rowspan}">{time_str} &mdash; {next_hour} </td>'

#            if currnet_time 
#            if current_time in times:
#                next_time = next((t for t in times if t > current_time), max_time)
#                duration = (next_time - current_time).total_seconds() // 60 
#                rowspan = duration // self.TIMESLOT
#                next_time_str = next_time.strftime("%H:%M")
##                html += f'<td rowspan="{rowspan}">{time_str} &mdash; {next_time_str} </td>'
#                html += f'<td rowspan="{rowspan}">{time_str} </td>'

            for room in self.ROOM_ORDER:
                # Check if the room is occupied

                if occupied[room] is None or occupied[room] <= current_time:
                    # Find a session that starts at this time in the current room
                    session = next((s for s in day_sessions if datetime.fromisoformat(s['slot']['start']) == current_time and s['slot']['room']['en'] == room), None)

                    if session:
                        # Calculate the end time of the session
                        session_end = datetime.fromisoformat(session['slot']['end'])
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
                                         and datetime.fromisoformat(s['slot']['start']) > current_time), None)
                        if next_session:
                            next_start_time = datetime.fromisoformat(next_session['slot']['start'])
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