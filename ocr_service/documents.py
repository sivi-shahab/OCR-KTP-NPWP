"""Registry of supported document types. Each one gets its own POST /extract/{key} endpoint.

To support a new document: add its data model in schemas.py, its prompt in prompts.py,
and register it here.
"""

from dataclasses import dataclass

from pydantic import BaseModel

from .prompts import KK_PROMPT, KTP_PROMPT, NPWP_PROMPT
from .schemas import KKData, KKResponse, KTPData, KTPResponse, NPWPData, NPWPResponse


@dataclass(frozen=True)
class DocumentType:
    key: str                              # URL path segment and JSON schema name
    label: str                            # Human-readable name for docs and logs
    data_model: type[BaseModel]
    response_model: type[BaseModel]
    prompt: str
    log_fields: tuple[str, ...]           # Fields logged after a successful extraction
    # Overrides of Settings.max_pixels / Settings.max_new_tokens for larger documents
    max_pixels: int | None = None
    max_new_tokens: int | None = None

    @property
    def json_schema(self) -> dict:
        schema = self.data_model.model_json_schema()
        # Every field has a default, so pydantic marks none as required; without this,
        # vLLM's constrained decoding lets the model silently skip keys.
        for model_schema in (schema, *schema.get("$defs", {}).values()):
            model_schema["required"] = list(model_schema["properties"])
        return schema


KTP = DocumentType(
    key="ktp",
    label="KTP",
    data_model=KTPData,
    response_model=KTPResponse,
    prompt=KTP_PROMPT,
    log_fields=("NIK", "NAMA"),
)

NPWP = DocumentType(
    key="npwp",
    label="NPWP",
    data_model=NPWPData,
    response_model=NPWPResponse,
    prompt=NPWP_PROMPT,
    log_fields=("NPWP", "NAMA"),
)

KK = DocumentType(
    key="kk",
    label="Kartu Keluarga",
    data_model=KKData,
    response_model=KKResponse,
    prompt=KK_PROMPT,
    log_fields=("NO_KK", "NAMA_KEPALA_KELUARGA"),
    # A KK is an A4 sheet with small table text: it needs more pixels than an ID card, and
    # one JSON object per family member needs far more output tokens.
    max_pixels=3200 * 28 * 28,
    max_new_tokens=3072,
)

DOCUMENTS: tuple[DocumentType, ...] = (KTP, NPWP, KK)
