"""Parsing of the model's answer into a document's data model."""

import json
import re
from typing import TypeVar, get_args, get_origin

from pydantic import BaseModel

DataModel = TypeVar("DataModel", bound=BaseModel)

_JSON_OBJECT = re.compile(r"\{.*\}", re.DOTALL)
_TRAILING_COMMA = re.compile(r",\s*}")


class OutputParseError(ValueError):
    """The model's answer did not contain a usable JSON object."""


def parse_fields(raw: str, data_model: type[DataModel]) -> DataModel:
    """Extract the outermost JSON object from `raw` and map it onto `data_model`.

    Missing keys become "", unknown keys are dropped, non-string values are stringified.
    List-of-model fields (e.g. KK family members) are parsed item by item the same way.
    """
    return _build(_load_json_object(raw), data_model)


def _build(fields: dict, data_model: type[DataModel]) -> DataModel:
    values = {}
    for name, field in data_model.model_fields.items():
        value = fields.get(name)
        item_model = _list_item_model(field.annotation)
        if item_model is None:
            values[name] = "" if value is None else str(value)
        elif isinstance(value, list):
            values[name] = [_build(item, item_model) for item in value if isinstance(item, dict)]
        else:
            values[name] = []
    return data_model(**values)


def _list_item_model(annotation) -> type[BaseModel] | None:
    """The item model of a `list[SomeModel]` annotation, otherwise None."""
    if get_origin(annotation) is list:
        (item,) = get_args(annotation)
        if isinstance(item, type) and issubclass(item, BaseModel):
            return item
    return None


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
