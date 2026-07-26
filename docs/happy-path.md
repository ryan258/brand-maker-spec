# Brand Maker — Happy Path Walkthrough

This document provides a clear, step-by-step guide to using **Brand Maker** from start to finish. Follow these exact steps to create a brand workspace, leverage AI to auto-fill missing sections, edit your brand system, and export a complete Brand Bible.

---

## Quick Map of the Web Application

```
http://localhost:8000/
 ├── /                         --> Home Page (Create Workspace & View Workspaces)
 ├── /brand-systems/<brand_id> --> Brand Workshop (Brief, AI Generation, Section Editor, Assets)
 └── /brand-systems/<brand_id>/bible --> Brand Bible (Published system view, Font picker, Export)
```

---

## Step 1: Start the Local Application

1. Open your terminal in the `brand-maker-spec` repository root.
2. Run the application server:
   ```bash
   uv run brand-maker
   ```
3. Open your browser and navigate to:
   ```
   http://localhost:8000
   ```

---

## Step 2: Create a Brand Workspace

On the main page (`http://localhost:8000/`):

1. **What are you starting with?**: Choose your entry path (*Raw idea*, *Named concept*, or *Existing project*).
2. **How should AI help?**: Select your preferred AI mode (*Advisor*, *Copilot*, or *Autonomous strategist*).
3. **Brand or working name**: Enter your brand's name (e.g., `Northstar Books`).
4. **What do you already know?**: *(Optional)* Add a short description, target audience, or brand core context.
5. **Your name**: Enter your owner name.
6. Click **`Create workspace`**. You will automatically be redirected to your **Brand Workshop** page.

---

## Step 3: Fill Out (or Auto-Suggest) the Founding Brief

At the top of the **Brand Workshop** page (`/brand-systems/<brand_id>`):

1. Locate the **Founding brief** section.
2. You can use the quick **Suggested brief answers** buttons to auto-populate starting text:
   - Click **`Use a starter objective`**
   - Click **`Use a starter audience`**
   - Click **`Use a starter success measure`**
3. Fill in any other fields you know (Objective, Audience, Category, Competitors, etc.).
4. *Tip:* Leave anything unknown blank. Every field auto-saves when you pause typing.

---

## Step 4: Auto-Fill Blank Sections with AI Generation

Scroll down past the brief to find the **Generate a starting point** card.

### Option A: Fill Every Section Automatically
* Click the **`Generate complete draft`** button.
* The AI generation engine will process each section in dependency order (Core Identity → Strategy → Colors → Typography → Voice & Tone → etc.), using your founding brief and any existing filled sections as ground truth context.
* You can watch the progress log in real time below the buttons.

### Option B: Fill One Selected Blank Section
1. Scroll down to the **Section Editor** at the bottom of the page.
2. In the left navigation sidebar under *Brand sections*, click the section you want to complete (e.g. `Voice and Tone`).
3. Scroll back up to *Generate a starting point* and click **`Generate selected section`**.
4. The AI will synthesize only that specific section based on your brief and any previously completed sections.

### Option C: Re-align an Existing Brand to the Brief
* Click the **`Update to match brief`** button after editing your founding brief.
* Every **unlocked** section is regenerated so its objective, audience, category, differentiators, constraints, concept, and stage obey the current brief. Locked sections are preserved.
* This replaces unlocked section content, so lock or approve anything you want to keep first.

---

## Step 5: Review, Edit, and Lock Your Brand System

Scroll down to the **Section Editor**:

1. Use the left sidebar menu to navigate between brand sections.
2. Expand content groups (**Prose**, **Rules**, **Tokens**, **Examples**, **Patterns**) to add, reorder, or edit fields manually.
3. Update the **Section status** (`incomplete` → `draft` → `reviewed` → `approved`).
4. *Note on Locking:* Hand-edited or approved sections act as locked anchor points. When you run AI generation again later, locked sections are preserved and fed into the AI as established context.

---

## Step 6: Generate Logos and Production Assets

Locate the **Logos and production assets** card:

1. **AI Logo Generation**: Enter any specific instructions into the *Extra instructions* field (e.g., `Minimalist line mark, monochrome, legibility at small scale`) and click **`Generate logo`**.
2. **Asset Derivatives**: Select an uploaded or generated raster logo from the *Source raster logo* dropdown, then click:
   - **`Create favicon + app icons`**
   - **`Create selected AI variants`**
   - **`Vectorize to SVG`**

---

## Step 7: View and Export the Brand Bible

1. In the header of the Workshop page, click **`View complete brand bible`** (or go to `/brand-systems/<brand_id>/bible`).
2. **In-place Prose Editing**: Click **`Edit in place`** to make live inline edits directly on prose blocks.
3. **Typography Customization**: Use the font pickers to select Google Fonts for headings and body text in real time.
4. **Theme Preview**: Toggle between light and dark mode preview using **`Preview dark mode`**.
5. **Export / Print**: Click **`Print / Export PDF`** or use your browser's print function to generate a clean PDF or printout of your brand bible.

---

## Summary Checklist

- [x] Run `uv run brand-maker` and open `http://localhost:8000`
- [x] Create workspace
- [x] Use starter buttons in Founding Brief
- [x] Click **`Generate complete draft`** to auto-fill missing sections
- [x] Click **`Update to match brief`** to re-align unlocked sections after editing the brief
- [x] Review & edit sections in the Section Editor
- [x] Generate logo & asset variants
- [x] View and print your complete Brand Bible
