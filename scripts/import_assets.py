#!/usr/bin/env python3
"""Import the supplied review manuscript and three demonstration replays.

Requires PyMuPDF, Pillow, ffmpeg, and ffprobe. These are build-time tools only.
The figure locations below refer to the 12-page review draft used for this site.
Review them when replacing the manuscript; they are not a general PDF extractor.
Source filenames and absolute paths are deliberately not written to the site.
"""

import argparse
import hashlib
import io
import json
import subprocess
from pathlib import Path

import pymupdf
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
TITLE = "Latent RL Priors for Data-Efficient Dexterous Manipulation"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def flatten_on_white(image):
    """Composite any transparency onto white, as the figure appears on the PDF page.

    A plain RGB conversion would expose the colour stored under transparent pixels,
    which is usually black.
    """
    if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
        image = image.convert("RGBA")
        background = Image.new("RGB", image.size, "white")
        background.paste(image, mask=image.getchannel("A"))
        return background
    return image.convert("RGB")


def embedded_figure(document, page_number):
    """Return the largest raster image on a page, with its soft mask applied as alpha."""
    page = document[page_number - 1]
    info = max(page.get_image_info(xrefs=True), key=lambda x: x["width"] * x["height"])
    xref = info["xref"]
    image = Image.open(io.BytesIO(document.extract_image(xref)["image"]))
    # PDF stores transparency in a separate soft-mask image; extract_image() omits it.
    smask = next((item[1] for item in page.get_images(full=True) if item[0] == xref), 0)
    if smask:
        alpha = Image.open(io.BytesIO(document.extract_image(smask)["image"])).convert("L")
        image = image.convert("RGB")
        image.putalpha(alpha.resize(image.size))
    return image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paper", type=Path, required=True)
    parser.add_argument("--pose-video", type=Path, required=True)
    parser.add_argument("--door-video", type=Path, required=True)
    parser.add_argument("--assembly-video", type=Path, required=True)
    args = parser.parse_args()
    assets = ROOT / "assets"
    images = assets / "images"
    videos = assets / "videos"
    images.mkdir(parents=True, exist_ok=True)
    videos.mkdir(parents=True, exist_ok=True)
    document = pymupdf.open(args.paper)
    if len(document) != 12:
        raise ValueError("Expected the supplied 12-page review draft. Check figure locations.")
    for page, marker in [(2, "Figure 1:"), (5, "Figure 4:"), (6, "Figure 5:"),
                         (7, "Figure 7:"), (8, "Figure 9:")]:
        if marker not in document[page].get_text():
            raise ValueError(f"Expected {marker} on page {page + 1}; check figure locations.")
    manifest = {
        "manuscript": {
            "title": TITLE,
            "source_sha256": digest(args.paper),
            "pages": len(document),
            "status": "Anonymous review manuscript",
        },
        "assets": {},
    }
    # Keep derived figures registered; validation requires them to be reverified
    # whenever the manuscript changes.
    old_manifest = assets / "manifest.json"
    if old_manifest.exists():
        previous = json.loads(old_manifest.read_text()).get("assets", {})
        for name in ("data/contact-probes.json", "images/contact.svg"):
            if name in previous:
                manifest["assets"][name] = previous[name]

    def save_image(image, name, width, source):
        image = flatten_on_white(image)
        if image.width > width:
            image = image.resize((width, round(image.height * width / image.width)),
                                 Image.Resampling.LANCZOS)
        target = images / f"{name}.webp"
        image.save(target, "WEBP", lossless=True, method=6)
        manifest["assets"][f"images/{name}.webp"] = {
            "source": source, "width": image.width, "height": image.height,
            "sha256": digest(target),
        }
        print(name, image.size, target.stat().st_size)

    # Extract the embedded raster figures from the manuscript, not older source plots.
    for name, page_number, width, figure in [
        ("method", 3, 2400, 1),
        ("tasks", 5, 3200, 2),
        ("results", 6, 3200, 4),
        ("interface", 7, 2000, 5),
    ]:
        save_image(embedded_figure(document, page_number), name, width,
                   f"Manuscript Figure {figure}, page {page_number}; embedded image.")

    # Render vector figures at publication quality, with no captions or line numbers.
    for name, page_number, rect, width, figure in [
        ("adaptation", 8, (107, 81, 505, 179), 2400, 7),
        ("mass", 8, (304, 460, 505, 544), 1800, 8),
        ("contact", 9, (107, 202, 505, 291), 2400, 9),
        ("stability", 7, (107, 467, 505, 556), 2800, 6),
    ]:
        clip = pymupdf.Rect(rect)
        pix = document[page_number - 1].get_pixmap(
            matrix=pymupdf.Matrix(width / clip.width, width / clip.width),
            clip=clip, alpha=False)
        image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        save_image(image, name, width,
                   f"Manuscript Figure {figure}, page {page_number}; rendered vector crop.")

    # Visible manuscript content is unchanged. Remove identifying document metadata.
    document.set_metadata({"title": TITLE, "author": "", "subject": "",
                           "keywords": "", "creator": "", "producer": "",
                           "creationDate": "", "modDate": ""})
    document.del_xml_metadata()
    for name in document.embfile_names():
        document.embfile_del(name)
    target_pdf = assets / "paper.pdf"
    if target_pdf.exists():
        target_pdf.unlink()
    document.save(target_pdf, garbage=4, deflate=True, clean=True)
    document.close()
    manifest["assets"]["paper.pdf"] = {
        "source": "Supplied anonymous manuscript; document metadata removed.",
        "sha256": digest(target_pdf),
    }

    # All clips retain the source timing. Crop only the small recording annotation
    # at the top of the door/assembly frames, then preserve aspect ratio with padding.
    for task, source, crop_top, poster_time in [
        ("pose", args.pose_video, 0, 5),
        ("door", args.door_video, 40, 10 / 3),
        ("assembly", args.assembly_video, 40, 5),
    ]:
        target = videos / f"{task}.mp4"
        filters = []
        if crop_top:
            filters.append(f"crop=iw:ih-{crop_top}:0:{crop_top}")
        filters += ["scale=720:720:force_original_aspect_ratio=decrease",
                    "pad=720:720:(ow-iw)/2:(oh-ih)/2:color=0xe7ecf3", "setsar=1"]
        subprocess.run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-i", str(source), "-map", "0:v:0", "-an",
            "-vf", ",".join(filters), "-c:v", "libx264",
            "-crf", "18" if task == "door" else "23", "-preset", "medium", "-pix_fmt", "yuv420p",
            "-map_metadata", "-1", "-map_chapters", "-1",
            "-movflags", "+faststart", str(target),
        ], check=True)
        result = subprocess.run([
            "ffmpeg", "-hide_banner", "-loglevel", "error",
            "-ss", str(poster_time), "-i", str(target), "-frames:v", "1",
            "-f", "image2pipe", "-vcodec", "png", "-",
        ], check=True, stdout=subprocess.PIPE)
        save_image(Image.open(io.BytesIO(result.stdout)), f"{task}-poster", 720,
                   f"Frame at {poster_time} s of {task}.mp4.")
        probe = subprocess.run([
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "json", str(target),
        ], check=True, capture_output=True, text=True)
        manifest["assets"][f"videos/{task}.mp4"] = {
            "source": "MuJoCo replay of a collected demonstration trajectory.",
            "role": "Task illustration; not an evaluated adapted-policy rollout.",
            "source_sha256": digest(source),
            "sha256": digest(target),
            "duration_seconds": float(json.loads(probe.stdout)["format"]["duration"]),
            "processing": f"Source timing retained; top {crop_top} pixels cropped; "
                          "aspect-preserving padding to 720x720; metadata removed.",
        }
        print(task, "video", target.stat().st_size)

    (assets / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
