"""
ALICE Legacy Extraction — extract_opus.py
Extracts course content from SQL Server to individual XML files.

Setup (run once from the /python folder):
    uv venv .venv
    .venv\Scripts\activate
    uv pip install pyodbc lxml

Usage:
    python extract_opus.py
Output:
    ../data/<id_opus>.xml for each ID in COURSE_IDS
"""

import pyodbc
from lxml import etree
from pathlib import Path

# ── Configuration ─────────────────────────────────────────────────────────────

CONNECTION_STRING = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=localhost;"
    "DATABASE=ALICE;"
    "Trusted_Connection=yes;"
)

COURSE_IDS = [
    1073,
    1023,
    1043,
    1053,
    1073,
    1093,
    1133,
    1193,
    1214,
    1224,
    2214,
    2233,
    3013,
    3213,
    3613,
    4213,
    4214,
    4221,
    4222,
    4223,
    4224,
    4225,
    4226,
    4227,
    4228,
    4229,
    4230,
    4231,
    4232,
    4233
    # add more IDs here
]

OUTPUT_DIR = Path(__file__).parent.parent / "data"

# ── Main ──────────────────────────────────────────────────────────────────────

def extract_course(cursor, id_opus: int) -> str:
    """Call the stored procedure and return the XML string."""
    cursor.execute("EXEC extract_opus @id_opus = ?", id_opus)
    row = cursor.fetchone()
    if row is None or row[0] is None:
        raise ValueError(f"No data returned for id_opus={id_opus}")
    return row[0]


def validate_and_write(xml_string: str, path: Path) -> None:
    """Parse with lxml to validate well-formedness, then write."""
    root = etree.fromstring(xml_string.encode("utf-8"))
    tree = etree.ElementTree(root)
    tree.write(
        str(path),
        encoding="utf-8",
        xml_declaration=True,
        pretty_print=True,
    )


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    conn = pyodbc.connect(CONNECTION_STRING)
    cursor = conn.cursor()

    for id_opus in COURSE_IDS:
        print(f"Extracting id_opus={id_opus} ...", end=" ")
        try:
            xml_string = extract_course(cursor, id_opus)
            out_path = OUTPUT_DIR / f"{id_opus}.xml"
            validate_and_write(xml_string, out_path)
            print(f"OK → {out_path}")
        except Exception as e:
            print(f"FAILED — {e}")

    cursor.close()
    conn.close()


if __name__ == "__main__":
    main()
