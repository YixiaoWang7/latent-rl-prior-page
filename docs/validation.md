# Validation of the prepared site

The prepared version was checked locally in Chromium using Playwright.

- All referenced images, scripts, styles, video files, and the PDF resolve.
- The site works from a domain root and a simulated `/r/review/index.html` subpath.
- All three H.264 videos decode and play at 720 × 720.
- Task tabs work with mouse and arrow/Home/End keys.
- Figure dialogs open, close with Escape or the close button, and return keyboard focus.
- The temporary BibTeX entry copies to the clipboard.
- Figures inside disclosures open correctly.
- No horizontal page overflow at viewport widths of 320, 375, 390, 768, 1024, and 1440 pixels.
- No browser JavaScript errors, HTTP failures, or external runtime requests were observed.
- The page works under the content-security policy in the CloudFront template.
- Core content and direct video links remain available with JavaScript disabled.
- All 12 pages of the sanitized PDF rendered identically to the supplied original in the comparison.
- PDF author/creator/producer/date metadata and embedded attachments are absent.
- Exported images have no EXIF metadata; videos have no source title, author, comment, or creation date.
- Static validation checks provenance hashes, missing files, path escapes, and common identity leaks.
- The CloudFormation template passes `cfn-lint`.

The initial CloudFront publication was also checked anonymously: all exported files matched the
local bytes, videos supported range requests, HTTP redirected to HTTPS, and the direct private
S3 origin denied anonymous access.

## Interactive revision

The 2026-10-15 revision adds a reproducible Chromium check in `scripts/check_browser.py`.
It verifies all force targets and budgets through 120 numeric readout assertions; method-stage
keyboard controls and the walkthrough timer; both budget comparisons; all three video decoders;
layouts from 320 to 1440 pixels; reduced motion; and readable fallbacks when JavaScript is disabled
or the chart-data request fails. The checks run under the production CSP with no external requests.

All 320 contact-curve values are independently checked against the manuscript's vector paths.
The replacement door clip retains its original timing and is 6.166667 seconds long.

Screenshots and detailed machine-readable reports are generated locally under `dist/`, which is
excluded from Git and from the published site. Pass `--url` to the browser check to verify a live
deployment.

## Academic redesign (2026-11-05)

The page was restructured as a standard academic project page: title block with paper links, sticky section navigation, numbered sections, key-number cards,
the full abstract and contributions, full-width figures with manuscript captions, and one takeaway
per finding.

- The formal manuscript supplied for this revision renders identically on all 12 pages to the
  sanitized `assets/paper.pdf` (pixel comparison), so the PDF, figures, and chart data were kept.
- Every stated number was rechecked against the manuscript text, and the contact-probe summary
  against `assets/data/contact-probes.json`.
- `scripts/check_browser.py` passed in Chrome with the production CSP: 120 contact readouts, all
  three videos, keyboard task tabs, section navigation, static and fetch-failure fallbacks, and,
  at 320, 390, 768, 1024, and 1440 pixels, no overflow, no text below 12.5 px, and one shared left
  edge for all section headings. No console errors or external requests were observed.
- `scripts/validate_site.py` now also rejects inline styles, inline scripts, and inline event
  handlers, which the CSP would block.
