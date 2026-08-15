from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class LiveSession:
    session_id: str
    line_name: str
    created_at: str
    activation_unit: int | None = None
    records: list[dict[str, Any]] = field(default_factory=list)
    finalized: bool = False


class LiveSessionRegistry:
    def __init__(self) -> None:
        self._sessions: dict[str, LiveSession] = {}

    def create(self, line_name: str, activation_unit: int | None = None) -> LiveSession:
        sid = "LIVE-" + uuid.uuid4().hex[:10].upper()
        session = LiveSession(
            session_id=sid,
            line_name=line_name,
            activation_unit=activation_unit,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self._sessions[sid] = session
        return session

    def get(self, session_id: str) -> LiveSession:
        try:
            return self._sessions[session_id]
        except KeyError as exc:
            raise KeyError(f"Unknown live session: {session_id}") from exc

    def append(self, session_id: str, records: list[dict[str, Any]]) -> LiveSession:
        session = self.get(session_id)
        if session.finalized:
            raise ValueError("Live session has already been finalized.")
        session.records.extend(records)
        return session

    def finalize(self, session_id: str) -> LiveSession:
        session = self.get(session_id)
        if session.finalized:
            raise ValueError("Live session has already been finalized.")
        session.finalized = True
        return session
