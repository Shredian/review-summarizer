from __future__ import annotations

from typing import Any

import orjson


def dumps_bytes(obj: Any) -> bytes:
    return orjson.dumps(obj, default=_orjson_default)


def loads_dict(data: bytes | str | memoryview | None) -> dict[str, Any]:
    if data is None:
        raise ValueError("empty payload")
    if isinstance(data, memoryview):
        data = data.tobytes()
    if isinstance(data, str):
        data = data.encode("utf-8")
    out = orjson.loads(data)
    if not isinstance(out, dict):
        raise TypeError("expected JSON object")
    return out


def decode_stream_payload_fields(fields: dict[Any, Any]) -> dict[str, Any]:
    """Декодирование поля payload из Redis Streams (str или bytes ключи/значения)."""
    raw = fields.get(b"payload") or fields.get("payload")
    if raw is None:
        raise KeyError("payload")
    if isinstance(raw, str):
        return loads_dict(raw.encode("utf-8"))
    return loads_dict(raw)


def _orjson_default(obj: object) -> str:
    return str(obj)
