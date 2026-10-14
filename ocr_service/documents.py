"""Registry of supported document types. Each one gets its own POST /extract/{key} endpoint.

To support a new document: add its data model in schemas.py and register it here.
"""

from dataclasses import dataclass

from pydantic import BaseModel

from .extraction import build_prompt
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
        return self.data_model.model_json_schema()


KTP = DocumentType(
    key="ktp",
    label="KTP",
    data_model=KTPData,
    response_model=KTPResponse,
    prompt=build_prompt("KTP (identity card)", "KTP", KTPData),
    log_fields=("NIK", "NAMA"),
)

NPWP = DocumentType(
    key="npwp",
    label="NPWP",
    data_model=NPWPData,
    response_model=NPWPResponse,
    prompt=build_prompt(
        "NPWP (tax ID card)",
        "NPWP card",
        NPWPData,
        field_notes="""
- NPWP: the tax number exactly as printed, keeping dots and dashes (e.g. 01.234.567.8-901.000),
  or the 16-digit number on newer cards.
- NIK: the 16-digit NIK if printed on the card, otherwise "".
- KPP: the issuing tax office name (e.g. KPP PRATAMA JAKARTA SETIABUDI SATU).
- TANGGAL_TERDAFTAR: the registration date as printed.
""",
        empty_when="unreadable or missing",
    ),
    log_fields=("NPWP", "NAMA"),
)

DOCUMENTS: tuple[DocumentType, ...] = (KTP, NPWP)
