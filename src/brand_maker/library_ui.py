"""Dependency-free browser behavior for saved brand pages."""

# JavaScript output rendering uses text-only DOM APIs by design.
# ruff: noqa: E501

LIBRARY_SCRIPT = r'''"use strict";

const pageType = document.body.dataset.page;
const safeHex = /^#[0-9a-fA-F]{6}$/;
let detailPayload = null;

function setText(element, value) {
  element.textContent = typeof value === "string" ? value : "";
}

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) setText(node, text);
  return node;
}

function displayDate(value) {
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return "Date unavailable";
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(date);
}

function applyColor(node, value) {
  if (safeHex.test(value)) node.style.backgroundColor = value;
}

function paletteStrip(palette) {
  const strip = element("div", "palette-strip");
  for (const role of ["primary", "secondary", "accent", "background"]) {
    const color = element("span");
    color.setAttribute("aria-hidden", "true");
    applyColor(color, palette?.[role]);
    strip.append(color);
  }
  return strip;
}

function brandCard(brand) {
  const card = element("article", "brand-card");
  const link = element("a", "brand-card-link");
  link.href = `/brands/${encodeURIComponent(brand.id)}`;
  link.append(paletteStrip(brand.color_palette));
  link.append(element("p", "card-target", `Parody of ${brand.parody_target}`));
  link.append(element("h2", "", brand.brand_name));
  link.append(element("p", "card-tagline", brand.tagline));
  const foot = element("div", "card-foot");
  foot.append(element("time", "", displayDate(brand.created_at)));
  foot.append(element("span", "", "View full kit →"));
  link.append(foot);
  card.append(link);
  return card;
}

function messageState(kind, title, copy, actionText, actionHref) {
  const state = element("div", kind === "error" ? "error-state" : "empty-state");
  state.append(element("h2", "", title));
  state.append(element("p", "", copy));
  const action = element("a", "primary-action", actionText);
  action.href = actionHref;
  state.append(action);
  return state;
}

function renderPagination(payload) {
  const pagination = document.getElementById("library-pagination");
  pagination.replaceChildren();
  if (payload.total_pages <= 1) {
    pagination.hidden = true;
    return;
  }
  if (payload.page > 1) {
    const previous = element("a", "", "← Previous");
    previous.href = `/brands?page=${payload.page - 1}`;
    pagination.append(previous);
  }
  pagination.append(element("span", "", `Page ${payload.page} of ${payload.total_pages}`));
  if (payload.page < payload.total_pages) {
    const next = element("a", "", "Next →");
    next.href = `/brands?page=${payload.page + 1}`;
    pagination.append(next);
  }
  pagination.hidden = false;
}

async function loadLibrary() {
  const root = document.getElementById("brand-library");
  const count = document.getElementById("library-count");
  const requestedPage = Math.max(1, Number.parseInt(new URLSearchParams(location.search).get("page") || "1", 10) || 1);
  try {
    const params = new URLSearchParams({ page: String(requestedPage), pageSize: "12" });
    const response = await fetch("/api/brands?" + params.toString());
    if (!response.ok) throw new Error("library request failed");
    const payload = await response.json();
    root.replaceChildren();
    root.setAttribute("aria-busy", "false");
    count.textContent = `${payload.total_items} saved ${payload.total_items === 1 ? "brand" : "brands"}`;
    if (payload.items.length === 0) {
      const hasBrands = payload.total_items > 0;
      root.append(messageState(
        "empty",
        hasBrands ? "No brands on this page" : "No brands yet",
        hasBrands ? "Return to the beginning of your collection." : "Generate your first brand kit and it will appear here automatically.",
        hasBrands ? "Go to the first page" : "Create your first brand",
        hasBrands ? "/brands" : "/#brand-form",
      ));
      return;
    }
    const grid = element("div", "brand-grid");
    for (const brand of payload.items) grid.append(brandCard(brand));
    root.append(grid);
    renderPagination(payload);
  } catch {
    root.replaceChildren(messageState("error", "Could not load the library", "The local brand store could not be reached. Try refreshing this page.", "Refresh", location.href));
    root.setAttribute("aria-busy", "false");
    count.textContent = "Library unavailable";
  }
}

function detailCard(label, copy, className = "") {
  const card = element("article", `detail-card ${className}`.trim());
  card.append(element("p", "section-label", label));
  card.append(element("p", "detail-copy", copy));
  return card;
}

function paletteCard(palette) {
  const card = element("article", "detail-card");
  card.append(element("p", "section-label", "Color palette"));
  const list = element("div", "palette-list");
  for (const role of ["primary", "secondary", "accent", "background"]) {
    const value = typeof palette?.[role] === "string" ? palette[role] : "Unavailable";
    const swatch = element("div", "swatch");
    const color = element("span", "swatch-color");
    color.setAttribute("aria-hidden", "true");
    applyColor(color, value);
    const words = element("span");
    words.append(element("strong", "", role));
    words.append(element("code", "", value));
    swatch.append(color, words);
    list.append(swatch);
  }
  card.append(list);
  return card;
}

function renderDetail(saved) {
  detailPayload = saved;
  const kit = saved.kit;
  const root = document.getElementById("brand-detail");
  root.replaceChildren();
  root.setAttribute("aria-busy", "false");

  const hero = element("header", "detail-hero");
  const heading = element("div");
  const label = element("p", "eyebrow");
  label.append(element("span", "", "Saved brand kit"));
  const title = element("h1", "", kit.brand_name);
  title.id = "detail-title";
  heading.append(label, title, element("p", "detail-target", `A parody of ${kit.parody_target} · Saved ${displayDate(saved.created_at)}`));
  const actions = element("div", "detail-actions");
  const copy = element("button", "quiet-button", "Copy JSON");
  copy.type = "button";
  copy.addEventListener("click", copyDetail);
  const create = element("a", "primary-action", "Create another");
  create.href = "/#brand-form";
  actions.append(copy, create);
  hero.append(heading, actions);

  const grid = element("div", "detail-grid");
  const identity = element("article", "detail-card identity-card");
  identity.append(element("p", "section-label", "Tagline"));
  identity.append(element("blockquote", "tagline", kit.tagline));
  identity.append(element("p", "detail-copy", kit.description));
  const voice = detailCard("Brand voice", kit.brand_voice);
  const traits = element("ul", "traits");
  for (const trait of kit.personality) traits.append(element("li", "", trait));
  voice.append(traits);
  grid.append(identity, voice, paletteCard(kit.color_palette));
  root.append(hero, grid);
  document.title = `${kit.brand_name} — Brand System Maker`;
}

async function copyDetail(event) {
  const button = event.currentTarget;
  try {
    await navigator.clipboard.writeText(JSON.stringify(detailPayload, null, 2));
    button.textContent = "Copied";
  } catch {
    button.textContent = "Copy unavailable";
  }
}

async function loadDetail() {
  const root = document.getElementById("brand-detail");
  try {
    const response = await fetch(`/api/brands/${encodeURIComponent(document.body.dataset.brandId)}`);
    if (!response.ok) throw new Error("detail request failed");
    renderDetail(await response.json());
  } catch {
    root.replaceChildren(messageState("error", "Could not load this brand", "The saved kit could not be retrieved.", "Return to the library", "/brands"));
    root.setAttribute("aria-busy", "false");
  }
}

if (pageType === "library") loadLibrary();
if (pageType === "detail") loadDetail();
'''
