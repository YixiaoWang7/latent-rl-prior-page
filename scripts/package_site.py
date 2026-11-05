#!/usr/bin/env python3
"""Create a host-neutral, allowlisted static-site directory and optional ZIP."""

import argparse
import shutil
import sys
import zipfile
from pathlib import Path

from validate_site import SITE_FILES, validate


ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist" / "site")
    parser.add_argument("--zip", dest="zip_path", type=Path)
    args = parser.parse_args()
    errors = validate(ROOT)
    if errors:
        sys.exit("\n".join(errors))
    output = args.output.resolve()
    # Export directories must never replace source files or a parent of the repo.
    if output == ROOT or ROOT.is_relative_to(output):
        sys.exit("Export output must not be the repository root or its parent.")
    if output.exists() and any(output.iterdir()):
        if not (output / ".site-export").is_file():
            sys.exit("Refusing to replace a nonempty directory without a .site-export marker.")
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)
    for name in SITE_FILES:
        shutil.copy2(ROOT / name, output / name)
    shutil.copytree(ROOT / "assets", output / "assets")
    (output / ".site-export").write_text("Generated static-site export.\n", encoding="utf-8")
    errors = validate(output)
    if errors:
        sys.exit("\n".join(errors))
    paths = [p for p in output.rglob("*") if p.is_file()]
    if args.zip_path:
        archive = args.zip_path.resolve()
        if archive.is_relative_to(output):
            sys.exit("Put the ZIP outside the exported directory.")
        archive.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
            for path in sorted(paths):
                if path.name != ".site-export":
                    bundle.write(path, path.relative_to(output))
        print(f"ZIP: {archive}")
    total = sum(p.stat().st_size for p in paths)
    print(f"Exported {len(paths)} files ({total / 1024 / 1024:.1f} MiB) to {output}")


if __name__ == "__main__":
    main()
