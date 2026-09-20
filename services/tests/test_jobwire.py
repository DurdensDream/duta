"""JobWire connector tests: the three header dialects, latin-1, date chaos."""

from pathlib import Path

import pytest

from duta.connectors.jobwire import read_drop

V1 = 'Full Name,E-mail,Phone,Job Ref,Applied,Location,Summary\n' \
     'José Muñoz,jose.munoz@gmail.com,614-555-0101,TECH-2026-001,24/07/2026,"Columbus, OH",Java dev\n' \
     'Ann Lee,ann@x.com,614-555-0102,TECH-2026-002,31/06/2026,Cleveland,QA lead\n'
V2 = 'name,email_address,phone_number,job_ref,applied_on,city,resume_summary\n' \
     'Sam Kim,sam.kim@x.com,3125550103,TECH-2026-003,2026-07-25,Chicago,Data engineer\n'
V3 = 'Name,Email,Phone #,JobRef,Date,Location,Notes\n' \
     'Tara Osei,tara@x.com,(614) 555-0104,TECH-2026-004,07/26/2026,Austin,DevOps\n'


def write(tmp_path: Path, name: str, content: str, encoding: str) -> Path:
    p = tmp_path / name
    p.write_bytes(content.encode(encoding))
    return p


def test_v1_latin1_header_and_dates(tmp_path):
    rows, report = read_drop(write(tmp_path, "jobwire_20260724.csv", V1, "latin-1"))
    assert report["encoding"] == "latin-1"
    assert report["date_format"] == "%d/%m/%Y"
    assert rows[0]["name"] == "José Muñoz"
    assert rows[0]["email"] == "jose.munoz@gmail.com"
    assert rows[0]["position_code"] == "TECH-2026-001"
    assert rows[0]["source_ref"] == "JW-20260724-0001"
    assert rows[0]["submitted_at"].day == 24
    assert rows[1]["submitted_at"] is None  # 31/06/2026 does not exist: NULL beats wrong
    assert report["dates_failed"] == 1


def test_v2_and_v3_header_dialects(tmp_path):
    rows2, rep2 = read_drop(write(tmp_path, "jobwire_20260725.csv", V2, "utf-8"))
    assert rep2["date_format"] == "%Y-%m-%d"
    assert rows2[0]["resume"] == "Data engineer"
    rows3, rep3 = read_drop(write(tmp_path, "jobwire_20260726.csv", V3, "utf-8"))
    assert rep3["date_format"] == "%m/%d/%Y"
    assert rows3[0]["phone"] == "(614) 555-0104"
    assert rows3[0]["submitted_at"].day == 26


def test_unknown_required_headers_fail_loudly(tmp_path):
    bad = "Person,Contact\nA,B\n"
    with pytest.raises(ValueError):
        read_drop(write(tmp_path, "jobwire_20260727.csv", bad, "utf-8"))


def test_date_format_detected_per_file_majority(tmp_path):
    # every row is day>12 in dd/mm; a lone ambiguous 03/04 row must follow the file's format
    content = ('Full Name,E-mail,Phone,Job Ref,Applied,Location,Summary\n'
               'A One,a@x.com,,R1,24/07/2026,,s\n'
               'B Two,b@x.com,,R2,25/07/2026,,s\n'
               'C Three,c@x.com,,R3,03/04/2026,,s\n')
    rows, report = read_drop(write(tmp_path, "jobwire_20260728.csv", content, "utf-8"))
    assert report["date_format"] == "%d/%m/%Y"
    assert rows[2]["submitted_at"].month == 4 and rows[2]["submitted_at"].day == 3
