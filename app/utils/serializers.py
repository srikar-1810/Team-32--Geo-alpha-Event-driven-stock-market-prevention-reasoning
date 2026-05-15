from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any, Dict, List, Optional
from uuid import UUID


class GeoMarketJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles dates, datetimes, UUIDs, and models."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, date):
            return obj.isoformat()
        if isinstance(obj, UUID):
            return str(obj)
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        if hasattr(obj, "dict"):
            return obj.dict()
        if hasattr(obj, "__str__"):
            return str(obj)
        return super().default(obj)


def serialize(obj: Any, **kwargs) -> str:
    return json.dumps(obj, cls=GeoMarketJSONEncoder, **kwargs)


def deserialize(data: str) -> Any:
    return json.loads(data)


def serialize_model(model: Any) -> Dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    if hasattr(model, "dict"):
        return model.dict()
    if hasattr(model, "__dict__"):
        return {
            k: v for k, v in model.__dict__.items()
            if not k.startswith("_")
        }
    return dict(model)


def serialize_list(models: List[Any]) -> List[Dict[str, Any]]:
    return [serialize_model(m) for m in models]
