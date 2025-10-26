from __future__ import annotations

from typing import Dict, List, Union

JSONPrimitive = Union[str, int, float, bool, None]
JSONValue = Union["JSONArray", "JSONObject", JSONPrimitive]
JSONArray = List[JSONValue]
JSONObject = Dict[str, JSONValue]

# Backwards compatible alias for dictionary responses returned by Plexity APIs.
JSONDict = JSONObject

__all__ = [
    "JSONPrimitive",
    "JSONValue",
    "JSONArray",
    "JSONObject",
    "JSONDict",
]
