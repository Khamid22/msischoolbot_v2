import json
import re
import threading
import time

from backend.core.redis_client import get_redis_client

_UPLOAD_ID_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{5,127}$")
_EVENT_HISTORY_LIMIT = 200
_UPLOAD_TTL_SECONDS = 30 * 60

_UPLOAD_STATES_LOCK = threading.Lock()
_UPLOAD_STATES = {}


def _redis_keys(upload_id):
    prefix = f"msi:upload-progress:{upload_id}"
    return f"{prefix}:events", f"{prefix}:seq"


def normalize_upload_id(raw_upload_id):
    normalized = str(raw_upload_id or "").strip()
    if not normalized:
        return ""
    if not _UPLOAD_ID_PATTERN.fullmatch(normalized):
        return ""
    return normalized


def _clamp_percent(value):
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = 0.0
    if parsed < 0.0:
        return 0.0
    if parsed > 100.0:
        return 100.0
    return parsed


def _normalize_eta_seconds(value):
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if parsed < 0:
        return None
    return parsed


def _prune_expired_states_locked(now):
    expired_upload_ids = []
    for upload_id, state in _UPLOAD_STATES.items():
        updated_at = float(state.get("updated_at", 0.0))
        completed_at = state.get("completed_at")
        if completed_at is not None:
            if now - float(completed_at) > _UPLOAD_TTL_SECONDS:
                expired_upload_ids.append(upload_id)
                continue
        elif now - updated_at > (_UPLOAD_TTL_SECONDS * 2):
            expired_upload_ids.append(upload_id)

    for upload_id in expired_upload_ids:
        _UPLOAD_STATES.pop(upload_id, None)


def _ensure_state(upload_id):
    now = time.time()
    with _UPLOAD_STATES_LOCK:
        _prune_expired_states_locked(now)
        state = _UPLOAD_STATES.get(upload_id)
        if state is None:
            state = {
                "condition": threading.Condition(),
                "events": [],
                "next_seq": 1,
                "updated_at": now,
                "completed_at": None,
            }
            _UPLOAD_STATES[upload_id] = state
        else:
            state["updated_at"] = now
        return state


def publish_upload_event(
    upload_id,
    *,
    percent=0.0,
    stage="processing",
    message="",
    eta_seconds=None,
    done=False,
    error=False,
):
    normalized_upload_id = normalize_upload_id(upload_id)
    if not normalized_upload_id:
        return

    now = time.time()
    redis_client = get_redis_client()
    if redis_client is not None:
        events_key, seq_key = _redis_keys(normalized_upload_id)
        try:
            seq = int(redis_client.incr(seq_key))
            event = {
                "seq": seq,
                "upload_id": normalized_upload_id,
                "percent": _clamp_percent(percent),
                "stage": str(stage or "").strip(),
                "message": str(message or "").strip(),
                "eta_seconds": _normalize_eta_seconds(eta_seconds),
                "done": bool(done),
                "error": bool(error),
                "timestamp": now,
            }
            pipeline = redis_client.pipeline(transaction=False)
            pipeline.rpush(events_key, json.dumps(event, ensure_ascii=False))
            pipeline.ltrim(events_key, -_EVENT_HISTORY_LIMIT, -1)
            pipeline.expire(events_key, _UPLOAD_TTL_SECONDS)
            pipeline.expire(seq_key, _UPLOAD_TTL_SECONDS)
            pipeline.execute()
            return
        except Exception:
            pass

    state = _ensure_state(normalized_upload_id)
    with state["condition"]:
        seq = int(state["next_seq"])
        state["next_seq"] = seq + 1

        event = {
            "seq": seq,
            "upload_id": normalized_upload_id,
            "percent": _clamp_percent(percent),
            "stage": str(stage or "").strip(),
            "message": str(message or "").strip(),
            "eta_seconds": _normalize_eta_seconds(eta_seconds),
            "done": bool(done),
            "error": bool(error),
            "timestamp": now,
        }
        state["events"].append(event)
        if len(state["events"]) > _EVENT_HISTORY_LIMIT:
            state["events"] = state["events"][-_EVENT_HISTORY_LIMIT:]
        state["updated_at"] = now
        if bool(done) or bool(error):
            state["completed_at"] = now
        state["condition"].notify_all()


def begin_upload(upload_id):
    publish_upload_event(
        upload_id,
        percent=1.0,
        stage="start",
        message="Preparing upload...",
    )


def complete_upload(upload_id, message="Upload completed."):
    publish_upload_event(
        upload_id,
        percent=100.0,
        stage="complete",
        message=message,
        done=True,
        error=False,
    )


def fail_upload(upload_id, message="Upload failed.", percent=0.0, stage="error"):
    publish_upload_event(
        upload_id,
        percent=percent,
        stage=stage,
        message=message,
        done=True,
        error=True,
    )


def wait_for_upload_event(upload_id, *, after_seq=0, timeout_seconds=20.0):
    normalized_upload_id = normalize_upload_id(upload_id)
    if not normalized_upload_id:
        return None

    safe_after_seq = int(after_seq or 0)
    safe_timeout = max(float(timeout_seconds or 0.0), 0.0)
    deadline = time.time() + safe_timeout

    redis_client = get_redis_client()
    if redis_client is not None:
        while True:
            events = get_upload_events(normalized_upload_id, after_seq=safe_after_seq, limit=1)
            if events:
                return events[0]
            now = time.time()
            if now >= deadline:
                return None
            time.sleep(min(0.2, deadline - now))

    with _UPLOAD_STATES_LOCK:
        state = _UPLOAD_STATES.get(normalized_upload_id)
    if state is None:
        return None

    def _next_event_locked():
        for event in state["events"]:
            if int(event.get("seq", 0)) > safe_after_seq:
                return dict(event)
        return None

    # NOTE:
    # Poll with short sleeps rather than blocking on threading.Condition.wait():
    # the upload producer and this SSE consumer live in different worker threads,
    # and short-sleep polling keeps the response streaming without holding the
    # condition lock across the wait.
    while True:
        with state["condition"]:
            found = _next_event_locked()
        if found is not None:
            return found

        now = time.time()
        if now >= deadline:
            return None

        time.sleep(min(0.2, deadline - now))


def get_upload_events(upload_id, *, after_seq=0, limit=100):
    normalized_upload_id = normalize_upload_id(upload_id)
    if not normalized_upload_id:
        return []

    try:
        safe_after_seq = int(after_seq or 0)
    except (TypeError, ValueError):
        safe_after_seq = 0
    try:
        safe_limit = max(int(limit or 0), 1)
    except (TypeError, ValueError):
        safe_limit = 100
    redis_client = get_redis_client()
    if redis_client is not None:
        events_key, _seq_key = _redis_keys(normalized_upload_id)
        try:
            decoded = []
            for raw_event in redis_client.lrange(events_key, 0, -1):
                event = json.loads(raw_event)
                if int(event.get("seq", 0)) > safe_after_seq:
                    decoded.append(event)
                if len(decoded) >= safe_limit:
                    break
            return decoded
        except Exception:
            pass

    with _UPLOAD_STATES_LOCK:
        state = _UPLOAD_STATES.get(normalized_upload_id)
    if state is None:
        return []
    with state["condition"]:
        events = [
            dict(event)
            for event in state["events"]
            if int(event.get("seq", 0)) > safe_after_seq
        ]
    return events[:safe_limit]


__all__ = [
    "normalize_upload_id",
    "publish_upload_event",
    "begin_upload",
    "complete_upload",
    "fail_upload",
    "wait_for_upload_event",
    "get_upload_events",
]
