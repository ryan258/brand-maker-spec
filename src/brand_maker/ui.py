"""Browser behavior for generating and presenting a brand kit."""

# JavaScript is kept dependency-free and uses text-only DOM APIs for model output.
# ruff: noqa: E501

UI_SCRIPT = r""""use strict";

const form = document.getElementById("brand-form");
const input = document.getElementById("brand-name");
const count = document.getElementById("name-count");
const submit = document.getElementById("generate-button");
const submitLabel = document.getElementById("generate-label");
const status = document.getElementById("generation-status");
const results = document.getElementById("brand-results");
const resultKind = document.getElementById("result-kind");
const resultTitle = document.getElementById("results-heading");
const resultTarget = document.getElementById("result-target");
const resultContent = document.getElementById("result-content");
const copyButton = document.getElementById("copy-result");
const resetButton = document.getElementById("reset-generator");
const viewSavedBrand = document.getElementById("view-saved-brand");

let currentResponse = null;

function setText(element, value) {
  element.textContent = typeof value === "string" ? value : "";
}

function updateCount() {
  count.textContent = `${input.value.length} / 80`;
}

function setBusy(busy) {
  submit.disabled = busy;
  input.disabled = busy;
  form.setAttribute("aria-busy", String(busy));
  submit.classList.toggle("is-loading", busy);
  submitLabel.textContent = busy ? "Building your brand…" : "Generate brand kit";
}

function makeElement(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) setText(element, text);
  return element;
}

function makeCard(label, content, className = "") {
  const card = makeElement("article", `result-card ${className}`.trim());
  card.append(makeElement("p", "result-label", label));
  card.append(makeElement("p", "result-copy", content));
  return card;
}

function renderPalette(palette) {
  const card = makeElement("article", "result-card palette-card");
  card.append(makeElement("p", "result-label", "Color palette"));
  const grid = makeElement("div", "palette-grid");
  const safeHex = /^#[0-9a-fA-F]{6}$/;

  for (const role of ["primary", "secondary", "accent", "background"]) {
    const value = typeof palette?.[role] === "string" ? palette[role] : "Unavailable";
    const swatch = makeElement("div", "swatch");
    const sample = makeElement("span", "swatch-color");
    sample.setAttribute("aria-hidden", "true");
    if (safeHex.test(value)) sample.style.backgroundColor = value;
    const words = makeElement("span", "swatch-words");
    words.append(makeElement("strong", "", role));
    words.append(makeElement("code", "", value));
    swatch.append(sample, words);
    grid.append(swatch);
  }

  card.append(grid);
  return card;
}

function renderSuccess(response) {
  const kit = response.kit;
  currentResponse = response;
  resultContent.replaceChildren();
  resultKind.className = "result-kind success";
  setText(resultKind, "Brand starting point ready");
  setText(resultTitle, kit.brand_name);
  setText(resultTarget, "Concept-stage living workspace created");

  const identity = makeElement("article", "result-card identity-card");
  identity.append(makeElement("p", "result-label", "Tagline"));
  identity.append(makeElement("blockquote", "result-tagline", kit.tagline));
  identity.append(makeElement("p", "result-copy", kit.description));

  const voice = makeElement("article", "result-card voice-card");
  voice.append(makeElement("p", "result-label", "Brand voice"));
  voice.append(makeElement("p", "result-copy", kit.brand_voice));
  const traits = makeElement("ul", "traits");
  for (const trait of Array.isArray(kit.personality) ? kit.personality : []) {
    traits.append(makeElement("li", "", trait));
  }
  voice.append(traits);

  resultContent.append(identity, voice, renderPalette(kit.color_palette));
  copyButton.hidden = false;
  if (response.workspace_id || response.id) {
    viewSavedBrand.href = response.workspace_id
      ? `/brand-systems/${encodeURIComponent(response.workspace_id)}`
      : `/brands/${encodeURIComponent(response.id)}`;
    viewSavedBrand.textContent = response.workspace_id ? "Open living workspace" : "View saved kit";
    viewSavedBrand.hidden = false;
  }
  results.hidden = false;
  results.focus({ preventScroll: true });
  results.scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderMessage(kind, message) {
  currentResponse = null;
  resultContent.replaceChildren();
  resultKind.className = `result-kind ${kind}`;
  setText(resultKind, kind === "refused" ? "Request declined" : "Generation stopped");
  setText(resultTitle, kind === "refused" ? "Try a different direction" : "That did not work");
  setText(resultTarget, message || "Please try again in a moment.");
  resultContent.append(makeCard("What to do next", kind === "refused"
    ? "Use an original, lighthearted name that does not target a person or protected group."
    : "Check that the server is running and try again. If the problem continues, verify your provider configuration."));
  copyButton.hidden = true;
  viewSavedBrand.hidden = true;
  results.hidden = false;
  results.focus({ preventScroll: true });
  results.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function parseFailure(response) {
  try {
    const payload = await response.json();
    if (Array.isArray(payload.detail) && payload.detail.length > 0) {
      return payload.detail[0].msg || "Check the brand name and try again.";
    }
    return typeof payload.detail === "string" ? payload.detail : "The request was not accepted.";
  } catch {
    return "The server returned an unreadable response.";
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const brandName = input.value.trim();
  if (!brandName || brandName.length > 80) {
    input.focus();
    status.textContent = "Enter a brand name between 1 and 80 characters.";
    return;
  }

  setBusy(true);
  results.hidden = true;
  status.textContent = `Building ${brandName}. This can take about a minute.`;

  try {
    const response = await fetch("/api/brands", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ brand_name: brandName }),
    });
    if (!response.ok) {
      renderMessage("error", await parseFailure(response));
      return;
    }
    const payload = await response.json();
    if (payload.status === "ok" && payload.kit) renderSuccess(payload);
    else renderMessage(payload.status === "refused" ? "refused" : "error", payload.message);
  } catch {
    renderMessage("error", "Could not reach the Brand System Maker server.");
  } finally {
    setBusy(false);
    status.textContent = "";
  }
});

input.addEventListener("input", updateCount);
resetButton.addEventListener("click", () => {
  results.hidden = true;
  currentResponse = null;
  viewSavedBrand.hidden = true;
  input.value = "";
  updateCount();
  input.focus();
});
copyButton.addEventListener("click", async () => {
  if (!currentResponse) return;
  try {
    await navigator.clipboard.writeText(JSON.stringify(currentResponse, null, 2));
    copyButton.textContent = "Copied";
    window.setTimeout(() => { copyButton.textContent = "Copy JSON"; }, 1600);
  } catch {
    copyButton.textContent = "Copy unavailable";
  }
});

updateCount();
"""
