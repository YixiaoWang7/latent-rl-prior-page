# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

The **public project page** for the arXiv paper *Latent RL Priors for Data-Efficient Dexterous
Manipulation*. It is plain HTML/CSS/JS with no build step, no runtime dependencies, and every asset
(figures, videos, PDF, chart data) stored locally. It is published with GitHub Pages.

Authors and affiliations come from the preprint title block in the paper's LaTeX source. Still pending
until the arXiv version exists: the arXiv link (a `.link-pending` pill), the arXiv BibTeX, and a PDF link
(`assets/paper.pdf` is the anonymous review PDF, kept only for chart-data provenance and not linked). Fill these only from information the user
provides; never invent author names, affiliations, or IDs. Any `TODO-NAME` marker in `index.html` fails
validation and blocks deployment. The anonymous review version is kept unpublished in
`.local-backups/2026-11-05-anonymous-version/`; never deploy the public page to the anonymous hosts
(Anonymous GitHub, CloudFront).

## Commands

Python 3.11+ stdlib only for preview, validation, and packaging; nothing to install.

```bash
# Preview. Must bind loopback only; never bind all interfaces.
python3 -m http.server 8000 --bind 127.0.0.1

# Static checks: links, anchors, alt text, provenance hashes, placeholders, private-content patterns
python3 scripts/validate_site.py            # optionally pass a root dir, e.g. dist/site

# Validate and export the publishable allowlist to dist/site (and optional ZIP)
python3 scripts/package_site.py --zip dist/latent-rl-prior-site.zip

# Browser checks against dist/site under the production CSP (needs Playwright, e.g. in a
# throwaway venv; run package_site.py first). --url checks a live deployment; --chrome picks a binary.
python scripts/check_browser.py
```

`check_browser.py` auto-detects Chrome on Linux and macOS. Screenshots and the JSON report go to `dist/`.

Build-time-only regeneration scripts (need PyMuPDF/Pillow/ffmpeg or NumPy/PyMuPDF and private
source files; see README for full arguments): `scripts/import_assets.py` (figures, PDF, videos from a
manuscript revision) and `scripts/export_contact_data.py` (Figure 9 force-probe data + vector SVG).

## Architecture

**Publish allowlist.** `SITE_FILES` in `scripts/validate_site.py` (`index.html`, `styles.css`,
`site.js`, `visuals.js`, `robots.txt`, `.nojekyll`) plus `assets/` is the only content that is exported.
`package_site.py` imports that tuple, validates the source, copies, then re-validates the export.
A new top-level site file must be added to `SITE_FILES`, or it will not ship.

**Provenance manifest is enforced.** `assets/manifest.json` stores a SHA-256 for every asset.
Validation fails if any asset's bytes change without the manifest being updated. Also,
`assets/data/contact-probes.json` → `manuscript_sha256` must equal the manifest's `paper.pdf` hash,
which ties chart data to the exact PDF. The import and export scripts rewrite the manifest. When an
asset is edited by hand, its manifest hash must be updated.

**Validator-enforced rules** (`validate_site.py`):
- every `src`/`poster` and non-`<a>` `href` must be a local file inside the site. `<a href>` may also be
  an https link to a host in `ALLOWED_LINK_HOSTS` (arxiv.org, github.com, huggingface.co); add hosts there.
- no `TODO-…` placeholder may remain in `index.html`.
- `site.js`, `visuals.js`, and `styles.css` must not contain `http(s)://` (except the SVG namespace
  string) or `@import`. `./assets/...` strings in them must resolve.
- images need `alt`; videos must not `autoplay`; no duplicate IDs, symlinks, or files over 50 MiB.
- text assets are scanned for `/Users/`, `/home/`, `s3://`, email addresses, and AWS/GitHub tokens.

**Strict CSP.** `default-src 'self'` with `script-src 'self'` and `style-src 'self'` and no
`unsafe-inline`, so inline `<script>`, `<style>`, `style="..."` attributes, and `on*=` handlers are blocked
in production; `validate_site.py` rejects them. The policy is duplicated in `deployment/cloudfront.yml`
and `scripts/check_browser.py`. Keep both copies in sync.

**Page structure.** Standard academic project-page layout (Nerfies-style): centered
title block with pill links, sticky `.section-nav`, then numbered `<section class="container page-section">`
blocks (Overview, Method, Setup, Results, Analysis A1–A4, Limitations, Resources, Citation). Analysis
findings are `.finding` blocks: question → figure with the manuscript caption → short findings →
`.takeaway`. Everything except the hero aligns to the `.container` edge.

**Type scale.** All font sizes come from the `--fs-*` variables at the top of `styles.css`, with a
12.5 px floor. `check_browser.py` fails if any visible text is smaller or if section headings do
not share one left edge. Do not add ad-hoc sizes. SVG chart labels are sized in viewBox units, and the
≤760 px rule enlarges them so they still render at 12.5 px or more. "Ours" is orange (`--ours`) and
π0.5 is blue (`--baseline`), matching the paper's figures; `visuals.js` repeats these hex values.

**Progressive enhancement.** `#contact-explorer` ships `hidden` and `#contact-fallback` (vector SVG of
Figure 9) is visible by default; JS swaps them only after `contact-probes.json` loads and validates.
Everything else is static HTML, so the page is complete with JS disabled. It also works from `file://`,
where only the force-data fetch fails.

**JS split.** `site.js`: task tabs/video swapping (task metadata lives in its `tasks` object),
section-nav `aria-current` tracking, figure zoom `<dialog>`, BibTeX copy (`#citation-text`).
`visuals.js`: the contact-force explorer only (per-target y-axis `domains` are hardcoded). Earlier
versions with a method walkthrough and budget-bar widget are in `.local-backups/` (gitignored).

**`check_browser.py` asserts exact UI details**, including element IDs, SVG viewBoxes (`0 0 440 350` /
`0 0 790 390`), 720 px video width, and the door clip duration (6.166667 s). Update it when
changing these.

## Content rules

- The manuscript (`assets/paper.pdf`) is the sole source of truth for numbers and claims.
  `docs/content.md` maps each site claim to a section or figure. Never estimate values from pixels or
  synthesize curves.
- Videos are replays of **collected demonstration trajectories**, not closed-loop policy evaluations.
  Wording must not imply otherwise.
- Code/dataset cards stay "planned release" until real URLs are provided.
- `private/` (exporter verification reports) and `dist/` are gitignored and must never be published.
- Replacing `assets/paper.pdf` requires updating its hash in `assets/manifest.json` and re-verifying
  `contact-probes.json` → `manuscript_sha256` against the new PDF (see README, "Replacing the PDF").

## Deployment

`.github/workflows/pages.yml` validates, packages, and deploys `dist/site` to GitHub Pages on every push
to `main`, so pushing to `main` publishes the page. `deployment/cloudfront.yml` is for the anonymous
snapshot only. Details are in `docs/hosting.md`. Do not push, deploy, or run AWS commands unless explicitly
asked.
