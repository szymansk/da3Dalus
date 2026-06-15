#!/usr/bin/env python3
"""Parse D-Power PDF datasheets → data/cots/dpower.json.

Usage:
    poetry run python scripts/parse_dpower_pdfs.py

Source PDFs must be placed in:
    components/cots-assets/dpower/manuals/

The script writes (or overwrites) data/cots/dpower.json with a list of
component records in the canonical snapshot format.

PDFs are copyrighted and must NEVER be committed to the repository.
Only the extracted factual numbers (this JSON snapshot) are committed.
"""

from __future__ import annotations

import json
import logging
import re
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
PDF_DIR = REPO_ROOT / "components" / "cots-assets" / "dpower" / "manuals"
OUTPUT_PATH = REPO_ROOT / "data" / "cots" / "dpower.json"

MANUFACTURER = "D-Power"
SOURCE_URL_BASE = "https://www.d-power-modellbau.com"


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────


def _parse_float(s: str | None) -> float | None:
    """Parse a numeric string like '1.5A', '199g', '540U/min/V' → float."""
    if s is None:
        return None
    s = str(s).strip()
    # Extract first number (int or decimal)
    m = re.search(r"[\d]+(?:[.,]\d+)?", s)
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", "."))
    except ValueError:
        return None


def _parse_int(s: str | None) -> int | None:
    v = _parse_float(s)
    return int(v) if v is not None else None


def _parse_lipo_range(cell_str: str | None) -> tuple[int | None, int | None]:
    """Parse '3-6' or '3-5 S' → (3, 6)."""
    if not cell_str:
        return None, None
    m = re.search(r"(\d+)\s*[-–]\s*(\d+)", str(cell_str))
    if m:
        return int(m.group(1)), int(m.group(2))
    # single number
    m = re.search(r"(\d+)", str(cell_str))
    if m:
        v = int(m.group(1))
        return v, v
    return None, None


def _parse_dims_mm(dim_str: str | None) -> tuple[int | None, int | None, int | None]:
    """Parse 'L*B*H' or 'L x B x H' strings → (bbox_x, bbox_y, bbox_z) in mm."""
    if not dim_str:
        return None, None, None
    nums = re.findall(r"\d+", str(dim_str))
    if len(nums) >= 3:
        return int(nums[0]), int(nums[1]), int(nums[2])
    if len(nums) == 2:
        return int(nums[0]), int(nums[1]), None
    return None, None, None


def _parse_motor_dims(dim_str: str | None) -> tuple[int | None, int | None]:
    """Parse motor dimensions like '42x40mm' → (diameter_mm, length_mm)."""
    if not dim_str:
        return None, None
    nums = re.findall(r"\d+", str(dim_str))
    if len(nums) >= 2:
        return int(nums[0]), int(nums[1])
    return None, None


def _parse_shaft_mm(shaft_str: str | None) -> float | None:
    """Parse shaft diameter like '5.0' or '3.17' (already in mm in the datasheet)."""
    return _parse_float(shaft_str)


def _parse_cont_burst(current_str: str | None) -> tuple[float | None, float | None]:
    """Parse 'cont/burst A' like '20A/30A' or '55-65A' → (cont_a, burst_a)."""
    if not current_str:
        return None, None
    nums = re.findall(r"[\d]+(?:[.,]\d+)?", str(current_str))
    if len(nums) >= 2:
        return float(nums[0]), float(nums[1])
    if len(nums) == 1:
        return float(nums[0]), None
    return None, None


def _parse_bec_output(bec_str: str | None) -> str | None:
    """Normalise BEC output string, or None if no BEC."""
    if not bec_str or str(bec_str).strip() in ("---", "", "None"):
        return None
    return str(bec_str).strip()


# ──────────────────────────────────────────────────────────────────────────────
# Per-document extractors
# ──────────────────────────────────────────────────────────────────────────────


def _extract_al_motors(pdf_path: Path) -> list[dict]:
    """Extract AL outrunner motors from V3_AL-Manual_print_A5_Max.pdf.

    Table columns (12 per row, German headers):
      0: Bezeichnung (name)
      1: Abmessungen mm (dims)
      2: Leerlaufdrehzahl (KV RPM/V)
      3: Welle (shaft mm)
      4: LiPo (cell range)
      5: Leerlaufstrom (Io no-load A)
      6: empf. Strom (continuous A)
      7: Strom kurzz. (peak/burst A)
      8: Gewicht (mass g)
      9: Schubkraft (static thrust g)
      10: Best.-Nr. (art_no)
      11: Propeller (prop recommendations — ignored)
    """
    try:
        import pdfplumber
    except ImportError:
        logger.error("pdfplumber not installed. Run: poetry add pdfplumber")
        return []

    records: list[dict] = []
    warnings: list[str] = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                for table in page.extract_tables():
                    for row in table:
                        if not row or not row[0]:
                            continue
                        name_raw = str(row[0]).strip()
                        # Skip header rows
                        if "Bezeich" in name_raw or not name_raw.startswith("AL"):
                            continue

                        name = name_raw.replace("\n", " ").strip()
                        dim_str = str(row[1]).strip() if row[1] else None
                        kv_str = str(row[2]).strip() if row[2] else None
                        shaft_str = str(row[3]).strip() if row[3] else None
                        cell_str = str(row[4]).strip() if row[4] else None
                        io_str = str(row[5]).strip() if row[5] else None
                        cont_str = str(row[6]).strip() if row[6] else None
                        peak_str = str(row[7]).strip() if row[7] else None
                        mass_str = str(row[8]).strip() if row[8] else None
                        thrust_str = str(row[9]).strip() if row[9] else None
                        art_no = str(row[10]).strip() if row[10] else None

                        diam_mm, len_mm = _parse_motor_dims(dim_str)
                        kv = _parse_int(kv_str)
                        shaft_mm = _parse_shaft_mm(shaft_str)
                        cells_min, cells_max = _parse_lipo_range(cell_str)
                        io_a = _parse_float(io_str)
                        cont_a = _parse_float(cont_str)
                        peak_a = _parse_float(peak_str)
                        mass_g = _parse_int(mass_str)
                        thrust_g = _parse_int(thrust_str)

                        if kv is None:
                            warnings.append(
                                f"AL motor '{name}': could not parse KV from '{kv_str}'"
                            )

                        slug = name.lower().replace(" ", "-").replace("/", "-")
                        records.append(
                            {
                                "manufacturer": MANUFACTURER,
                                "name": name,
                                "component_type": "brushless_motor",
                                "mass_g": mass_g,
                                "bbox_x_mm": diam_mm,
                                "bbox_y_mm": diam_mm,
                                "bbox_z_mm": len_mm,
                                "model_ref": f"dpower/{slug}",
                                "source_url": f"{SOURCE_URL_BASE}/brushless-motor-al-serie",
                                "source_version": "AL manual V3",
                                "specs": {
                                    "kv_rpm_per_volt": kv,
                                    "io_no_load_a": io_a,
                                    "continuous_current_a": cont_a,
                                    "max_current_a": peak_a,
                                    "cells_lipo_min": cells_min,
                                    "cells_lipo_max": cells_max,
                                    "shaft_diameter_mm": shaft_mm,
                                    "static_thrust_g": thrust_g,
                                    "art_no": art_no,
                                },
                            }
                        )
    except Exception as exc:
        logger.error("Failed to parse AL motor PDF %s: %s", pdf_path, exc)
        return []

    for w in warnings:
        logger.warning(w)

    logger.info("AL motors: extracted %d records", len(records))
    return records


def _extract_ddrive_motors(pdf_path: Path) -> list[dict]:
    """Extract D-Drive geared motors from D-Drive-Manual.pdf.

    Each motor appears as a key-value table (2-column: param / value).
    Two motors on page 1: IL36 3.7:1 (Art.Nr. DPDDIL36371) and IL36 5:1 (DPDDIL3651).
    """
    try:
        import pdfplumber
    except ImportError:
        logger.error("pdfplumber not installed")
        return []

    records: list[dict] = []

    # Names extracted from the text header (not the table)
    motor_names = ["D-Drive IL36 3.7:1", "D-Drive IL36 5:1"]
    art_nos = ["DPDDIL36371", "DPDDIL3651"]
    lipo_ranges = [(3, 5), (4, 6)]

    try:
        with pdfplumber.open(pdf_path) as pdf:
            page = pdf.pages[0]
            tables = page.extract_tables()

            for idx, table in enumerate(tables[:2]):
                if not table:
                    continue
                kv_dict: dict[str, str] = {}
                for row in table:
                    if row and len(row) == 2 and row[0] and row[1]:
                        kv_dict[str(row[0]).strip()] = str(row[1]).strip()

                mass_g = _parse_int(kv_dict.get("Gewicht"))
                dims_str = kv_dict.get("Abmessungen", "")
                # '88 x 36mm' → bbox_z=88, bbox_x=bbox_y=36
                dims_nums = re.findall(r"\d+", dims_str)
                bbox_z = int(dims_nums[0]) if len(dims_nums) >= 1 else None
                bbox_xy = int(dims_nums[1]) if len(dims_nums) >= 2 else None

                shaft_str = kv_dict.get("Wellendurchmesser", "")
                shaft_mm = _parse_float(shaft_str)

                kv = _parse_int(kv_dict.get("Drehzahl"))
                peak_a = _parse_float(kv_dict.get("Strom kurz"))
                cont_range = kv_dict.get("empfohlener Strom", "")
                cont_a, _ = _parse_cont_burst(cont_range)
                eta_pct = _parse_float(kv_dict.get("Wirkungsgrad"))

                cells_min, cells_max = lipo_ranges[idx] if idx < len(lipo_ranges) else (None, None)
                name = motor_names[idx] if idx < len(motor_names) else f"D-Drive IL36 variant {idx}"
                art_no = art_nos[idx] if idx < len(art_nos) else None

                slug = name.lower().replace(" ", "-").replace(":", "-").replace(".", "-")
                records.append(
                    {
                        "manufacturer": MANUFACTURER,
                        "name": name,
                        "component_type": "brushless_motor",
                        "mass_g": mass_g,
                        "bbox_x_mm": bbox_xy,
                        "bbox_y_mm": bbox_xy,
                        "bbox_z_mm": bbox_z,
                        "model_ref": f"dpower/{slug}",
                        "source_url": f"{SOURCE_URL_BASE}/d-drive",
                        "source_version": "D-Drive manual",
                        "specs": {
                            "kv_rpm_per_volt": kv,
                            "io_no_load_a": None,  # not in datasheet
                            "continuous_current_a": cont_a,
                            "max_current_a": peak_a,
                            "cells_lipo_min": cells_min,
                            "cells_lipo_max": cells_max,
                            "shaft_diameter_mm": shaft_mm,
                            "static_thrust_g": None,  # per-prop, not summarised
                            "art_no": art_no,
                            # '... 3.7:1' → 3.7 (ratio is the value BEFORE the colon)
                            "gear_ratio": (
                                _parse_float(name.split(":")[0].split()[-1])
                                if ":" in name
                                else None
                            ),
                            "efficiency_pct": eta_pct,
                        },
                    }
                )
    except Exception as exc:
        logger.error("Failed to parse D-Drive PDF %s: %s", pdf_path, exc)
        return []

    logger.info("D-Drive motors: extracted %d records", len(records))
    return records


def _extract_avicon_escs(pdf_path: Path) -> list[dict]:
    """Extract Avicon standard ESCs from Avicon Anleitung_web.pdf.

    The ESC spec table (8 columns) appears on both pages (DE + EN).
    We use the English table from page 2 (more reliable column headers).

    Columns:
      0: Type (name)
      1: PN#Model (art_no)
      2: Cont./Burst Current(A)
      3: Battery cell NiXX/Lipo
      4: Weight (g)
      5: BEC Output
      6: Size(mm) L*W*H
      7: User Program (ignored)
    """
    try:
        import pdfplumber
    except ImportError:
        logger.error("pdfplumber not installed")
        return []

    records: list[dict] = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Use page 2 (English) — index 1
            page = pdf.pages[1]
            tables = page.extract_tables()
            target_table = None
            for table in tables:
                if table and len(table) > 2 and table[0] and "Type" in str(table[0]):
                    target_table = table
                    break
            if target_table is None:
                # Fall back to page 1 (German)
                page = pdf.pages[0]
                for table in page.extract_tables():
                    if table and len(table) > 2 and table[0] and "Typ" in str(table[0]):
                        target_table = table
                        break

            if not target_table:
                logger.error("Avicon: could not locate ESC spec table")
                return []

            for row in target_table[1:]:  # skip header
                if not row or not row[0]:
                    continue
                name = str(row[0]).strip()
                if not name.startswith("AVICON"):
                    continue
                art_no = str(row[1]).strip() if row[1] else None
                cont_burst = str(row[2]).strip() if row[2] else None
                cell_str = str(row[3]).strip() if row[3] else None
                mass_str = str(row[4]).strip() if row[4] else None
                bec_str = str(row[5]).strip() if row[5] else None
                size_str = str(row[6]).strip() if row[6] else None

                cont_a, burst_a = _parse_cont_burst(cont_burst)
                # cell range: '5-18NC\2-6Lipo' → LiPo part
                lipo_m = re.search(r"(\d+)-(\d+)\s*Lipo", str(cell_str), re.IGNORECASE)
                if lipo_m:
                    cells_min, cells_max = int(lipo_m.group(1)), int(lipo_m.group(2))
                else:
                    cells_min, cells_max = _parse_lipo_range(cell_str)

                mass_g = _parse_int(mass_str)
                bec_output = _parse_bec_output(bec_str)
                bbox_x, bbox_y, bbox_z = _parse_dims_mm(size_str)

                slug = name.lower().replace(" ", "-")
                records.append(
                    {
                        "manufacturer": MANUFACTURER,
                        "name": name,
                        "component_type": "esc",
                        "mass_g": mass_g,
                        "bbox_x_mm": bbox_x,
                        "bbox_y_mm": bbox_y,
                        "bbox_z_mm": bbox_z,
                        "model_ref": f"dpower/{slug}",
                        "source_url": f"{SOURCE_URL_BASE}/avicon-regler",
                        "source_version": "Avicon manual",
                        "specs": {
                            "continuous_current_a": cont_a,
                            "max_current_a": burst_a,
                            "cells_lipo_min": cells_min,
                            "cells_lipo_max": cells_max,
                            "bec_output": bec_output,
                            "art_no": art_no,
                        },
                    }
                )
    except Exception as exc:
        logger.error("Failed to parse Avicon PDF %s: %s", pdf_path, exc)
        return []

    logger.info("Avicon ESCs: extracted %d records", len(records))
    return records


def _extract_avicon_pro_escs_manual() -> list[dict]:
    """Avicon PRO ESCs — image-based PDF; data entered manually from the printed sheet.

    The Avicon PRO Anleitung_web.pdf is an image-based scan with no extractable text.
    D-Power publishes the Avicon PRO specs on their website; the three models are:

    Source: Avicon PRO Anleitung_web.pdf cover page (visual inspection)
      - AVICON PRO 65A  HV  (DPAC065HV): 65/80A,  HV 6-14S, ~120g, BEC 5V/8A
      - AVICON PRO 125A HV (DPAC125HV): 125/150A, HV 6-14S, ~155g, BEC 5V/8A
      - AVICON PRO 130A HV (DPAC130HV): 130/160A, HV 6-14S, ~160g, BEC 5V/8A

    Note: mass/dims approximated from visual; update if exact figures become available.
    """
    records = []
    models = [
        {
            "name": "AVICON PRO 65A HV",
            "art_no": "DPAC065HV",
            "cont_a": 65.0,
            "burst_a": 80.0,
            "cells_min": 6,
            "cells_max": 14,
            "mass_g": 120,
            "bec": "5V / 8A",
        },
        {
            "name": "AVICON PRO 125A HV",
            "art_no": "DPAC125HV",
            "cont_a": 125.0,
            "burst_a": 150.0,
            "cells_min": 6,
            "cells_max": 14,
            "mass_g": 155,
            "bec": "5V / 8A",
        },
        {
            "name": "AVICON PRO 130A HV",
            "art_no": "DPAC130HV",
            "cont_a": 130.0,
            "burst_a": 160.0,
            "cells_min": 6,
            "cells_max": 14,
            "mass_g": 160,
            "bec": "5V / 8A",
        },
    ]
    for m in models:
        slug = m["name"].lower().replace(" ", "-")
        records.append(
            {
                "manufacturer": MANUFACTURER,
                "name": m["name"],
                "component_type": "esc",
                "mass_g": m["mass_g"],
                "bbox_x_mm": None,
                "bbox_y_mm": None,
                "bbox_z_mm": None,
                "model_ref": f"dpower/{slug}",
                "source_url": f"{SOURCE_URL_BASE}/avicon-pro-regler",
                "source_version": "Avicon PRO manual (visual, image-PDF)",
                "specs": {
                    "continuous_current_a": m["cont_a"],
                    "max_current_a": m["burst_a"],
                    "cells_lipo_min": m["cells_min"],
                    "cells_lipo_max": m["cells_max"],
                    "bec_output": m["bec"],
                    "art_no": m["art_no"],
                },
            }
        )
    logger.info("Avicon PRO ESCs: %d records (manual entry, image PDF)", len(records))
    return records


def _extract_antares_escs(pdf_path: Path) -> list[dict]:
    """Extract Antares ESCs from manual_Antares_V3.pdf.

    Table on page 3 (6 columns):
      0: Typ (name)
      1: Dauer/kurz 10s (cont / burst A)
      2: Zellenzahl Lipo/Nixx
      3: Gewicht g
      4: BEC Ausgang
      5: Abmessungen mm
    """
    try:
        import pdfplumber
    except ImportError:
        logger.error("pdfplumber not installed")
        return []

    records: list[dict] = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            page = pdf.pages[2]  # page 3, 0-indexed
            tables = page.extract_tables()
            target_table = None
            for table in tables:
                if table and len(table) > 2 and table[0] and "Typ" in str(table[0]):
                    target_table = table
                    break

            if not target_table:
                logger.error("Antares: could not locate ESC spec table on page 3")
                return []

            # Row 1 is a sub-header ('None', 'Dauerstrom A', ...)
            for row in target_table[2:]:  # skip header + sub-header
                if not row or not row[0]:
                    continue
                name = str(row[0]).strip()
                if not name.startswith("Antares"):
                    continue

                cont_burst_str = str(row[1]).strip() if row[1] else None
                cell_str = str(row[2]).strip() if row[2] else None
                mass_str = str(row[3]).strip() if row[3] else None
                bec_str = str(row[4]).strip() if row[4] else None
                size_str = str(row[5]).strip() if row[5] else None

                cont_a, burst_a = _parse_cont_burst(cont_burst_str)

                # cell range: '2-4 / 5-12' — LiPo is the first part
                lipo_m = re.match(r"(\d+)-(\d+)", str(cell_str))
                if lipo_m:
                    cells_min, cells_max = int(lipo_m.group(1)), int(lipo_m.group(2))
                else:
                    cells_min, cells_max = None, None

                mass_g = _parse_int(mass_str)
                bec_output = _parse_bec_output(bec_str)
                bbox_x, bbox_y, bbox_z = _parse_dims_mm(size_str)

                slug = name.lower().replace(" ", "-")
                records.append(
                    {
                        "manufacturer": MANUFACTURER,
                        "name": name,
                        "component_type": "esc",
                        "mass_g": mass_g,
                        "bbox_x_mm": bbox_x,
                        "bbox_y_mm": bbox_y,
                        "bbox_z_mm": bbox_z,
                        "model_ref": f"dpower/{slug}",
                        "source_url": f"{SOURCE_URL_BASE}/antares-regler",
                        "source_version": "Antares V3 manual",
                        "specs": {
                            "continuous_current_a": cont_a,
                            "max_current_a": burst_a,
                            "cells_lipo_min": cells_min,
                            "cells_lipo_max": cells_max,
                            "bec_output": bec_output,
                            "art_no": None,  # not in the Antares table
                        },
                    }
                )
    except Exception as exc:
        logger.error("Failed to parse Antares PDF %s: %s", pdf_path, exc)
        return []

    logger.info("Antares ESCs: extracted %d records", len(records))
    return records


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────


def parse_all(pdf_dir: Path = PDF_DIR) -> list[dict]:
    """Parse all D-Power PDFs and return the combined record list."""
    all_records: list[dict] = []

    pdfs = {
        "al_motor": pdf_dir / "V3_AL-Manual_print_A5_Max.pdf",
        "ddrive": pdf_dir / "D-Drive-Manual.pdf",
        "avicon": pdf_dir / "Avicon Anleitung_web.pdf",
        "avicon_pro": pdf_dir / "Avicon PRO Anleitung_web.pdf",
        "antares": pdf_dir / "manual_Antares_V3.pdf",
    }

    missing = [name for name, path in pdfs.items() if not path.exists()]
    if missing:
        logger.warning(
            "Missing PDFs (run without them, skipping): %s",
            ", ".join(missing),
        )

    if pdfs["al_motor"].exists():
        all_records.extend(_extract_al_motors(pdfs["al_motor"]))
    if pdfs["ddrive"].exists():
        all_records.extend(_extract_ddrive_motors(pdfs["ddrive"]))
    if pdfs["avicon"].exists():
        all_records.extend(_extract_avicon_escs(pdfs["avicon"]))
    # Avicon PRO is image-based: manual entry regardless of PDF presence
    all_records.extend(_extract_avicon_pro_escs_manual())
    if pdfs["antares"].exists():
        all_records.extend(_extract_antares_escs(pdfs["antares"]))

    return all_records


def write_snapshot(records: list[dict], output_path: Path = OUTPUT_PATH) -> None:
    """Atomically write the snapshot JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = output_path.with_suffix(".tmp.json")
    tmp.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(output_path)
    logger.info("Wrote %d records to %s", len(records), output_path)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
        stream=sys.stderr,
    )

    if not PDF_DIR.exists():
        logger.error(
            "PDF directory not found: %s\nPlace the D-Power PDFs there before running this script.",
            PDF_DIR,
        )
        sys.exit(1)

    records = parse_all()
    if not records:
        logger.error("No records extracted — check PDF availability and parser logs")
        sys.exit(1)

    motors = sum(1 for r in records if r["component_type"] == "brushless_motor")
    escs = sum(1 for r in records if r["component_type"] == "esc")
    print(f"Extracted: {motors} motors + {escs} ESCs = {len(records)} total")

    write_snapshot(records)
    print(f"Snapshot written to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
