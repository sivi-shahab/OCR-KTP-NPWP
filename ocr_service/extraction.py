"""Prompt construction and parsing of the model's answer into a document's data model."""

import json
import re
from typing import TypeVar

from pydantic import BaseModel

DataModel = TypeVar("DataModel", bound=BaseModel)

_JSON_OBJECT = re.compile(r"\{.*\}", re.DOTALL)
_TRAILING_COMMA = re.compile(r",\s*}")


class OutputParseError(ValueError):
    """The model's answer did not contain a usable JSON object."""


def build_prompt(
    document: str,
    image_label: str,
    data_model: type[BaseModel],
    field_notes: str = "",
    empty_when: str = "unreadable",
) -> str:
    """Build the extraction prompt; the JSON keys come straight from `data_model`.

    `document` e.g. "KTP (identity card)", `image_label` e.g. "KTP" ("this KTP image"),
    `empty_when` e.g. "unreadable or missing" ('Use "" for unreadable or missing fields').
    """
    template = json.dumps(data_model().model_dump(), separators=(",", ":"))
    notes = f"\nField notes:\n{field_notes.strip()}\n" if field_notes else ""
    return f"""You are an OCR system specialized in Indonesian {document} extraction.
Extract ALL text fields from this {image_label} image carefully and accurately.
{notes}
Return ONLY valid JSON with exactly these keys, as compact JSON on a single line
(no indentation, no newlines, no markdown, no explanation). Use "" for {empty_when} fields:
{template}"""


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
