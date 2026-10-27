from pydantic import BaseModel, Field


def _constrained(*, enum: list[str] | None = None, pattern: str | None = None):
    """A string field whose allowed values are only enforced in the JSON schema.

    vLLM's structured output uses the schema to constrain decoding, so the model cannot emit
    e.g. "PEREMPUA-J". Pydantic itself does not validate these, so the hf backend (which has
    no constrained decoding) still returns whatever the model read instead of failing.
    "" stays allowed everywhere for unreadable fields.
    """
    extra: dict = {}
    if enum is not None:
        extra["enum"] = [*enum, ""]
    if pattern is not None:
        extra["pattern"] = f"^({pattern})?$"
    return Field(default="", json_schema_extra=extra)


class KTPData(BaseModel):
    NIK: str = _constrained(pattern=r"[0-9]{16}")
    NAMA: str = ""
    TTL: str = ""
    JENIS_KELAMIN: str = _constrained(enum=["LAKI-LAKI", "PEREMPUAN"])
    GOL_DARAH: str = _constrained(enum=["A", "B", "AB", "O", "A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-", "-"])
    ALAMAT: str = ""
    RT_RW: str = _constrained(pattern=r"[0-9]{1,3}/[0-9]{1,3}")
    KEL_DESA: str = ""
    KECAMATAN: str = ""
    AGAMA: str = ""
    STATUS_PERKAWINAN: str = _constrained(enum=["BELUM KAWIN", "KAWIN", "CERAI HIDUP", "CERAI MATI"])
    PEKERJAAN: str = ""
    KEWARGANEGARAAN: str = ""
    BERLAKU_HINGGA: str = ""


class NPWPData(BaseModel):
    # 15-digit format "01.234.567.8-901.000" (older cards) or a plain 15/16-digit number
    NPWP: str = _constrained(pattern=r"[0-9]{2}\.[0-9]{3}\.[0-9]{3}\.[0-9]-[0-9]{3}\.[0-9]{3}|[0-9]{15,16}")
    NAMA: str = ""
    NIK: str = _constrained(pattern=r"[0-9]{16}")
    ALAMAT: str = ""
    KPP: str = ""
    TANGGAL_TERDAFTAR: str = ""


class KTPResponse(BaseModel):
    success: bool
    data: KTPData
    raw_output: str


class NPWPResponse(BaseModel):
    success: bool
    data: NPWPData
    raw_output: str


class Base64ImageRequest(BaseModel):
    image: str = Field(
        description="Image (jpg/png/webp, max 10 MB) as a base64 string, "
                    "with or without a data URI prefix such as 'data:image/jpeg;base64,'.",
        examples=["/9j/4AAQSkZJRgABAQ..."],
    )


class HealthResponse(BaseModel):
    status: str
    backend: str
    model_loaded: bool
