"""Registry of supported document types. Each one gets its own POST /extract/{key} endpoint.

To support a new document: add its data model in schemas.py, its prompt in prompts.py,
and register it here.
"""

from dataclasses import dataclass

from pydantic import BaseModel

from .prompts import KTP_PROMPT, NPWP_PROMPT
from .schemas import KTPData, KTPResponse, NPWPData, NPWPResponse


@dataclass(frozen=True)
class DocumentType:
    key: str                              # URL path segment and JSON schema name
    label: str                            # Human-readable name for docs and logs
    data_model: type[BaseModel]
    response_model: type[BaseModel]
    prompt: str
    log_fields: tuple[str, ...]           # Fields logged after a successful extraction

    @property
    def json_schema(self) -> dict:
        schema = self.data_model.model_json_schema()
        # Every field has a "" default, so pydantic marks none as required; without this,
        # vLLM's constrained decoding lets the model silently skip keys.
        schema["required"] = list(schema["properties"])
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

DOCUMENTS: tuple[DocumentType, ...] = (KTP, NPWP)
