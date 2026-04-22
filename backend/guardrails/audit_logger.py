"""
Guardrail 5 — Audit Logger
Structured security audit trail for all guardrail events.
Logs: who, what, when, outcome, risk level — for compliance & demo visibility.

All guardrail events are written to:
  - Python logger (stdout / log file)
  - In-memory audit log (queryable via /api/guardrails/audit endpoint)
"""

import json
import logging
import time
from collections import deque
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from threading import Lock
from typing import Optional

logger = logging.getLogger(__name__)

# Keep last 500 audit events in memory
MAX_AUDIT_EVENTS = 500


@dataclass
class AuditEvent:
    event_id: int
    timestamp: str
    guardrail: str          # e.g. "file_validator", "rate_limiter", "query_safety"
    action: str             # e.g. "BLOCKED", "ALLOWED", "WARNING"
    risk_level: str         # SAFE / LOW / MEDIUM / HIGH / CRITICAL
    user_id: Optional[int]
    ip_address: Optional[str]
    details: dict = field(default_factory=dict)


class AuditLog:
    """Thread-safe in-memory audit log with recent event buffer."""

    def __init__(self, max_events: int = MAX_AUDIT_EVENTS):
        self._events: deque[AuditEvent] = deque(maxlen=max_events)
        self._counter = 0
        self._lock = Lock()

    def log(
        self,
        guardrail: str,
        action: str,
        risk_level: str,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        **details,
    ) -> AuditEvent:
        with self._lock:
            self._counter += 1
            event = AuditEvent(
                event_id=self._counter,
                timestamp=datetime.now(timezone.utc).isoformat(),
                guardrail=guardrail,
                action=action,
                risk_level=risk_level,
                user_id=user_id,
                ip_address=ip_address,
                details=details,
            )
            self._events.append(event)

        # Emit to Python logger
        log_fn = logger.warning if risk_level in ("HIGH", "CRITICAL") else logger.info
        log_fn(
            f"[AUDIT] guardrail={guardrail} action={action} risk={risk_level} "
            f"user={user_id} ip={ip_address} details={json.dumps(details)}"
        )
        return event

    def get_recent(self, limit: int = 50) -> list[dict]:
        with self._lock:
            events = list(self._events)
        return [asdict(e) for e in reversed(events[-limit:])]

    def get_blocked_events(self, limit: int = 50) -> list[dict]:
        with self._lock:
            blocked = [e for e in self._events if e.action == "BLOCKED"]
        return [asdict(e) for e in reversed(blocked[-limit:])]

    def get_stats(self) -> dict:
        with self._lock:
            events = list(self._events)

        total = len(events)
        blocked = sum(1 for e in events if e.action == "BLOCKED")
        by_guardrail: dict[str, int] = {}
        by_risk: dict[str, int] = {}

        for e in events:
            by_guardrail[e.guardrail] = by_guardrail.get(e.guardrail, 0) + 1
            by_risk[e.risk_level] = by_risk.get(e.risk_level, 0) + 1

        return {
            "total_events": total,
            "blocked_events": blocked,
            "allowed_events": total - blocked,
            "block_rate_percent": round(blocked / total * 100, 1) if total else 0,
            "by_guardrail": by_guardrail,
            "by_risk_level": by_risk,
        }


# ── Singleton ─────────────────────────────────────────────────────────────────
audit_log = AuditLog()


# ── Convenience helpers ───────────────────────────────────────────────────────

def log_file_blocked(filename: str, error_code: str, user_id: Optional[int] = None,
                     ip: Optional[str] = None):
    audit_log.log(
        guardrail="file_validator",
        action="BLOCKED",
        risk_level="HIGH",
        user_id=user_id,
        ip_address=ip,
        filename=filename,
        error_code=error_code,
    )


def log_file_allowed(filename: str, size_bytes: int, user_id: Optional[int] = None):
    audit_log.log(
        guardrail="file_validator",
        action="ALLOWED",
        risk_level="SAFE",
        user_id=user_id,
        filename=filename,
        size_bytes=size_bytes,
    )


def log_rate_limit_blocked(endpoint: str, user_id: Optional[int] = None,
                            ip: Optional[str] = None, retry_after: int = 60):
    audit_log.log(
        guardrail="rate_limiter",
        action="BLOCKED",
        risk_level="MEDIUM",
        user_id=user_id,
        ip_address=ip,
        endpoint=endpoint,
        retry_after_seconds=retry_after,
    )


def log_query_blocked(query: str, blocked_code: str, risk_level: str,
                      user_id: Optional[int] = None):
    audit_log.log(
        guardrail="query_safety",
        action="BLOCKED",
        risk_level=risk_level,
        user_id=user_id,
        query_preview=query[:80],
        blocked_code=blocked_code,
    )


def log_query_allowed(query: str, user_id: Optional[int] = None):
    audit_log.log(
        guardrail="query_safety",
        action="ALLOWED",
        risk_level="SAFE",
        user_id=user_id,
        query_preview=query[:80],
    )


def log_llm_output_warning(guardrail_name: str, warnings: list[str],
                            user_id: Optional[int] = None):
    audit_log.log(
        guardrail=guardrail_name,
        action="WARNING",
        risk_level="LOW",
        user_id=user_id,
        warnings=warnings,
    )


def log_llm_output_blocked(guardrail_name: str, errors: list[str],
                            user_id: Optional[int] = None):
    audit_log.log(
        guardrail=guardrail_name,
        action="BLOCKED",
        risk_level="HIGH",
        user_id=user_id,
        errors=errors,
    )
