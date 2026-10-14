"""Prompt construction and parsing of the model's answer into KTPData."""

import json
import re

from .schemas import KTPData

_EMPTY_TEMPLATE = json.dumps(KTPData().model_dump(), separators=(",", ":"))

PROMPT = f"""You are an OCR system specialized in Indonesian KTP (identity card) extraction.
Extract ALL text fields from this KTP image carefully and accurately.

Return ONLY valid JSON with exactly these keys, as compact JSON on a single line
(no indentation, no newlines, no markdown, no explanation). Use "" for unreadable fields:
{_EMPTY_TEMPLATE}"""

_JSON_OBJECT = re.compile(r"\{.*\}", re.DOTALL)
_TRAILING_COMMA = re.compile(r",\s*}")


class OutputParseError(ValueError):
    """The model's answer did not contain a usable JSON object."""


def parse_ktp(raw: str) -> KTPData:
    """Extract the outermost JSON object from `raw` and map it onto KTPData.

    Missing keys become "", unknown keys are dropped, non-string values are stringified.
    """
    fields = _load_json_object(raw)
    return KTPData(**{name: str(fields.get(name, "")) for name in KTPData.model_fields})


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
