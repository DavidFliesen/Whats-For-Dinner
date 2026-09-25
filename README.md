# What’s 4 Dinner? — Progressive Web App (PWA)

A smart, clinical dietary dinner decider built for **Eat In vs. Dine Out**, featuring **GLP-1 friendly, low-sodium (<500mg), and calorie-controlled recommendations**, custom fork + plate monogram branding, and a randomizer spin wheel.

## 🚀 Publishing to GitHub Pages in 2 Minutes

1. **Extract this zip archive.**
2. Go to [GitHub](https://github.com/) and create a new repository called `whats-4-dinner`.
3. Drag and upload all the files directly to the root of the repository:
   - `index.html`
   - `manifest.json`
   - `sw.js`
   - `icons/` (containing `icon-192.png` and `icon-512.png`)
   - `agent_pipeline.ipynb`
4. Go to **Settings** -> **Pages** (in the left sidebar).
5. Under **Build and deployment**:
   - Set **Source** to `Deploy from a branch`
   - Set **Branch** to `main` (or `master`) and folder to `/ (root)`.
   - Click **Save**.
6. GitHub will provide your live URL (e.g., `https://<your-username>.github.io/whats-4-dinner/`).

## 📍 Google Maps Integration
External linking to Google Maps works seamlessly once deployed on GitHub Pages because it runs in a top-level, secure HTTPS origin without iframe sandboxing restrictions.

## 🤖 Google Colab Agent
Upload `agent_pipeline.ipynb` to [Google Colab](https://colab.research.google.com/) to automatically query and audit menus in your city using Gemini AI.