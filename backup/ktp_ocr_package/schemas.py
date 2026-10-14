from pydantic import BaseModel


class KTPData(BaseModel):
    """Fields extracted from a KTP. Single source of truth for the prompt and JSON schema."""

    NIK: str = ""
    NAMA: str = ""
    TTL: str = ""
    JENIS_KELAMIN: str = ""
    GOL_DARAH: str = ""
    ALAMAT: str = ""
    RT_RW: str = ""
    KEL_DESA: str = ""
    KECAMATAN: str = ""
    AGAMA: str = ""
    STATUS_PERKAWINAN: str = ""
    PEKERJAAN: str = ""
    KEWARGANEGARAAN: str = ""
    BERLAKU_HINGGA: str = ""


class KTPResponse(BaseModel):
    success: bool
    data: KTPData
    raw_output: str


class HealthResponse(BaseModel):
    status: str
    backend: str
    model_loaded: bool
