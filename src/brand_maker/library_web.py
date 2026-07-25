"""HTML shells for the saved brand library."""

# Static HTML fragments are kept compact and visually grouped.
# ruff: noqa: E501

from uuid import UUID

HEAD = """<meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light dark">
  <link rel="icon" href="/favicon.svg" type="image/svg+xml">
  <link rel="stylesheet" href="/assets/library.css">
  <script src="/assets/library.js" defer></script>"""

HEADER = """<a class="skip-link" href="#main-content">Skip to main content</a>
  <header class="site-header"><div class="shell">
    <a class="wordmark" href="/" aria-label="Brand System Maker home"><span class="mark" aria-hidden="true">BSM</span><span>Brand System Maker</span></a>
    <nav aria-label="Primary navigation"><ul><li><a href="/brand-systems">Living brands</a></li><li><a href="/compliance">Compliance</a></li><li><a href="/brands" aria-current="page">Kit library</a></li><li><a href="/docs">API docs</a></li></ul></nav>
  </div></header>"""

FOOTER = """<footer><div class="shell"><p><strong>Brand System Maker</strong><br><span>Built for durable creative systems.</span></p><div class="footer-links"><a href="/brand-systems">Living brands</a><a href="/compliance">Compliance</a><a href="/brands">Kit library</a><a href="/docs">API</a></div></div></footer>"""


def library_page() -> str:
    return f"""<!doctype html>
<html lang="en"><head>{HEAD}
  <meta name="description" content="Browse generated Brand System Maker kits.">
  <title>Brand Library — Brand System Maker</title></head>
<body data-page="library">{HEADER}
  <main id="main-content">
    <header class="page-head"><div class="shell page-head-grid"><div><p class="eyebrow"><span>Your collection</span></p><h1>Quick-start library</h1><p class="lede">Concept-stage starting points, saved locally and ready to develop.</p></div><div><a class="primary-action" href="/#brand-form">Create a new brand</a></div></div></header>
    <section class="library-section" aria-labelledby="library-heading"><div class="shell"><div class="library-meta"><h2 id="library-heading">Saved starting points</h2><p id="library-count" role="status">Loading your library…</p></div><div id="brand-library" aria-busy="true"><div class="loading-grid" aria-label="Loading brands"><div class="skeleton"></div><div class="skeleton"></div><div class="skeleton"></div></div></div><nav class="pagination" id="library-pagination" aria-label="Brand library pages" hidden></nav></div></section>
  </main>{FOOTER}</body></html>"""


def detail_page(brand_id: UUID) -> str:
    return f"""<!doctype html>
<html lang="en"><head>{HEAD}
  <meta name="description" content="Full generated brand kit details.">
  <title>Brand Details — Brand System Maker</title></head>
<body data-page="detail" data-brand-id="{brand_id}">{HEADER}
  <main id="main-content"><section class="detail-section"><div class="shell"><a class="detail-back" href="/brands">← Back to quick-start library</a><div id="brand-detail" aria-busy="true"><div class="detail-hero"><div><p class="eyebrow"><span>Saved starting point</span></p><h1 id="detail-title">Loading brand…</h1><p class="detail-target" id="detail-target">Retrieving the concept-stage kit.</p></div></div><div class="loading-grid" aria-label="Loading brand details"><div class="skeleton"></div><div class="skeleton"></div></div></div></div></section></main>{FOOTER}</body></html>"""


def not_found_page() -> str:
    return f"""<!doctype html>
<html lang="en"><head>{HEAD}<title>Brand not found — Brand System Maker</title></head>
<body data-page="not-found">{HEADER}<main id="main-content"><section class="detail-section"><div class="shell empty-state"><p class="eyebrow"><span>404</span></p><h1>Brand not found</h1><p>This saved brand does not exist or is no longer available.</p><a class="primary-action" href="/brands">Return to the library</a></div></section></main>{FOOTER}</body></html>"""
