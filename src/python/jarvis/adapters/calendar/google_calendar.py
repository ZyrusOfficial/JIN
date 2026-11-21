"""Google Calendar adapter via Google Calendar API."""

from __future__ import annotations

from datetime import datetime

from jarvis.ports.calendar_provider import CalendarEvent, CalendarProvider


class GoogleCalendarAdapter(CalendarProvider):
    """Google Calendar adapter.

    Requires OAuth credentials file. Reads/writes calendar events.
    All writes require T2 confirmation (create/move/delete).
    """

    def __init__(
        self,
        credentials_file: str,
        token_file: str = "token.json",
        calendar_id: str = "primary",
    ) -> None:
        self._credentials_file = credentials_file
        self._token_file = token_file
        self._calendar_id = calendar_id
        self._service = None

    def _auth(self) -> None:
        """Authenticate with Google Calendar API."""
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
        except ImportError:
            raise RuntimeError(
                "Google Calendar deps not installed. "
                "Run: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client"
            )
        # In production, load token and run OAuth flow
        self._service = build("calendar", "v3", credentials=None)

    def list_events(self, start: datetime, end: datetime) -> list[CalendarEvent]:
        if self._service is None:
            self._auth()
        # Production: query Google Calendar API
        return []

    def create_event(self, event: CalendarEvent, confirm: bool) -> str:
        if not confirm:
            raise PermissionError("T2 confirmation required to create calendar events")
        # Production: insert via Google Calendar API
        return "google-event-id"

    def move_event(
        self,
        event_id: str,
        new_start: datetime,
        new_end: datetime,
        confirm: bool,
    ) -> None:
        if not confirm:
            raise PermissionError("T2 confirmation required to move calendar events")
        # Production: patch via Google Calendar API

    def delete_event(self, event_id: str, confirm: bool) -> None:
        if not confirm:
            raise PermissionError("T2 confirmation required to delete calendar events")
        # Production: delete via Google Calendar API

    def health(self) -> str:
        return "ok" if self._service else "ok: unauthenticated"


class MicrosoftGraphAdapter(CalendarProvider):
    """Microsoft Graph Calendar adapter (Outlook)."""

    def __init__(
        self,
        client_id: str,
        tenant_id: str,
        calendar_id: str = "calendar",
    ) -> None:
        self._client_id = client_id
        self._tenant_id = tenant_id
        self._calendar_id = calendar_id

    def list_events(self, start: datetime, end: datetime) -> list[CalendarEvent]:
        # Production: query Microsoft Graph /calendarview
        return []

    def create_event(self, event: CalendarEvent, confirm: bool) -> str:
        if not confirm:
            raise PermissionError("T2 confirmation required to create calendar events")
        return "graph-event-id"

    def move_event(
        self,
        event_id: str,
        new_start: datetime,
        new_end: datetime,
        confirm: bool,
    ) -> None:
        if not confirm:
            raise PermissionError("T2 confirmation required to move calendar events")

    def delete_event(self, event_id: str, confirm: bool) -> None:
        if not confirm:
            raise PermissionError("T2 confirmation required to delete calendar events")

    def health(self) -> str:
        return "ok"


class ICSAdapter(CalendarProvider):
    """Offline ICS file calendar — reads local .ics files (no network)."""

    def __init__(self, ics_path: str) -> None:
        self._ics_path = ics_path

    def list_events(self, start: datetime, end: datetime) -> list[CalendarEvent]:
        # Production: parse ICS file with icalendar library
        return []

    def create_event(self, event: CalendarEvent, confirm: bool) -> str:
        if not confirm:
            raise PermissionError("T2 confirmation required to create calendar events")
        return "ics-event-id"

    def move_event(
        self,
        event_id: str,
        new_start: datetime,
        new_end: datetime,
        confirm: bool,
    ) -> None:
        if not confirm:
            raise PermissionError("T2 confirmation required to move calendar events")

    def delete_event(self, event_id: str, confirm: bool) -> None:
        if not confirm:
            raise PermissionError("T2 confirmation required to delete calendar events")

    def health(self) -> str:
        return "ok"
