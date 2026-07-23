"""Dependency-free HTML surfaces for the Brand System Maker."""

# The page source deliberately keeps CSS declarations and short HTML fragments together.
# ruff: noqa: E501

from fastapi.responses import HTMLResponse

HOME_PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light dark">
  <meta name="description" content="A plain-language guide to running Brand System Maker.">
  <title>Brand System Maker — One name in, one brand kit out</title>
  <link rel="icon" href="/favicon.svg" type="image/svg+xml">
  <script src="/assets/app.js" defer></script>
  <style>
    :root {
      color-scheme: light dark;
      --paper: #f4f0e7;
      --paper-strong: #fffdf7;
      --ink: #17201c;
      --muted: #526058;
      --line: #b9b8ad;
      --accent: #b83b27;
      --accent-ink: #fffaf1;
      --signal: #bee452;
      --code: #17201c;
      --code-ink: #f6f2e9;
      --shadow: 6px 6px 0 #17201c;
      --radius: 0.4rem;
    }

    * { box-sizing: border-box; }
    html { scroll-behavior: smooth; }
    body {
      margin: 0;
      background: var(--paper);
      color: var(--ink);
      font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      font-size: 1rem;
      line-height: 1.6;
    }
    a { color: inherit; text-underline-offset: 0.2em; }
    a:hover { text-decoration-thickness: 0.18em; }
    a:focus-visible, summary:focus-visible {
      outline: 3px solid var(--accent);
      outline-offset: 4px;
    }
    code { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
    .skip-link {
      position: fixed;
      z-index: 20;
      top: 0.75rem;
      left: 0.75rem;
      padding: 0.65rem 0.9rem;
      background: var(--ink);
      color: var(--paper-strong);
      transform: translateY(-160%);
    }
    .skip-link:focus { transform: translateY(0); }
    .shell { width: min(72rem, calc(100% - 2rem)); margin-inline: auto; }
    .site-header { border-bottom: 1px solid var(--line); }
    .site-header .shell {
      min-height: 4.75rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 1.5rem;
    }
    .wordmark { display: flex; align-items: center; gap: 0.75rem; text-decoration: none; font-weight: 800; }
    .mark {
      display: grid;
      place-items: center;
      width: 2.5rem;
      height: 2.5rem;
      background: var(--code);
      color: var(--signal);
      border-radius: 50%;
      font-size: 0.72rem;
      letter-spacing: 0.08em;
    }
    nav ul { display: flex; align-items: center; gap: 1.25rem; margin: 0; padding: 0; list-style: none; }
    nav a { min-height: 2.75rem; display: inline-flex; align-items: center; font-weight: 700; }
    .hero { padding-block: clamp(4rem, 9vw, 8rem); border-bottom: 1px solid var(--line); }
    .hero-grid { display: grid; grid-template-columns: minmax(0, 1.45fr) minmax(16rem, 0.55fr); gap: 4rem; align-items: end; }
    .eyebrow { margin: 0 0 1.25rem; font-size: 0.78rem; font-weight: 900; letter-spacing: 0.12em; text-transform: uppercase; }
    .eyebrow span { padding: 0.35rem 0.55rem; background: var(--signal); color: #17201c; }
    h1, h2, h3 { line-height: 1.05; letter-spacing: -0.04em; }
    h1 { max-width: 13ch; margin: 0; font-family: Georgia, "Times New Roman", serif; font-size: clamp(3.2rem, 8vw, 7.6rem); font-weight: 500; }
    .hero-copy { max-width: 35rem; margin: 1.5rem 0 0; color: var(--muted); font-size: clamp(1.05rem, 2vw, 1.3rem); }
    .actions { display: flex; flex-wrap: wrap; gap: 0.8rem; margin-top: 2rem; }
    .button {
      min-height: 3rem;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 0.65rem 1rem;
      border: 2px solid var(--ink);
      border-radius: var(--radius);
      background: var(--accent);
      color: var(--accent-ink);
      font-weight: 850;
      text-decoration: none;
      box-shadow: 3px 3px 0 var(--ink);
      transition: transform 120ms ease, box-shadow 120ms ease;
    }
    .button:hover { transform: translate(2px, 2px); box-shadow: 1px 1px 0 var(--ink); }
    .button.secondary { background: transparent; color: var(--ink); }
    [hidden] { display: none !important; }
    .generator {
      border: 2px solid var(--ink);
      border-radius: var(--radius);
      background: var(--paper-strong);
      box-shadow: var(--shadow);
    }
    .generator-header { padding: 1rem 1.25rem; border-bottom: 2px solid var(--ink); }
    .generator-header strong { display: block; font-size: 1.1rem; }
    .generator-header span { display: block; margin-top: 0.25rem; color: var(--muted); font-size: 0.9rem; }
    .generator form { padding: 1.25rem; }
    .generator label { display: block; margin-bottom: 0.5rem; font-weight: 850; }
    .generator input {
      width: 100%;
      min-height: 3.5rem;
      padding: 0.75rem;
      border: 2px solid var(--ink);
      border-radius: var(--radius);
      background: var(--paper);
      color: var(--ink);
      font: inherit;
      font-size: 1.05rem;
    }
    .generator input:focus-visible { outline: 3px solid var(--accent); outline-offset: 3px; }
    .form-meta { display: flex; justify-content: space-between; gap: 1rem; margin: 0.45rem 0 1rem; color: var(--muted); font-size: 0.8rem; }
    .generate-button { width: 100%; cursor: pointer; }
    .generate-button:disabled { cursor: wait; opacity: 0.78; }
    .generate-button.is-loading::before {
      content: "";
      width: 0.85rem;
      height: 0.85rem;
      margin-right: 0.65rem;
      border: 2px solid currentColor;
      border-right-color: transparent;
      border-radius: 50%;
      animation: spin 700ms linear infinite;
    }
    .generation-status { min-height: 1.5rem; margin: 0.8rem 0 0; color: var(--muted); font-size: 0.85rem; }
    @keyframes spin { to { transform: rotate(360deg); } }
    .results { scroll-margin-top: 1rem; background: var(--paper-strong); }
    .results:focus { outline: none; }
    .results-header { display: grid; grid-template-columns: 1fr auto; gap: 2rem; align-items: end; margin-bottom: 2rem; }
    .result-kind { display: inline-block; margin: 0 0 0.75rem; padding: 0.25rem 0.5rem; background: var(--signal); color: #17201c; font-size: 0.75rem; font-weight: 900; letter-spacing: 0.08em; text-transform: uppercase; }
    .result-kind.error, .result-kind.refused { background: var(--accent); color: var(--accent-ink); }
    .results h2 { max-width: none; }
    .result-target { margin: 0.6rem 0 0; color: var(--muted); font-size: 1.1rem; }
    .result-actions { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 0.75rem; }
    .quiet-button {
      min-height: 2.75rem;
      display: inline-flex;
      align-items: center;
      padding: 0.55rem 0.8rem;
      border: 2px solid var(--ink);
      border-radius: var(--radius);
      background: transparent;
      color: var(--ink);
      cursor: pointer;
      font: inherit;
      font-weight: 800;
      text-decoration: none;
    }
    .result-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1rem; }
    .result-card { min-width: 0; padding: 1.5rem; border: 1px solid var(--line); background: var(--paper); }
    .identity-card { grid-column: 1 / -1; }
    .result-label { margin: 0 0 1rem; font-size: 0.72rem; font-weight: 900; letter-spacing: 0.1em; text-transform: uppercase; }
    .result-copy { margin: 0; color: var(--muted); white-space: pre-wrap; }
    .result-tagline { margin: 0 0 1rem; font-family: Georgia, "Times New Roman", serif; font-size: clamp(1.8rem, 4vw, 3.25rem); line-height: 1.08; }
    .traits { display: flex; flex-wrap: wrap; gap: 0.5rem; margin: 1.25rem 0 0; padding: 0; list-style: none; }
    .traits li { padding: 0.35rem 0.6rem; border: 1px solid var(--line); border-radius: 999px; font-size: 0.85rem; font-weight: 700; }
    .palette-grid { display: grid; gap: 0.75rem; }
    .swatch { display: grid; grid-template-columns: 3rem 1fr; gap: 0.75rem; align-items: center; }
    .swatch-color { width: 3rem; height: 3rem; border: 1px solid var(--line); border-radius: 50%; background: var(--line); }
    .swatch-words { min-width: 0; }
    .swatch-words strong, .swatch-words code { display: block; }
    .swatch-words strong { text-transform: capitalize; }
    .swatch-words code { color: var(--muted); font-size: 0.78rem; }
    section { padding-block: clamp(3.5rem, 7vw, 6.5rem); }
    section + section { border-top: 1px solid var(--line); }
    .section-heading { display: grid; grid-template-columns: 1fr 2fr; gap: 2rem; margin-bottom: 2.5rem; }
    .kicker { font-size: 0.75rem; font-weight: 900; letter-spacing: 0.12em; text-transform: uppercase; }
    h2 { max-width: 18ch; margin: 0; font-family: Georgia, "Times New Roman", serif; font-size: clamp(2.1rem, 5vw, 4rem); font-weight: 500; }
    .steps { counter-reset: step; display: grid; grid-template-columns: repeat(3, 1fr); border: 1px solid var(--line); }
    .step { counter-increment: step; min-width: 0; padding: 1.5rem; border-right: 1px solid var(--line); }
    .step:last-child { border: 0; }
    .step::before { content: "0" counter(step); display: block; margin-bottom: 3rem; color: var(--accent); font-family: ui-monospace, monospace; font-weight: 900; }
    h3 { margin: 0 0 0.75rem; font-size: 1.35rem; letter-spacing: -0.02em; }
    .step p { margin: 0; color: var(--muted); }
    .guide { display: grid; grid-template-columns: minmax(0, 0.7fr) minmax(0, 1.3fr); gap: clamp(2rem, 6vw, 6rem); }
    .guide > * { min-width: 0; }
    .guide-nav { align-self: start; position: sticky; top: 1.5rem; }
    .guide-nav ol { padding-left: 1.25rem; }
    .guide-nav li { margin-block: 0.65rem; }
    .instructions article { padding-bottom: 2.5rem; }
    .number { display: inline-grid; place-items: center; width: 2rem; height: 2rem; margin-right: 0.5rem; border-radius: 50%; background: var(--ink); color: var(--signal); font: 800 0.9rem ui-monospace, monospace; }
    pre {
      max-width: 100%;
      overflow-x: auto;
      margin: 1rem 0;
      padding: 1rem;
      border-radius: var(--radius);
      background: var(--code);
      color: var(--code-ink);
      line-height: 1.55;
      box-shadow: 4px 4px 0 var(--accent);
    }
    .note { padding: 1rem; border-left: 5px solid var(--accent); background: var(--paper-strong); }
    .status-list { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; }
    .status-list div { padding: 1.25rem; border-top: 4px solid var(--ink); background: var(--paper-strong); }
    .status-list dt { font: 900 0.85rem ui-monospace, monospace; text-transform: uppercase; }
    .status-list dd { margin: 0.55rem 0 0; color: var(--muted); }
    footer { padding-block: 2rem; border-top: 1px solid var(--line); }
    footer .shell { display: flex; justify-content: space-between; gap: 2rem; }
    footer p { margin: 0; }
    .footer-links { display: flex; flex-wrap: wrap; gap: 1rem; }

    @media (max-width: 48rem) {
      .site-header .shell { align-items: flex-start; padding-block: 0.8rem; }
      .site-header nav ul { gap: 0.25rem; flex-direction: column; align-items: flex-end; }
      .site-header nav a { min-height: 2.75rem; }
      .hero-grid, .section-heading, .guide { grid-template-columns: minmax(0, 1fr); }
      .hero-grid { gap: 3rem; }
      .steps { grid-template-columns: 1fr; }
      .step { border-right: 0; border-bottom: 1px solid var(--line); }
      .step::before { margin-bottom: 1.5rem; }
      .guide-nav { position: static; }
      .status-list { grid-template-columns: 1fr; }
      .results-header, .result-grid { grid-template-columns: 1fr; }
      .result-actions { justify-content: flex-start; }
      .identity-card { grid-column: auto; }
      footer .shell { flex-direction: column; }
    }
    @media (max-width: 25rem) {
      .shell { width: min(100% - 1.25rem, 72rem); }
      .wordmark > span:last-child { max-width: 8rem; line-height: 1.1; }
      h1 { font-size: clamp(2.65rem, 16vw, 3.5rem); }
      .actions, .button { width: 100%; }
    }
    @media (prefers-color-scheme: dark) {
      :root {
        --paper: #131a17;
        --paper-strong: #1c2521;
        --ink: #f1eee4;
        --muted: #b7c0b9;
        --line: #4c5851;
        --accent: #ff765c;
        --accent-ink: #171b18;
        --signal: #c7ed5f;
        --code: #080c0a;
        --code-ink: #f6f2e9;
        --shadow: 6px 6px 0 #738078;
      }
      .button { border-color: var(--ink); box-shadow: 3px 3px 0 var(--ink); }
      .button:hover { box-shadow: 1px 1px 0 var(--ink); }
    }
    @media (prefers-reduced-motion: reduce) {
      html { scroll-behavior: auto; }
      *, *::before, *::after { transition-duration: 0.01ms !important; }
      .generate-button.is-loading::before { animation-duration: 1ms; }
    }
  </style>
</head>
<body>
  <a class="skip-link" href="#main-content">Skip to main content</a>
  <header class="site-header">
    <div class="shell">
      <a class="wordmark" href="/" aria-label="Brand System Maker home">
        <span class="mark" aria-hidden="true">BSM</span><span>Brand System Maker</span>
      </a>
      <nav aria-label="Primary navigation">
        <ul><li><a href="#how-it-works">How it works</a></li><li><a href="/brands">Library</a></li><li><a href="#quick-start">Quick start</a></li><li><a href="/docs">API docs</a></li></ul>
      </nav>
    </div>
  </header>

  <main id="main-content">
    <div class="hero">
      <div class="shell hero-grid">
        <div>
          <p class="eyebrow"><span>Local tool · AI assisted</span></p>
          <h1>One name in. One brand world out.</h1>
          <p class="hero-copy">Brand System Maker turns a parody brand name into a structured, validated kit with identity, voice, personality, and color direction.</p>
          <div class="actions"><a class="button" href="/docs">Open the API console</a><a class="button secondary" href="#quick-start">Follow the quick start</a></div>
        </div>
        <aside class="generator" aria-labelledby="generator-heading">
          <div class="generator-header"><strong id="generator-heading">Generate a brand kit</strong><span>One name is all it takes.</span></div>
          <form id="brand-form">
            <label for="brand-name">Parody brand name</label>
            <input id="brand-name" name="brand_name" type="text" required maxlength="80" autocomplete="off" placeholder="Try Floogle" aria-describedby="name-help name-count">
            <div class="form-meta"><span id="name-help">Original names work best.</span><span id="name-count">0 / 80</span></div>
            <button class="button generate-button" id="generate-button" type="submit"><span id="generate-label">Generate brand kit</span></button>
            <p class="generation-status" id="generation-status" role="status" aria-live="polite"></p>
          </form>
        </aside>
      </div>
    </div>

    <section class="results" id="brand-results" aria-labelledby="results-heading" tabindex="-1" hidden>
      <div class="shell">
        <header class="results-header">
          <div><p class="result-kind success" id="result-kind">Brand kit ready</p><h2 id="results-heading">Your brand</h2><p class="result-target" id="result-target"></p></div>
          <div class="result-actions"><a class="quiet-button" id="view-saved-brand" href="/brands" hidden>View full brand</a><button class="quiet-button" id="copy-result" type="button">Copy JSON</button><button class="quiet-button" id="reset-generator" type="button">Make another</button></div>
        </header>
        <div class="result-grid" id="result-content"></div>
      </div>
    </section>

    <section id="how-it-works" aria-labelledby="how-heading">
      <div class="shell">
        <div class="section-heading"><p class="kicker">The whole idea</p><h2 id="how-heading">A small pipeline with a useful finish line.</h2></div>
        <div class="steps">
          <article class="step"><h3>Name it</h3><p>Send one original parody brand name, between 1 and 80 characters.</p></article>
          <article class="step"><h3>Make it</h3><p>The model develops the identity, positioning, personality, and palette.</p></article>
          <article class="step"><h3>Check it</h3><p>The service validates every required field before returning the complete kit.</p></article>
        </div>
      </div>
    </section>

    <section id="quick-start" aria-labelledby="quick-heading">
      <div class="shell">
        <div class="section-heading"><p class="kicker">Quick start</p><h2 id="quick-heading">From download to first brand in three steps.</h2></div>
        <div class="guide">
          <div class="guide-nav"><strong>On this page</strong><ol><li><a href="#configure">Add your API key</a></li><li><a href="#run">Start the app</a></li><li><a href="#create">Create a brand</a></li></ol></div>
          <div class="instructions">
            <article id="configure"><h3><span class="number" aria-hidden="true">1</span>Add your API key</h3><p>Copy the example settings file. Create an <a href="https://openrouter.ai/settings/keys">OpenRouter key</a>, then place it after the equals sign in <code>.env</code>.</p><pre tabindex="0"><code>cp .env.example .env
# Open .env and set:
OPENROUTER_API_KEY=your-key-here</code></pre><p class="note"><strong>Keep it private.</strong> Never paste your key into a browser page, screenshot it, or commit <code>.env</code> to Git.</p></article>
            <article id="run"><h3><span class="number" aria-hidden="true">2</span>Install and start</h3><p>From the project folder, install the dependencies and launch the local server.</p><pre tabindex="0"><code>uv sync --extra dev
uv run brand-maker</code></pre><p>Leave that terminal open. The app is ready when it reports <code>Uvicorn running on http://127.0.0.1:8000</code>.</p></article>
            <article id="create"><h3><span class="number" aria-hidden="true">3</span>Create your first brand</h3><p>Open the <a href="/docs">interactive API console</a>. Expand <strong>POST /brand</strong>, choose <strong>Try it out</strong>, replace the sample name, and press <strong>Execute</strong>.</p><pre tabindex="0"><code>{
  "brand_name": "Floogle"
}</code></pre><p>Prefer a terminal? This request does the same thing:</p><pre tabindex="0"><code>curl -X POST http://127.0.0.1:8000/brand \
  -H "Content-Type: application/json" \
  -d '{"brand_name":"Floogle"}'</code></pre></article>
          </div>
        </div>
      </div>
    </section>

    <section aria-labelledby="responses-heading">
      <div class="shell">
        <div class="section-heading"><p class="kicker">What comes back</p><h2 id="responses-heading">Readable outcomes, including when things go wrong.</h2></div>
        <dl class="status-list"><div><dt>ok</dt><dd>A complete kit that passed every structural check.</dd></div><div><dt>refused</dt><dd>The name was not safe or suitable to develop.</dd></div><div><dt>error</dt><dd>The provider was unavailable or could not return a valid kit.</dd></div></dl>
      </div>
    </section>
  </main>

  <footer><div class="shell"><p><strong>Brand System Maker</strong><br><span>Built for creative exploration.</span></p><div class="footer-links"><a href="/">Home</a><a href="/brands">Library</a><a href="/docs">Swagger</a><a href="/redoc">ReDoc</a><a href="/health">Health</a></div></div></footer>
</body>
</html>
"""

FAVICON = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
<rect width="64" height="64" rx="32" fill="#17201c"/>
<path fill="#bee452" d="M15 17h20c9 0 14 4 14 11 0 4-2 7-6 9 5 2 7 5 7 10 0 8-5 12-15 12H15zm12 10v7h7c3 0 5-1 5-4s-2-3-5-3zm0 16v7h8c3 0 5-1 5-4s-2-3-5-3z"/>
</svg>"""

DOCS_NAVIGATION = """
<style>
  .app-home-link {
    position: fixed; z-index: 10000; right: 1rem; bottom: 1rem;
    min-height: 44px; display: inline-flex; align-items: center;
    padding: 0 1rem; border: 2px solid #17201c; border-radius: 4px;
    background: #bee452; color: #17201c; font: 800 14px/1 system-ui, sans-serif;
    text-decoration: none; box-shadow: 3px 3px 0 #17201c;
  }
  .app-home-link:focus-visible { outline: 3px solid #d24a31; outline-offset: 3px; }
</style>
"""


def add_home_navigation(page: HTMLResponse) -> HTMLResponse:
    """Add a stable way back to the project guide from framework documentation."""
    document = bytes(page.body).decode("utf-8")
    document = document.replace("<html>", '<html lang="en">', 1)
    document = document.replace("</head>", f"{DOCS_NAVIGATION}</head>", 1)
    document = document.replace(
        "<body>",
        '<body><a class="app-home-link" href="/" aria-label="Back to home">← Back to home</a>',
        1,
    )
    headers = {key: value for key, value in page.headers.items() if key != "content-length"}
    return HTMLResponse(document, status_code=page.status_code, headers=headers)
