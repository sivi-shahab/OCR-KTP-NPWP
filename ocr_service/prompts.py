"""Extraction prompts, one per document type.

Each prompt describes the card's layout and the expected format of every field, so the
model knows where to look and what a valid value looks like. The JSON keys at the end come
straight from the document's data model, so the prompt never drifts from the schema.
"""

import json

from pydantic import BaseModel

from .schemas import KTPData, NPWPData


def _output_instructions(data_model: type[BaseModel]) -> str:
    template = json.dumps(data_model().model_dump(), separators=(",", ":"))
    return f"""Return ONLY valid JSON with exactly these keys, as compact JSON on a single line
(no indentation, no newlines, no markdown, no explanation):
{template}"""


KTP_PROMPT = f"""You are an OCR system for Indonesian electronic identity cards (KTP-el).
Read the text in this KTP image exactly as printed. Do not guess, translate, or correct spelling.

Card layout: the header shows PROVINSI and KABUPATEN/KOTA. Below it, the NIK is printed in large
digits. The fields follow as "Label : value" rows on the left, always in this order:
Nama, Tempat/Tgl Lahir, Jenis Kelamin (with Gol. Darah at the right end of the same row), Alamat,
RT/RW, Kel/Desa, Kecamatan, Agama, Status Perkawinan, Pekerjaan, Kewarganegaraan, Berlaku Hingga.
The photo, the issuing city/date and the signature are on the right and are not fields.

Read each field from the row with its own label. Some values (often Gol. Darah) are blank; a blank
value must never be filled with the value from the next row.

Field rules:
- NIK: exactly 16 digits, no spaces or punctuation. It contains only digits, so read O as 0,
  I/l as 1, B as 8, S as 5.
- NAMA: full name, as printed.
- TTL: "Tempat/Tgl Lahir" as "PLACE, DD-MM-YYYY".
- JENIS_KELAMIN: "LAKI-LAKI" or "PEREMPUAN".
- GOL_DARAH: only the short value after "Gol. Darah" on the Jenis Kelamin row: A, B, AB or O
  (possibly with + or -), "-" if it shows a dash, or "" if blank. It is never an address or a name.
- ALAMAT: the value on the "Alamat" row (it may start with JL, KP, DUSUN, PERUM, KOMP, etc.).
  Do not include RT/RW, Kel/Desa or Kecamatan.
- RT_RW: the two 3-digit numbers on the "RT/RW" row as "NNN/NNN", without spaces.
- KEL_DESA: value on the "Kel/Desa" row.
- KECAMATAN: value on the "Kecamatan" row (not the KABUPATEN/KOTA from the header).
- AGAMA: value on the "Agama" row (e.g. ISLAM, KRISTEN, KATHOLIK, HINDU, BUDDHA, KHONGHUCU).
- STATUS_PERKAWINAN: "BELUM KAWIN", "KAWIN", "CERAI HIDUP" or "CERAI MATI".
- PEKERJAAN: occupation as printed.
- KEWARGANEGARAAN: usually "WNI".
- BERLAKU_HINGGA: value on the "Berlaku Hingga" row: "SEUMUR HIDUP" or a date "DD-MM-YYYY".
  It is NOT the issuing date printed under the photo.

Use "" for any field that is unreadable. Never take a value from a different row.

{_output_instructions(KTPData)}"""


NPWP_PROMPT = f"""You are an OCR system for Indonesian tax ID cards (kartu NPWP) issued by
Direktorat Jenderal Pajak (DJP).
Read the text in this NPWP card image exactly as printed. Do not guess, translate, or correct spelling.

Card layout: the DJP logo and "KEMENTERIAN KEUANGAN REPUBLIK INDONESIA / DIREKTORAT JENDERAL PAJAK"
header are at the top. Below it are the NPWP number, the taxpayer name, an optional NIK, the
address, the issuing tax office (KPP) and the registration date.

Field rules:
- NPWP: the tax number exactly as printed. Older cards use 15 digits formatted as
  "NN.NNN.NNN.N-NNN.NNN" (e.g. "01.234.567.8-901.000"): keep the dots and dash. Newer cards use a
  16-digit number: write it without spaces. The number contains only digits (read O as 0, I/l as 1,
  B as 8, S as 5).
- NAMA: the taxpayer's name (person or company) in capitals, as printed.
- NIK: the 16-digit NIK only if it is printed on the card, otherwise "". Do not copy the NPWP here.
- ALAMAT: the taxpayer's address, joining all address lines (street, RT/RW, kelurahan, kecamatan,
  city) with a single space. Do not include the KPP name or the DJP header.
- KPP: the issuing tax office, usually starting with "KPP" (e.g. "KPP PRATAMA JAKARTA SETIABUDI SATU").
- TANGGAL_TERDAFTAR: the value after "Tanggal Terdaftar" exactly as printed (e.g. "17-08-2015" or
  "17 Agustus 2015").

Use "" for any field that is unreadable or not printed on the card. Never take a value from a
different line.

{_output_instructions(NPWPData)}"""
