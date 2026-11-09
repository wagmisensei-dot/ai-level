# ▲ POWER-UP DAILY

New AI abilities, announced like a video game, plus a running **AI LEVEL** (0–100). At 100, AI TAKES OVER.

## How it fits together

| File | Job |
|---|---|
| `index.html`, `styles.css`, `app.js` | The site. Static, so any host works (GitHub Pages, Netlify, etc.). |
| `model.js` | The AI Level math: skill trees, milestones, XP formula, tiers. Single source of truth. |
| `data.js` | What the site shows. **Generated** by the scanner; currently demo data. |
| `scripts/scan.py` | Daily scanner: feeds → Claude → `data/state.json` → `data.js`. |
| `scripts/sources.json` | The RSS/Atom feeds to read. Add or remove freely. |
| `data/state.json` | Permanent record of every power-up ever, plus links already seen. |
| `data/days/<date>.json` | One file per day of drops (for a future archive page or video scripts). |
| `.github/workflows/daily-scan.yml` | Runs the scan daily on GitHub and commits the result. |

### What the scanner does
1. Reads every feed and keeps items from the last 36 hours it hasn't seen before.
2. Sends them to Claude (`claude-opus-5-5`), which picks the real new abilities (skipping funding, drama and opinion pieces),
   rates each one 1–5 on **Reach / Leap / Replace**, picks its skill tree, and writes the headline, "THIS MEANS…",
   the boss and the announcer script. The output is schema-locked JSON, and the script validates it again.
3. Appends the drops to `data/state.json` and rebuilds `data.js`. The site then calculates rarity, hype, XP and the
   level from the ratings in `model.js`. Every earlier day's drops feed the level, so it keeps climbing over time.

On a quiet day nothing new is found and the site keeps showing the last drop.

## Run it locally

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

```bash
.venv/bin/python scripts/scan.py --dry-run
```

```bash
export ANTHROPIC_API_KEY=sk-ant-...   # from console.anthropic.com
.venv/bin/python scripts/scan.py
```

Preview the site: `python3 -m http.server 8080`, then open http://localhost:8080.

## Run it every day automatically (GitHub)
1. Push this folder to a GitHub repo.
2. Add a repository secret: `ANTHROPIC_API_KEY`.
3. Turn on GitHub Pages (Settings → Pages → deploy from the `main` branch, root folder).
4. Actions → "Daily power-up scan" → **Run workflow** to test. After that it runs every day at 13:00 UTC.

## Tuning
- **Stricter or looser picks:** edit the rating rubric in `SYSTEM` inside `scripts/scan.py`.
- **Quality vs cost:** `effort` in `ask_claude()` (`medium` by default; `high` thinks harder).
- **Level math:** weights, milestones and the XP formula live in `model.js`. Changing them changes everyone's level
  retroactively, because the level is recalculated from the full history.
