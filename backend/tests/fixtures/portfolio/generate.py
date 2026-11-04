"""Generate fictional documents deterministically; never reads user documents."""

from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from docx import Document

LINES = {
    "strong": [
        "Avery Example",
        "avery@example.com",
        "FICTIONAL PORTFOLIO RESUME",
        "Backend Engineer - Fictional Orchard Studio, 2020-2026",
        "Built Python FastAPI services with SQL and tested recovery.",
        "Six years of fictional experience. Skills: Python, FastAPI, SQL.",
    ],
    "review": [
        "Riley Sample",
        "riley@example.com",
        "FICTIONAL PORTFOLIO RESUME",
        "Support Assistant - Fictional Orchard Studio, 2025-2026",
        "Answered customer support enquiries. One year of fictional experience.",
        "Skills: Customer support. Seeking a career change.",
    ],
}


def pdf(lines):
    stream = b"BT /F1 12 Tf 50 760 Td 18 TL "
    for line in lines:
        stream += b"(" + line.encode("ascii") + b") Tj T* "
    stream += b"ET"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length "
        + str(len(stream)).encode()
        + b" >>\nstream\n"
        + stream
        + b"\nendstream",
        b"<< /Author (Fictional Portfolio Generator) /Title (Synthetic Resume) /Creator (Portfolio Fixtures) >>",
    ]
    output, offsets = b"%PDF-1.4\n", [0]
    for i, obj in enumerate(objects, 1):
        offsets.append(len(output))
        output += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"
    start = len(output)
    output += f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode()
    output += b"".join(f"{o:010} 00000 n \n".encode() for o in offsets[1:])
    return (
        output
        + f"trailer << /Size {len(offsets)} /Root 1 0 R /Info 6 0 R >>\nstartxref\n{start}\n%%EOF\n".encode()
    )


def generate(destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    for name, lines in LINES.items():
        (destination / (name + ".pdf")).write_bytes(pdf(lines))
        doc = Document()
        props = doc.core_properties
        props.author = props.last_modified_by = "Fictional Portfolio Generator"
        props.title = "Synthetic Resume"
        props.created = props.modified = datetime(2026, 1, 1, tzinfo=UTC)
        props.revision = 1
        for line in lines:
            doc.add_paragraph(line)
        buffer = BytesIO()
        doc.save(buffer)
        with (
            ZipFile(buffer) as source,
            ZipFile(destination / (name + ".docx"), "w") as target,
        ):
            for entry in sorted(source.namelist()):
                info = ZipInfo(entry, (2026, 1, 1, 0, 0, 0))
                info.compress_type = ZIP_DEFLATED
                target.writestr(info, source.read(entry))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("destination", type=Path)
    generate(parser.parse_args().destination)
