#!/usr/bin/env python3
"""Verify the exported contact-probe data against Figure 9 of a paper PDF, optionally adopting that PDF.

Use this when the paper PDF changes but Figure 9 does not (for example, adding authors or an arXiv
header). Unlike export_contact_data.py, it needs no private probe files: it checks the 320 means in
assets/data/contact-probes.json against the plotted curves, panel by panel, with the same linear-axis
criterion as the exporter.

    python scripts/verify_contact_data.py --paper new.pdf            # verify only
    python scripts/verify_contact_data.py --paper new.pdf --adopt    # also copy to assets/paper.pdf
                                                                     # and update both hashes

Build-time dependencies: NumPy and PyMuPDF.
"""

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pymupdf


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "assets/data/contact-probes.json"
MANIFEST = ROOT / "assets/manifest.json"
TARGET_ORDER = ["grasp", "normal", "tangential", "vector"]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(paper, data):
    """Return the largest PDF-point error over all 320 values; raise if the figure does not match."""
    document = pymupdf.open(paper)
    page = next((p for p in document if "Figure 9:" in p.get_text()), None)
    if page is None:
        raise SystemExit("No 'Figure 9:' caption found in the PDF.")
    caption_y = page.search_for("Figure 9:")[0].y0
    # Data curves: 7-segment polylines in the plot area directly above the caption.
    curves = [d for d in page.get_drawings()
              if d["rect"].y1 < caption_y and caption_y - d["rect"].y0 < 140
              and d["rect"].width > 50 and len(d["items"]) == 7]
    if len(curves) != 40:
        raise SystemExit(f"Expected 40 Figure 9 curves, found {len(curves)}; the figure layout changed.")
    worst = 0.0
    for ti, key in enumerate(TARGET_ORDER):
        values, ys = [], []
        for bi, count in enumerate(data["budgets"]):
            for mi, model in enumerate(["prior", "scratch"]):
                curve = curves[ti * 10 + bi * 2 + mi]
                if not all(item[0] == "l" for item in curve["items"]):
                    raise SystemExit("Unexpected curve geometry in Figure 9.")
                if (curve["dashes"] == "[] 0") != (model == "prior"):
                    raise SystemExit("Solid/dashed curve order differs from prior/scratch.")
                points = [item[1] for item in curve["items"]] + [curve["items"][-1][2]]
                values += data["targets"][key]["series"][str(count)][model]["mean"]
                ys += [point.y for point in points]
        # Each panel has its own linear y-axis; all 80 points must fit one transform.
        slope, intercept = np.polyfit(values, ys, 1)
        residual = float(np.max(np.abs(np.array(ys) - (slope * np.array(values) + intercept))))
        if not (slope < 0 and residual < 0.001):
            raise SystemExit(f"Figure 9 panel '{key}' does not match the data (max error {residual:.4f} pt).")
        worst = max(worst, residual)
    return worst


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--paper", type=Path, required=True)
    parser.add_argument("--adopt", action="store_true",
                        help="copy the PDF to assets/paper.pdf and update the manifest and data hashes")
    parser.add_argument("--status", default="Preprint", help="manuscript status recorded in the manifest")
    args = parser.parse_args()
    data = json.loads(DATA.read_text())
    worst = verify(args.paper, data)
    print(f"Verified all 320 Figure 9 values (max error {worst:.6f} PDF pt).")
    if not args.adopt:
        return
    target = ROOT / "assets/paper.pdf"
    if args.paper.resolve() != target.resolve():
        shutil.copyfile(args.paper, target)
    digest = sha256(target)
    data["manuscript_sha256"] = digest
    DATA.write_text(json.dumps(data, indent=2) + "\n")
    manifest = json.loads(MANIFEST.read_text())
    manifest["manuscript"].update(source_sha256=digest, pages=len(pymupdf.open(target)), status=args.status)
    manifest["assets"]["paper.pdf"] = {"source": f"{args.status} PDF, published unmodified.", "sha256": digest}
    manifest["assets"]["data/contact-probes.json"]["sha256"] = sha256(DATA)
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    print(f"Adopted {args.paper.name} as assets/paper.pdf ({digest[:12]}); manifest and data hashes updated.")


if __name__ == "__main__":
    sys.exit(main())
