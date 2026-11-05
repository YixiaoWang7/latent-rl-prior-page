#!/usr/bin/env python3
"""Check the exported site's interactions, layout, and typography in Chrome.

Requires Playwright (pip install playwright) and a local Chrome or Chromium; pass
--chrome to choose a binary. The temporary preview binds only to loopback and uses
the production CSP. Reports and screenshots stay in the ignored dist folder.
Pass --url to repeat the checks against an already deployed website.
"""

import argparse
import functools
import json
import shutil
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright, expect


ROOT = Path(__file__).resolve().parents[1]
CSP = ("default-src 'self'; script-src 'self'; style-src 'self'; "
       "img-src 'self' data:; media-src 'self'; connect-src 'self'; object-src 'none'; "
       "base-uri 'self'; form-action 'none'; frame-ancestors 'none'")
CHROME_CANDIDATES = [
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
]
MIN_FONT_PX = 12.5
WIDTHS = [320, 390, 768, 1024, 1440]

# Visible text elements must use the shared type scale; none may be smaller than MIN_FONT_PX.
TYPOGRAPHY_JS = """() => {
  const sizes = new Set(), small = [];
  for (const el of document.querySelectorAll('body *')) {
    const own = [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim());
    if (!own || el.closest('svg, dialog, [hidden]')) continue;
    const r = el.getBoundingClientRect();
    const cs = getComputedStyle(el);
    if (!r.width || !r.height || cs.visibility === 'hidden') continue;
    const px = parseFloat(cs.fontSize);
    sizes.add(px);
    // <sub>/<sup> are scaled relative to their surrounding text.
    if (px < 12.5 && !['SUB', 'SUP'].includes(el.tagName)) small.push(`${el.tagName} ${px}px: ${el.textContent.trim().slice(0, 40)}`);
  }
  const lefts = [...document.querySelectorAll('.section-heading')].map(h => Math.round(h.getBoundingClientRect().left));
  return {sizes: [...sizes].sort((a, b) => a - b), small, headingLefts: [...new Set(lefts)]};
}"""


class PreviewServer(ThreadingHTTPServer):
    # The default listen backlog (5) can reset connections when the page loads many assets at once.
    request_queue_size = 128


class Preview(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Content-Security-Policy", CSP)
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()

    def log_message(self, *_):
        pass


def find_chrome(explicit):
    if explicit:
        return explicit
    for candidate in CHROME_CANDIDATES:
        if Path(candidate).exists():
            return candidate
    for name in ("google-chrome", "chromium", "chromium-browser"):
        if shutil.which(name):
            return shutil.which(name)
    raise SystemExit("Chrome not found; pass --chrome /path/to/chrome")


def check(url, prefix, chrome):
    source = json.loads((ROOT / "assets/data/contact-probes.json").read_text())
    errors, external = [], set()
    (ROOT / "dist").mkdir(exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=chrome, headless=True, args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 1440, "height": 1050})
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
        page.on("request", lambda request: external.add(request.url) if not request.url.startswith(url) else None)
        response = page.goto(url, wait_until="networkidle")
        assert response.status == 200
        expect(page.locator("#contact-explorer")).to_be_visible()
        expect(page.locator("#contact-fallback")).to_be_hidden()
        expect(page.locator("#method-figure img")).to_be_visible()

        # The section navigation follows the scroll position.
        page.locator('.nav-links a[href="#analysis"]').click()
        # Smooth scrolling takes a moment; wait for it to settle on the target.
        expect(page.locator('.nav-links a[href="#analysis"]')).to_have_attribute("aria-current", "location", timeout=5000)
        page.evaluate("window.scrollTo({top: document.body.scrollHeight, behavior: 'instant'})")
        expect(page.locator('.nav-links a[href="#citation"]')).to_have_attribute("aria-current", "location", timeout=5000)

        # Every target and budget; inspect early, middle, and final decoder layers.
        values_checked = 0
        for key, target in source["targets"].items():
            page.locator(f'[data-force="{key}"]').click()
            for index, budget in enumerate(source["budgets"]):
                page.locator("#force-budget").evaluate(
                    "(input, value) => {input.value = value; input.dispatchEvent(new Event('input', {bubbles: true}));}",
                    str(index))
                assert page.locator("#force-budget").get_attribute("aria-valuetext") == f"{budget:,} demonstrations"
                for layer in [0, 3, 7]:
                    page.locator("#layer-buttons button").nth(layer).click()
                    for model in ["prior", "scratch"]:
                        value = target["series"][str(budget)][model]["mean"][layer]
                        expect(page.locator(f"#force-{model}-value")).to_have_text(f"{value:.2f}")
                        values_checked += 1
        page.locator("#layer-buttons button").nth(7).focus()
        page.keyboard.press("ArrowRight")
        assert page.locator("#force-layer-name").inner_text() == "Layer 1"
        page.locator('[data-force="grasp"]').click()
        page.locator("#force-budget").evaluate(
            "(input) => {input.value = 0; input.dispatchEvent(new Event('input', {bubbles: true}));}")
        page.locator("#layer-buttons button").nth(3).click()

        # Task tabs work from the keyboard and from the teaser links.
        page.locator("#tab-pose").focus()
        page.keyboard.press("ArrowRight")
        assert page.locator("#tab-door").get_attribute("aria-selected") == "true"
        page.locator('[data-select-task="assembly"]').click()
        assert page.locator("#tab-assembly").get_attribute("aria-selected") == "true"
        expect(page.locator("#task-name")).to_have_text("Bimanual assembly")

        # The source figure is truly vector and all demonstration videos decode.
        svg = page.request.get(url + "assets/images/contact.svg")
        assert svg.status == 200 and "<svg" in svg.text() and "<image" not in svg.text()
        played = []
        for task in ["pose", "door", "assembly"]:
            page.locator("#tab-" + task).click()
            page.evaluate("document.getElementById('task-video').play()")
            deadline = time.monotonic() + 25
            while time.monotonic() < deadline:
                state = page.evaluate("""(() => {
                    const v = document.getElementById('task-video');
                    return {time: v.currentTime, width: v.videoWidth, error: v.error?.message || null, duration: v.duration};
                })()""")
                if state["time"] > .15:
                    break
                page.wait_for_timeout(100)
            assert state["time"] > .15 and state["width"] == 720 and state["error"] is None, state
            if task == "door":
                assert abs(state["duration"] - 6.166667) < .02
            played.append(task)
            page.evaluate("document.getElementById('task-video').pause()")

        # Responsive layouts: no page overflow, readable type, aligned section headings,
        # and the chart re-renders axes instead of shrinking desktop labels.
        layouts, font_sizes = [], {}
        for width in WIDTHS:
            page.set_viewport_size({"width": width, "height": 1000})
            page.wait_for_timeout(150)
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), f"Overflow at {width}"
            viewbox = page.locator("#contact-chart svg").get_attribute("viewBox")
            assert viewbox == ("0 0 440 350" if width <= 760 else "0 0 790 390"), (width, viewbox)
            typography = page.evaluate(TYPOGRAPHY_JS)
            assert not typography["small"], (width, typography["small"][:5])
            assert len(typography["headingLefts"]) == 1, (width, typography["headingLefts"])
            font_sizes[width] = typography["sizes"]
            layouts.append(width)
        page.set_viewport_size({"width": 1440, "height": 1050})
        page.locator("#contact-explorer").screenshot(path=str(ROOT / f"dist/{prefix}-contact-desktop.png"))
        page.screenshot(path=str(ROOT / f"dist/{prefix}-page-desktop.png"), full_page=True)
        page.set_viewport_size({"width": 390, "height": 844})
        page.locator("#contact-explorer").screenshot(path=str(ROOT / f"dist/{prefix}-contact-mobile.png"))
        page.screenshot(path=str(ROOT / f"dist/{prefix}-page-mobile.png"), full_page=True)

        # A failed data request must retain an independently readable scientific figure.
        fallback = browser.new_page()
        fallback.route("**/assets/data/contact-probes.json", lambda route: route.abort())
        fallback.goto(url, wait_until="networkidle")
        expect(fallback.locator("#contact-fallback")).to_be_visible()
        assert fallback.locator("#contact-explorer").is_hidden()
        fallback.close()
        context = browser.new_context(java_script_enabled=False)
        static = context.new_page()
        static.goto(url)
        expect(static.locator("#contact-fallback")).to_be_visible()
        expect(static.locator("#method-figure img")).to_be_visible()
        expect(static.locator("#results .result-grid")).to_be_visible()
        assert not errors, errors
        assert not external, sorted(external)
        browser.close()
    report = {"url": url, "numeric_readouts_checked": values_checked, "videos": played,
              "widths": layouts, "font_sizes_px": font_sizes, "min_font_px": MIN_FONT_PX,
              "keyboard": True, "section_navigation": True,
              "static_and_fetch_failure_fallbacks": True,
              "browser_errors": errors, "external_requests": sorted(external)}
    (ROOT / f"dist/{prefix}-browser-validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url")
    parser.add_argument("--prefix", default="revision")
    parser.add_argument("--chrome", help="Chrome or Chromium executable (auto-detected by default)")
    args = parser.parse_args()
    server = None
    if not args.url:
        handler = functools.partial(Preview, directory=str(ROOT / "dist/site"))
        server = PreviewServer(("127.0.0.1", 0), handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        args.url = f"http://127.0.0.1:{server.server_port}/"
    try:
        check(args.url, args.prefix, find_chrome(args.chrome))
    finally:
        if server:
            server.shutdown()
            server.server_close()
