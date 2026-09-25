# What’s 4 Dinner? — Version 1.2.0

> **Current Version:** `v1.2.0`  
> **Release Date:** September 2026  
> **Target Platform:** Progressive Web App (PWA) on GitHub Pages & Mobile Web

---

## 🌟 What's New in Version 1.2.0

- **Clickable Images & Cards**: Clicking anywhere on meal card images opens the recipe instructions (Eat In) or server ordering guide (Dine Out) directly, alongside the action buttons.
- **Visual Typography & Contrast Overhaul**: High-contrast, large-format typography in detail modals (`text-base`, `text-lg`, `text-2xl`) with generous spacing, checkmarked ingredient chips, and prominent server ordering callouts.
- **Exact Vector Monogram Logo**: Non-stretched reference rendering maintaining the `What's` top line, fork + plate monogram `D`, elevated artistic `4`, and `inner?` at its natural aspect ratio.
- **Bottom-Center Version Display**: Clean version badge (`Version 1.2.0`) anchored at the bottom center of the application footer.
- **Open-Source Colab Pipeline Fix**: Updated `agent_pipeline_oss.ipynb` removes redundant PyTorch reinstallations to eliminate CUDA dependency conflicts on Google Colab's free T4 GPU.

---

## 📁 Package Directory Structure

```text
whats-4-dinner/
├── index.html               # Main PWA Application (v1.2.0)
├── manifest.json            # Web App Manifest
├── sw.js                    # Service Worker (v1.2.0 Cache)
├── agent_pipeline_oss.ipynb # 100% Free AI Colab Notebook (Zero Keys)
├── README.md                # Documentation & Version Changelog
└── icons/
    ├── icon-192.png         # 192x192 Monogram App Icon
    └── icon-512.png         # 512x512 Monogram App Icon
```

---

## 🚀 Instant GitHub Pages Deployment (2 Minutes)

1. Extract the contents of `whats-4-dinner-v1.2.0.zip`.
2. In your GitHub repository (e.g. `whats-4-dinner`), upload all files directly into the repository root:
   - `index.html`
   - `manifest.json`
   - `sw.js`
   - `icons/` folder (containing `icon-192.png` and `icon-512.png`)
   - `agent_pipeline_oss.ipynb`
   - `README.md`
3. Go to **Settings** ➔ **Pages** in your repository:
   - **Branch:** `main` (or `master`)
   - **Folder:** `/ (root)`
   - Click **Save**.
4. Your PWA will be live at:
   `https://<your-username>.github.io/<repo-name>/`

---

## 📍 Google Maps Navigation
All "Navigate in Google Maps" buttons pass explicit local street addresses and open natively in Google Maps without sandboxing restrictions.

---

## 🤖 Running the Colab Agent
Upload `agent_pipeline_oss.ipynb` to Google Colab, select **T4 GPU**, and click **Run All** to scrape and audit local restaurant dishes without any paid API keys. Use the **Import JSON** button in the PWA header to load the generated `meals.json`.