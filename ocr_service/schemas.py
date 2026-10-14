from pydantic import BaseModel


class KTPData(BaseModel):
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


class NPWPData(BaseModel):
    NPWP: str = ""
    NAMA: str = ""
    NIK: str = ""
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


class HealthResponse(BaseModel):
    status: str
    backend: str
    model_loaded: bool
