# ▲ POWER-UP DAILY

New AI abilities, announced like a video game, plus a running **AI LEVEL** (0–100). At 100, AI TAKES OVER.

## How it fits together

| File | Job |
|---|---|
| `index.html`, `styles.css`, `app.js` | The site. Static, so any host works (GitHub Pages, Netlify, etc.). |
| `model.js` | The AI Level math: skill trees, milestones, XP formula, tiers. Single source of truth. |
| `data.js` | What the site shows. **Generated** by the scanner; currently demo data. |
| `scripts/scan.py` | Daily scanner: feeds → editor → `data/state.json` → `data.js`. |
| `scripts/rules.py` | The free editor: keyword filters, heuristic ratings, template hype copy. |
| `scripts/sources.json` | The RSS/Atom feeds to read. Add or remove freely. |
| `data/state.json` | Permanent record of every power-up ever, plus links already seen. |
| `data/days/<date>.json` | One file per day of drops (for a future archive page or video scripts). |
| `.github/workflows/daily-scan.yml` | Runs the scan daily on GitHub and commits the result. |

### What the scanner does
1. Reads every feed and keeps items from the last 36 hours it hasn't seen before.
2. An **editor** picks the real new abilities (skipping funding, drama and opinion pieces), rates each one 1–5 on
   **Reach / Leap / Replace**, picks its skill tree, and writes the headline, "THIS MEANS…", the boss and the
   announcer script. There are two editors:
   - **Rules (free, the default):** `scripts/rules.py` uses keyword filters, simple scores and copy templates.
     It's decent at picking launches; its hype lines are generic and repeat. At most 6 drops a day.
   - **Claude (optional upgrade, about $3–7 a month):** used automatically when `ANTHROPIC_API_KEY` is set.
     Sharper picks, calibrated ratings, specific jokes. If a Claude call fails, that day falls back to the rules.
3. Appends the drops to `data/state.json` and rebuilds `data.js`. The site then calculates rarity, hype, XP and the
   level from the ratings in `model.js`. Every earlier day's drops feed the level, so it keeps climbing over time.
   Switching editors later keeps all history.

On a quiet day nothing new is found and the site keeps showing the last drop.

## Run it locally

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

```bash
.venv/bin/python scripts/scan.py --dry-run
```

```bash
.venv/bin/python scripts/scan.py --editor rules
```

With a key (optional), `scan.py` picks Claude automatically:

```bash
export ANTHROPIC_API_KEY=sk-ant-...   # from console.anthropic.com
.venv/bin/python scripts/scan.py
```

Preview the site: `python3 -m http.server 8080`, then open http://localhost:8080.

## Run it every day automatically (GitHub)
This is already set up at https://github.com/wagmisensei-dot/ai-level (site: https://wagmisensei-dot.github.io/ai-level/).
It runs free every day at 13:00 UTC. Actions → "Daily power-up scan" → **Run workflow** runs it on demand
(set `lookback_hours` to e.g. `168` to pull in a whole week).

To upgrade to Claude later, add the key as a repository secret. Nothing else changes:

```bash
gh secret set ANTHROPIC_API_KEY -R wagmisensei-dot/ai-level
```

## Tuning
- **Stricter or looser picks:** edit the rating rubric in `SYSTEM` inside `scripts/scan.py`.
- **Quality vs cost:** `effort` in `ask_claude()` (`medium` by default; `high` thinks harder).
- **Level math:** weights, milestones and the XP formula live in `model.js`. Changing them changes everyone's level
  retroactively, because the level is recalculated from the full history.
