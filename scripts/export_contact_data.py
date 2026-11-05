#!/usr/bin/env python3
"""Export anonymous Figure 9 data and verify it against the manuscript vectors.

Build-time dependencies: NumPy and PyMuPDF. Runtime uses only the exported JSON.
The scratch summaries retain per-output R². Recover per-output RMSE from the
identical held-out label variance, then average outputs and policy seeds in the
same order as the manuscript. Never infer RMSE from an averaged R².
"""

import argparse
import csv
import hashlib
import json
from html import escape
from pathlib import Path

import numpy as np
import pymupdf


ROOT = Path(__file__).resolve().parents[1]
BUDGETS = [200, 500, 1000, 2000, 4000]
SEEDS = [11, 22, 33]
LAYERS = [f"L{i}" for i in range(1, 9)]
TARGETS = [
    ("grasp", "B_reg", "f_grasp", "Total grasp force", "The combined normal force of the grasp."),
    ("normal", "F_n", "finger_normal", "Normal force", "The force pressing into a surface, for each finger."),
    ("tangential", "F_t", "finger_tangent", "Tangential force", "The force along a surface, for each finger."),
    ("vector", "F_vec", "finger_force", "3D force", "The three force components at each finger."),
]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def budget(value):
    return 4000 if value == "full" else int(value)


def vector_figure(data, path):
    """Readable two-by-two vector layout; every curve uses the verified means."""
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1360 960" role="img" aria-labelledby="title desc">',
             '<title id="title">Contact-force readout across decoder layers</title>',
             '<desc id="desc">Figure 9 numerical results. Four force targets and five demonstration budgets. Solid curves are the RL prior; dashed curves are the scratch decoder. Lower RMSE is better.</desc>',
             '<rect width="1360" height="960" fill="white"/>',
             '<g font-family="Arial, Helvetica, sans-serif" fill="#202a29">']

    def text(x, y, value, size=18, extra=""):
        parts.append(f'<text x="{x}" y="{y}" font-size="{size}" {extra}>{escape(str(value))}</text>')

    text(60, 46, "Contact forces are easier to read out.", 30, 'font-weight="600"')
    text(60, 77, "Mean over three policy seeds · RMSE in newtons · Lower is better", 17, 'fill="#596764"')
    colors = ["#60398b", "#3b679b", "#19877e", "#429457", "#758d19"]
    text(60, 117, "Visual demonstrations", 16)
    for i, (count, color) in enumerate(zip(BUDGETS, colors)):
        px = 250 + i * 123
        parts.append(f'<path d="M{px} 111h28" stroke="{color}" stroke-width="3"/>')
        text(px + 36, 117, f"{count:,}", 16)
    parts.append('<path d="M925 111h35" stroke="#354740" stroke-width="3"/>')
    text(969, 117, "RL prior", 16)
    parts.append('<path d="M1080 111h35" stroke="#354740" stroke-width="3" stroke-dasharray="7 5"/>')
    text(1124, 117, "Scratch decoder", 16)
    axes = {
        "grasp": (9.4, 12.6, [9.5, 10, 10.5, 11, 11.5, 12, 12.5]),
        "normal": (3.75, 4.7, [3.8, 4, 4.2, 4.4, 4.6]),
        "tangential": (3.6, 4.08, [3.6, 3.7, 3.8, 3.9, 4]),
        "vector": (3.7, 4.5, [3.7, 3.9, 4.1, 4.3, 4.5]),
    }
    for ti, (key, target) in enumerate(data["targets"].items()):
        ox, oy = 60 + (ti % 2) * 660, 157 + (ti // 2) * 383
        text(ox, oy + 18, target["name"], 23, 'font-weight="600"')
        text(ox, oy + 43, "RMSE (N)", 14, 'fill="#596764"')
        left, right, top, bottom = ox + 53, ox + 570, oy + 62, oy + 301
        low, high, ticks = axes[key]
        x = lambda i: left + i * (right - left) / 7
        y = lambda value: bottom - (value - low) / (high - low) * (bottom - top)
        for tick in ticks:
            parts.append(f'<path d="M{left} {y(tick):.3f}H{right}" stroke="#e1e7df" stroke-width="1"/>')
            text(left - 12, round(y(tick) + 6, 3), f"{tick:.1f}", 16, 'text-anchor="end" fill="#596764"')
        for i in range(8):
            text(round(x(i), 3), bottom + 27, f"L{i+1}", 16, 'text-anchor="middle" fill="#596764"')
        text((left + right) / 2, bottom + 57, "Action-decoder layer", 16, 'text-anchor="middle" fill="#596764"')
        for count, color in zip(BUDGETS, colors):
            for model in ["scratch", "prior"]:
                values = target["series"][str(count)][model]["mean"]
                line = " ".join(f'{"M" if i == 0 else "L"}{x(i):.3f} {y(v):.3f}' for i, v in enumerate(values))
                dash = ' stroke-dasharray="7 5"' if model == "scratch" else ""
                parts.append(f'<path d="{line}" fill="none" stroke="{color}" stroke-width="2.4"{dash}/>')
                for i, v in enumerate(values):
                    parts.append(f'<circle cx="{x(i):.3f}" cy="{y(v):.3f}" r="2.6" fill="{color}"/>')
    text(60, 945, "Figure 9 data from the anonymous manuscript. Identical IID probe test episodes; linear ridge probes.", 14, 'fill="#596764"')
    parts.append("</g></svg>")
    path.write_text("\n".join(parts) + "\n")


def export(args):
    truth = np.load(args.truth, allow_pickle=False)
    test = truth["split_iid"] == 2
    assert int(test.sum()) == 13710
    assert np.all(truth["valid"][test])
    variances = {
        tier: np.var(truth[label][test].astype(np.float64).reshape(test.sum(), -1), axis=0)
        for _, tier, label, _, _ in TARGETS
    }
    prior, scratch = {}, {}
    with args.prior_errors.open() as stream:
        for row in csv.DictReader(stream):
            if (row["split"] == "iid" and row["head"] == "linear"
                    and row["scope"] == "all" and row["col"] == "mean"
                    and row["tier"] in variances and row["arm"] in LAYERS):
                key = (budget(row["budget"]), row["tier"], row["arm"], int(row["seed"]))
                assert key not in prior
                prior[key] = float(row["rmse"])
    with args.scratch_summary.open() as stream:
        for row in csv.DictReader(stream):
            if (row["split"] == "iid" and row["head"] == "linear"
                    and row["tier"] in variances and row["arm"] in LAYERS):
                key = (budget(row["budget"]), row["tier"], row["arm"], int(row["seed"]))
                assert key not in scratch
                r2 = np.array(json.loads(row["r2_cols"]), dtype=np.float64)
                assert r2.shape == variances[row["tier"]].shape
                mse = (1 - r2) * variances[row["tier"]]
                assert np.all(mse >= 0)
                scratch[key] = float(np.sqrt(mse).mean())
    assert len(prior) == len(scratch) == 480

    document = pymupdf.open(args.paper)
    assert len(document) == 12 and "Figure 9:" in document[8].get_text()
    curves = [
        drawing for drawing in document[8].get_drawings()
        if 200 < drawing["rect"].y0 < 280 and drawing["rect"].width > 50
        and len(drawing["items"]) == 7
    ]
    assert len(curves) == 40
    data = {
        "source": "Manuscript Figure 9. Numerical probe results verified against the plotted curves.",
        "manuscript_sha256": sha256(args.paper),
        "units": "N",
        "metric": "Root mean squared error (RMSE); lower is better.",
        "aggregation": "Per-output RMSE averaged over outputs, then over three policy seeds.",
        "protocol": "Linear ridge probes; identical IID test episodes; 100,000 policy-training steps.",
        "budgets": BUDGETS,
        "layers": LAYERS,
        "policy_seeds": 3,
        "targets": {},
    }
    verification = {}
    for ti, (key, tier, _, name, description) in enumerate(TARGETS):
        target = {"name": name, "description": description, "series": {}}
        numeric_values, paper_y = [], []
        for bi, count in enumerate(BUDGETS):
            target["series"][str(count)] = {}
            for mi, (model, values) in enumerate([("prior", prior), ("scratch", scratch)]):
                samples = [[values[count, tier, layer, seed] for seed in SEEDS] for layer in LAYERS]
                means = np.mean(samples, axis=1)
                target["series"][str(count)][model] = {
                    "mean": [round(float(x), 8) for x in means],
                    "sd": [round(float(x), 8) for x in np.std(samples, axis=1, ddof=1)],
                }
                curve = curves[ti * 10 + bi * 2 + mi]
                assert all(item[0] == "l" for item in curve["items"])
                assert (curve["dashes"] == "[] 0") == (model == "prior")
                points = [item[1] for item in curve["items"]] + [curve["items"][-1][2]]
                assert all(points[i].x < points[i + 1].x for i in range(7))
                numeric_values.extend(means)
                paper_y.extend(point.y for point in points)
        # Each panel has its own linear y-axis. All 80 points must fit one transform.
        slope, intercept = np.polyfit(numeric_values, paper_y, 1)
        residual = float(np.max(np.abs(np.array(paper_y) - (slope * np.array(numeric_values) + intercept))))
        assert slope < 0 and residual < 0.001, (tier, residual)
        verification[key] = {"points": 80, "max_pdf_point_error": residual}
        data["targets"][key] = target
    document.close()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, indent=2) + "\n")
    vector_path = ROOT / "assets/images/contact.svg"
    vector_figure(data, vector_path)
    manifest_path = ROOT / "assets/manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["assets"][args.output.relative_to(ROOT / "assets").as_posix()] = {
        "source": data["source"],
        "sha256": sha256(args.output),
        "verified_points": 320,
    }
    manifest["assets"]["images/contact.svg"] = {
        "source": "Manuscript Figure 9, redrawn as a two-by-two vector layout from verified numerical data.",
        "width": 1360, "height": 960, "sha256": sha256(vector_path),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    report = {
        "source_hashes": {name: sha256(getattr(args, name))
                          for name in ("prior_errors", "scratch_summary", "truth", "paper")},
        "figure_comparison": verification,
    }
    (ROOT / "private").mkdir(exist_ok=True)
    (ROOT / "private/contact-data-verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Verified all 320 plotted values against Figure 9 and exported", args.output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prior-errors", type=Path, required=True)
    parser.add_argument("--scratch-summary", type=Path, required=True)
    parser.add_argument("--truth", type=Path, required=True)
    parser.add_argument("--paper", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "assets/data/contact-probes.json")
    export(parser.parse_args())
