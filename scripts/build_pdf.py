"""Render the built site's print page to a single course PDF.

Run after `mkdocs build`:

    python scripts/build_pdf.py

Serves site/ locally, opens /print_page/ (made by mkdocs-print-site-plugin)
in headless Chromium and saves it to site/pdf/genai-labs.pdf, which is the
file the "Download PDF" button links to.
"""

import functools
import http.server
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

SITE_DIR = Path(__file__).resolve().parent.parent / "site"
PDF_PATH = SITE_DIR / "pdf" / "genai-labs.pdf"

# Insert a table of contents after the cover page, following the nav: day
# groups, their pages, and each page's h2 sections. The plugin's own TOC is
# off because it needs Material's right-hand sidebar, which the toc.integrate
# feature removes.
BUILD_TOC_JS = """
() => {
  const text = (el) => el.textContent.replace("\u00b6", "").trim();
  const entry = (section) => {
    const h1 = section.querySelector("h1");
    const children = [...section.querySelectorAll(":scope > section.print-page")].map(entry);
    const headings = [...section.querySelectorAll("h2[id]")]
      .filter((h2) => h2.closest("section.print-page") === section)
      .map((h2) => `<li><a href="#${h2.id}">${text(h2)}</a></li>`);
    const sub = [...children, ...headings].join("");
    return `<li><a href="#${section.id}">${h1 ? text(h1) : section.id}</a>${sub ? `<ul>${sub}</ul>` : ""}</li>`;
  };
  const top = [...document.querySelectorAll("section.print-page[id]")]
    .filter((s) => !s.parentElement.closest("section.print-page"));
  const toc = document.createElement("section");
  toc.className = "pdf-toc md-typeset";
  toc.innerHTML = `<h1>Table of contents</h1><ul>${top.map(entry).join("")}</ul>`;
  const cover = document.getElementById("print-site-cover-page");
  cover ? cover.after(toc) : top[0].before(toc);
}
"""


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass


def main() -> None:
    if not (SITE_DIR / "print_page" / "index.html").exists():
        raise SystemExit("site/print_page/ not found, run `mkdocs build` first.")

    handler = functools.partial(QuietHandler, directory=str(SITE_DIR))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_port}/print_page/"

    PDF_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(color_scheme="light")
            page.goto(url, wait_until="networkidle")
            page.evaluate(BUILD_TOC_JS)
            page.evaluate("document.fonts.ready")
            page.pdf(
                path=str(PDF_PATH),
                format="A4",
                print_background=True,
                margin={"top": "15mm", "bottom": "15mm", "left": "12mm", "right": "12mm"},
            )
            browser.close()
    finally:
        server.shutdown()

    print(f"Wrote {PDF_PATH.relative_to(SITE_DIR.parent)}")


if __name__ == "__main__":
    main()
