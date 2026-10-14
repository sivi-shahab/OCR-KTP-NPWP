"""Parsing of the model's answer into a document's data model."""

import json
import re
from typing import TypeVar

from pydantic import BaseModel

DataModel = TypeVar("DataModel", bound=BaseModel)

_JSON_OBJECT = re.compile(r"\{.*\}", re.DOTALL)
_TRAILING_COMMA = re.compile(r",\s*}")


class OutputParseError(ValueError):
    """The model's answer did not contain a usable JSON object."""


def parse_fields(raw: str, data_model: type[DataModel]) -> DataModel:
    """Extract the outermost JSON object from `raw` and map it onto `data_model`.

    Missing keys become "", unknown keys are dropped, non-string values are stringified.
    """
    fields = _load_json_object(raw)
    return data_model(**{name: str(fields.get(name, "")) for name in data_model.model_fields})


def _load_json_object(raw: str) -> dict:
    match = _JSON_OBJECT.search(raw)
    if not match:
        raise OutputParseError(f"No JSON object found in output: {raw}")

    text = match.group()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Common LLM hiccup: trailing comma before the closing brace
    text = _TRAILING_COMMA.sub("}", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise OutputParseError(f"Failed to parse JSON: {exc}\nRaw: {text}") from exc
