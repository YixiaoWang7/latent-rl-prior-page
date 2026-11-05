#!/usr/bin/env python3
"""Check links, export boundaries, placeholders, and accidental private content. Stdlib only."""

import argparse
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


SITE_FILES = ("index.html", "styles.css", "site.js", "visuals.js", "robots.txt", ".nojekyll")
SVG_NAMESPACE = '"http://www.w3.org/2000/svg"'
# Outbound <a href> links may point only to these hosts (and their subdomains). Add a host here
# after checking the link. Images, videos, scripts, and styles must always be local files.
ALLOWED_LINK_HOSTS = ("arxiv.org", "github.com", "huggingface.co")
# Fill-in markers; the site cannot be packaged while any remain.
PLACEHOLDER = re.compile(r"TODO-[A-Z-]+")
FORBIDDEN = [
    r"/home/", r"/Users/", r"/opt/mt", r"s3://",
    r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}",
    r"\bAKIA[A-Z0-9]{16}\b",
    r"gh[pousr]_[A-Za-z0-9]{20,}",
]


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.links, self.errors = set(), [], []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        identifier = attrs.get("id")
        if identifier:
            if identifier in self.ids:
                self.errors.append(f"Duplicate HTML ID: {identifier}")
            self.ids.add(identifier)
        for key in ("src", "href", "poster"):
            if attrs.get(key):
                # Only <a href> is a navigation link; everything else is a loaded resource.
                self.links.append((attrs[key], tag == "a" and key == "href"))
        if tag == "img" and "alt" not in attrs:
            self.errors.append("Image missing alt text")
        if tag == "video" and "autoplay" in attrs:
            self.errors.append("Unexpected video autoplay")
        # The production CSP (script-src/style-src 'self') blocks all inline code and styles.
        if "style" in attrs:
            self.errors.append(f"Inline style attribute is blocked by the CSP: <{tag}>")
        if tag == "style" or (tag == "script" and not attrs.get("src")):
            self.errors.append(f"Inline <{tag}> is blocked by the CSP")
        if any(key.startswith("on") for key in attrs):
            self.errors.append(f"Inline event handler is blocked by the CSP: <{tag}>")


def validate(root):
    errors = []
    for name in SITE_FILES:
        if not (root / name).is_file():
            errors.append(f"Missing required file: {name}")
    if errors:
        return errors
    html = (root / "index.html").read_text(encoding="utf-8")
    page = Page()
    page.feed(html)
    errors.extend(page.errors)
    for marker in sorted(set(PLACEHOLDER.findall(html))):
        errors.append(f"Unfilled placeholder in index.html: {marker}")
    for link, navigation in page.links:
        parsed = urlsplit(link)
        if parsed.scheme or parsed.netloc:
            host = (parsed.hostname or "").lower()
            allowed = any(host == h or host.endswith("." + h) for h in ALLOWED_LINK_HOSTS)
            if not navigation:
                errors.append(f"External resource; the site must be self-contained: {link}")
            elif parsed.scheme != "https" or not allowed:
                errors.append(f"External link not in ALLOWED_LINK_HOSTS (or not https): {link}")
            continue
        path = unquote(parsed.path)
        if path:
            target = (root / path).resolve()
            if not target.is_relative_to(root.resolve()):
                errors.append(f"Link escapes the exported site: {link}")
            elif not target.is_file():
                errors.append(f"Broken link: {link}")
        if parsed.fragment and not path and parsed.fragment not in page.ids:
            errors.append(f"Broken anchor: {link}")

    # JS task switching and CSS resources are not necessarily present in HTML.
    for name in ("site.js", "visuals.js", "styles.css"):
        text = (root / name).read_text(encoding="utf-8")
        for local in re.findall(r"""[\"'](\./assets/[^\"']+)[\"']""", text):
            if not (root / local).is_file():
                errors.append(f"Missing scripted asset: {local}")
        # XML namespace identifiers are never fetched, so they are not remote dependencies.
        if re.search(r"https?://|@import\b", text.replace(SVG_NAMESPACE, "")):
            errors.append(f"Remote dependency in {name}")

    files = [root / name for name in SITE_FILES]
    files += list((root / "assets").rglob("*"))
    for path in files:
        if path.is_symlink():
            errors.append(f"Symlink in site: {path.relative_to(root)}")
        if not path.is_file():
            continue
        if path.stat().st_size > 50 * 1024 * 1024:
            errors.append(f"Asset exceeds the 50 MiB site budget: {path.name}")
        if path.suffix in (".html", ".css", ".js", ".json", ".svg", ".txt"):
            text = path.read_text(encoding="utf-8")
            for pattern in FORBIDDEN:
                if re.search(pattern, text, re.IGNORECASE):
                    errors.append(f"Possible local path, email, or token in {path.relative_to(root)}")
                    break
    manifest_path = root / "assets" / "manifest.json"
    if not manifest_path.exists():
        errors.append("Missing asset provenance manifest")
    else:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        import hashlib
        for name, asset in manifest["assets"].items():
            target = root / "assets" / name
            if not target.is_file():
                errors.append(f"Missing manifest asset: {name}")
            elif hashlib.sha256(target.read_bytes()).hexdigest() != asset["sha256"]:
                errors.append(f"Asset differs from its provenance manifest: {name}")
        data_path = root / "assets/data/contact-probes.json"
        if data_path.exists():
            contact_data = json.loads(data_path.read_text(encoding="utf-8"))
            if contact_data.get("manuscript_sha256") != manifest["assets"]["paper.pdf"]["sha256"]:
                errors.append("Contact chart data was not verified against this manuscript PDF")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path,
                        default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    errors = validate(args.root)
    if errors:
        print("\n".join(f"ERROR: {x}" for x in errors))
        sys.exit(1)
    print("PASS: local links, assets, provenance hashes, placeholders, and private-content checks.")
    print("Still review the visible page, the PDF, and every outbound link before publishing.")


if __name__ == "__main__":
    main()
