# Latent RL Priors for Data-Efficient Dexterous Manipulation

Public project page for the arXiv paper. The website is plain HTML, CSS, and JavaScript, with all
figures, videos, and the PDF stored locally; it has no build step, runtime dependencies, remote fonts,
or analytics. Outbound links are limited to the hosts in `ALLOWED_LINK_HOSTS` in
`scripts/validate_site.py`.

**Pending until the arXiv version exists:** the author line (a commented template sits in the title
block of `index.html`), the arXiv button (currently a grey “coming soon” pill), the arXiv BibTeX entry,
and the PDF button. `assets/paper.pdf` is the anonymous review version; it stays in the repository
because the contact-chart data is verified against it, but the page does not link it. To add the arXiv
PDF, see “Replacing the PDF”. If you mark something as unfinished with a `TODO-NAME` marker, validation
and deployment fail until it is resolved. The anonymous review version of the page is kept,
unpublished, in `.local-backups/2026-11-05-anonymous-version/`.

The page follows a standard academic project-page layout: a title block with paper links, a sticky
section navigation, and numbered sections (Overview with key numbers, abstract, and contributions;
Method; Experimental Setup with task videos and the dataset table; Main Results; Analysis A1–A4 with
the interactive contact-force chart; Limitations; Resources; Citation). Every paper figure is shown at
full width with its manuscript caption, and each finding ends with a one-line takeaway. The code and
dataset cards say **planned release** because no public release URL has been provided.

## Preview

Serve the site locally to use every interactive chart:

```bash
python3 -m http.server 8000 --bind 127.0.0.1
```

Open `http://127.0.0.1:8000`. For a remote machine, forward this port through SSH.
Do not change the server to an all-interfaces bind.
Opening `index.html` directly still shows the static figures; the force-data request needs HTTP.

## Validate and package

Python 3.11+ is sufficient; no packages need to be installed.

```bash
python3 scripts/validate_site.py
python3 scripts/package_site.py --zip dist/latent-rl-prior-site.zip
```

`dist/site/` and the ZIP contain only the publishable page and assets. They do not include Git
history, the build scripts, deployment configuration, documentation, local notes, or screenshots.
Asset hashes are checked against `assets/manifest.json` before packaging.
See [validation notes](docs/validation.md) for the completed browser, metadata, and template checks.

With Playwright (`pip install playwright` in a temporary environment) and Chrome installed, run the
browser checks after packaging:

```bash
python scripts/check_browser.py            # add --chrome /path/to/chrome if it is not auto-detected
```

This starts a temporary loopback preview of the export with the production CSP. It checks the
contact-chart readouts, keyboard controls, section navigation, videos, static fallbacks, and, at
widths from 320 to 1440 pixels, page overflow, a 12.5-pixel minimum font size, and a shared left
edge for all section headings.

## Publish

The public page is published with GitHub Pages: `.github/workflows/pages.yml` validates, packages,
and deploys `dist/site` on every push to `main` (or when run manually from the Actions tab). See
[the hosting guide](docs/hosting.md) for first-time setup. The guide also covers the anonymous
review options (Anonymous GitHub and CloudFront), which must only ever serve the anonymous snapshot.

## Content and media provenance

Figures were extracted from the supplied 12-page review manuscript. The manuscript, rather than an
older source checkout, is the source for the site's experimental numbers and protocol.
[Content notes](docs/content.md) map claims to the paper and method descriptions to implementation
modules.

The videos replay **collected demonstration trajectories**. They illustrate the tasks and are not
presented as closed-loop evaluations of the adapted policy. Source timing is preserved. The small
recording annotation at the top of the door and assembly videos is cropped out, and the videos are
padded to a square without changing their aspect ratio.

The PDF's visible content is unchanged; document metadata and embedded-file attachments are removed.
Images are re-encoded without EXIF metadata, and videos are encoded without source metadata.
`assets/manifest.json` records provenance, image sizes, video durations, and SHA-256 hashes.

To re-import media, install PyMuPDF and Pillow in a temporary environment and ensure `ffmpeg` and
`ffprobe` are available:

```bash
python scripts/import_assets.py \
  --paper /path/to/review-manuscript.pdf \
  --pose-video /path/to/pose-demonstration.mp4 \
  --door-video /path/to/door-demonstration.mp4 \
  --assembly-video /path/to/assembly-demonstration.mp4
```

The importer uses figure locations in the supplied draft. Inspect and update those locations for a
new paper revision, then update any image dimensions in `index.html`, review the outputs, and
repackage.

The force explorer and downloadable SVG use numerical probe results, not pixel estimates.
To regenerate them, install NumPy and PyMuPDF and provide the original probe files:

```bash
python scripts/export_contact_data.py \
  --prior-errors /path/to/prior-errors.csv \
  --scratch-summary /path/to/scratch-summary.csv \
  --truth /path/to/probe-truth.npz \
  --paper assets/paper.pdf
```

The exporter verifies all 320 curve values against Figure 9 before writing the JSON
and SVG. Source hashes and residuals stay in ignored `private/` notes. Re-run this verification
after re-importing the manuscript; packaging rejects chart data tied to a different PDF.

## Replacing the PDF

`assets/manifest.json` stores a SHA-256 hash for every asset, and `assets/data/contact-probes.json`
records the hash of the PDF that its Figure 9 values were checked against. After copying the arXiv
PDF to `assets/paper.pdf`, re-run `scripts/export_contact_data.py` (which needs the original probe
files), or verify that Figure 9 is unchanged. Then update both hashes, run `scripts/validate_site.py`,
and repackage.

Do not upload this public version to the anonymous review deployments (Anonymous GitHub or the
CloudFront stack), because a link to those may appear in the review submission.

## Layout and typography rules

- All text uses the type scale defined at the top of `styles.css` (`--fs-xs` 12.5 px up to `--fs-h1`).
  Do not add one-off font sizes; nothing visible may be smaller than 12.5 px.
- Every block aligns to the `.container` edge. Only the title block is centered.
- Each section is `<section class="container page-section">` with a numbered `.section-heading`.
  Analysis findings use `.finding` blocks: question, figure with the manuscript caption, short
  findings, and a `.takeaway` line.
- “Ours” is orange and π<sub>0.5</sub> blue, matching the manuscript figures.
- The production CSP forbids inline styles and scripts; `validate_site.py` rejects them.

## Files

```text
index.html                 Page content
styles.css                 Responsive layout and print/reduced-motion styles
site.js                    Task selection, section navigation, figure dialogs, citation copying
visuals.js                 Contact-force explorer (Figure 9 data)
assets/                    Self-contained paper, figures, videos, provenance
scripts/                   Asset import, validation, and export
docs/                      Hosting and content notes
deployment/cloudfront.yml  Optional private-origin CloudFront configuration
.github/workflows/         Manual GitHub Pages publication
```
