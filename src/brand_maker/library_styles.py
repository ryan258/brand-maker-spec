"""Styles for the saved brand collection and detail pages."""

# Static CSS intentionally groups related declarations on compact lines.
# ruff: noqa: E501

LIBRARY_CSS = r""":root {
  color-scheme: light dark;
  --paper: #f4f0e7;
  --surface: #fffdf7;
  --ink: #17201c;
  --muted: #526058;
  --line: #b9b8ad;
  --accent: #b83b27;
  --accent-ink: #fffaf1;
  --signal: #bee452;
  --code: #17201c;
  --shadow: 5px 5px 0 #17201c;
  --radius: 0.4rem;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body { margin: 0; background: var(--paper); color: var(--ink); font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; line-height: 1.6; }
a { color: inherit; text-underline-offset: 0.2em; }
a:focus-visible, button:focus-visible { outline: 3px solid var(--accent); outline-offset: 3px; }
button { font: inherit; }
[hidden] { display: none !important; }
.skip-link { position: fixed; z-index: 20; top: 0.5rem; left: 0.5rem; padding: 0.65rem 0.9rem; background: var(--ink); color: var(--surface); transform: translateY(-180%); }
.skip-link:focus { transform: translateY(0); }
.shell { width: min(72rem, calc(100% - 2rem)); margin-inline: auto; }
.site-header { border-bottom: 1px solid var(--line); }
.site-header .shell { min-height: 4.75rem; display: flex; align-items: center; justify-content: space-between; gap: 1.5rem; }
.wordmark { display: flex; align-items: center; gap: 0.75rem; font-weight: 850; text-decoration: none; }
.mark { display: grid; place-items: center; width: 2.5rem; height: 2.5rem; border-radius: 50%; background: var(--code); color: var(--signal); font-size: 0.72rem; letter-spacing: 0.08em; }
nav ul { display: flex; align-items: center; gap: 1.25rem; margin: 0; padding: 0; list-style: none; }
nav a { min-height: 2.75rem; display: inline-flex; align-items: center; font-weight: 750; }
nav a[aria-current="page"] { text-decoration-thickness: 0.2em; }
.page-head { padding-block: clamp(3.5rem, 8vw, 7rem); border-bottom: 1px solid var(--line); }
.page-head-grid { display: grid; grid-template-columns: minmax(0, 1.5fr) minmax(15rem, 0.5fr); gap: 3rem; align-items: end; }
.eyebrow, .section-label, .card-target { margin: 0 0 0.75rem; font-size: 0.72rem; font-weight: 900; letter-spacing: 0.11em; text-transform: uppercase; }
.eyebrow span, .status-chip { display: inline-block; padding: 0.25rem 0.5rem; background: var(--signal); color: #17201c; }
h1, h2, h3 { line-height: 1.08; letter-spacing: -0.035em; }
h1 { max-width: 13ch; margin: 0; font-family: Georgia, "Times New Roman", serif; font-size: clamp(3rem, 8vw, 6.75rem); font-weight: 500; }
h2 { margin: 0; font-family: Georgia, "Times New Roman", serif; font-size: clamp(1.75rem, 3vw, 2.6rem); font-weight: 500; }
.lede { max-width: 40rem; margin: 1.25rem 0 0; color: var(--muted); font-size: 1.15rem; }
.primary-action { min-height: 3rem; display: inline-flex; align-items: center; justify-content: center; padding: 0.65rem 1rem; border: 2px solid var(--ink); border-radius: var(--radius); background: var(--accent); color: var(--accent-ink); box-shadow: 3px 3px 0 var(--ink); font-weight: 850; text-decoration: none; }
.library-section, .detail-section { min-height: 32rem; padding-block: clamp(3rem, 6vw, 5.5rem); }
.library-meta { display: flex; justify-content: space-between; gap: 1rem; align-items: baseline; margin-bottom: 1.5rem; }
.library-meta p { margin: 0; color: var(--muted); }
.loading-grid, .brand-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 1rem; }
.skeleton { min-height: 17rem; border: 1px solid var(--line); background: var(--surface); animation: pulse 1.2s ease-in-out infinite alternate; }
.brand-card { min-width: 0; border: 1px solid var(--line); background: var(--surface); transition: transform 140ms ease, box-shadow 140ms ease; }
.brand-card:hover { transform: translate(-2px, -2px); box-shadow: var(--shadow); }
.brand-card-link { height: 100%; display: flex; flex-direction: column; padding: 1.25rem; text-decoration: none; }
.palette-strip { display: grid; grid-template-columns: repeat(4, 1fr); height: 0.55rem; margin: -1.25rem -1.25rem 1.25rem; }
.palette-strip span { background: var(--line); }
.brand-card h2 { font-size: 2.1rem; }
.card-target { color: var(--muted); }
.card-tagline { flex: 1; margin: 1rem 0 1.5rem; color: var(--muted); }
.card-foot { display: flex; justify-content: space-between; gap: 1rem; padding-top: 1rem; border-top: 1px solid var(--line); font-size: 0.78rem; font-weight: 750; }
.empty-state, .error-state { padding: clamp(2rem, 7vw, 5rem); border: 1px solid var(--line); background: var(--surface); text-align: center; }
.empty-state h2, .error-state h2 { margin-inline: auto; }
.empty-state p, .error-state p { max-width: 34rem; margin: 1rem auto 1.5rem; color: var(--muted); }
.pagination { display: flex; justify-content: center; align-items: center; gap: 1rem; margin-top: 2rem; }
.pagination a { min-height: 2.75rem; display: inline-flex; align-items: center; padding: 0.5rem 0.8rem; border: 1px solid var(--line); font-weight: 750; }
.pagination span { color: var(--muted); }
.detail-back { min-height: 2.75rem; display: inline-flex; align-items: center; margin-bottom: 2rem; font-weight: 750; }
.detail-hero { display: grid; grid-template-columns: minmax(0, 1.4fr) minmax(16rem, 0.6fr); gap: clamp(2rem, 6vw, 5rem); align-items: end; }
.detail-hero h1 { max-width: 14ch; }
.detail-target { margin: 0.75rem 0 0; color: var(--muted); font-size: 1.15rem; }
.detail-actions { display: flex; flex-wrap: wrap; gap: 0.75rem; justify-content: flex-end; }
.quiet-button { min-height: 2.75rem; padding: 0.55rem 0.8rem; border: 2px solid var(--ink); border-radius: var(--radius); background: transparent; color: var(--ink); cursor: pointer; font-weight: 800; }
.detail-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1rem; margin-top: 2rem; }
.detail-card { min-width: 0; padding: 1.5rem; border: 1px solid var(--line); background: var(--surface); }
.identity-card { grid-column: 1 / -1; }
.detail-card .section-label { color: var(--muted); }
.tagline { margin: 0 0 1rem; font-family: Georgia, "Times New Roman", serif; font-size: clamp(2rem, 5vw, 4rem); line-height: 1.08; }
.detail-copy { margin: 0; color: var(--muted); white-space: pre-wrap; }
.traits { display: flex; flex-wrap: wrap; gap: 0.5rem; margin: 1.25rem 0 0; padding: 0; list-style: none; }
.traits li { padding: 0.35rem 0.6rem; border: 1px solid var(--line); border-radius: 999px; font-size: 0.85rem; font-weight: 750; }
.palette-list { display: grid; gap: 0.75rem; }
.swatch { display: grid; grid-template-columns: 3rem 1fr; gap: 0.75rem; align-items: center; }
.swatch-color { width: 3rem; height: 3rem; border: 1px solid var(--line); border-radius: 50%; background: var(--line); }
.swatch strong, .swatch code { display: block; }
.swatch strong { text-transform: capitalize; }
.swatch code { color: var(--muted); font-size: 0.78rem; }
footer { padding-block: 2rem; border-top: 1px solid var(--line); }
footer .shell { display: flex; justify-content: space-between; gap: 2rem; }
footer p { margin: 0; }
.footer-links { display: flex; flex-wrap: wrap; gap: 1rem; }
@keyframes pulse { from { opacity: 0.5; } to { opacity: 1; } }
@media (max-width: 64rem) { .brand-grid, .loading-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 48rem) {
  .site-header .shell { align-items: flex-start; padding-block: 0.8rem; }
  nav ul { gap: 0.25rem; flex-direction: column; align-items: flex-end; }
  .page-head-grid, .detail-hero, .detail-grid { grid-template-columns: minmax(0, 1fr); }
  .detail-actions { justify-content: flex-start; }
  .identity-card { grid-column: auto; }
  footer .shell { flex-direction: column; }
}
@media (max-width: 36rem) {
  .shell { width: min(100% - 1.25rem, 72rem); }
  .wordmark > span:last-child { max-width: 8rem; line-height: 1.1; }
  .brand-grid, .loading-grid { grid-template-columns: minmax(0, 1fr); }
  .library-meta { align-items: flex-start; flex-direction: column; }
}
@media (prefers-color-scheme: dark) {
  :root { --paper: #131a17; --surface: #1c2521; --ink: #f1eee4; --muted: #b7c0b9; --line: #4c5851; --accent: #ff765c; --accent-ink: #171b18; --signal: #c7ed5f; --code: #080c0a; --shadow: 5px 5px 0 #738078; }
}
@media (prefers-reduced-motion: reduce) {
  html { scroll-behavior: auto; }
  *, *::before, *::after { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; }
}
"""
