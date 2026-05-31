# World News Hub

A self-updating, categorised world-news page. Every hour a GitHub Actions
cron job fetches RSS feeds from trusted wire services and public
broadcasters, rebuilds a single static `docs/index.html`, and commits it.
GitHub Pages serves it. No backend, no database, no ads, no trackers — and
the page makes **zero external requests** at view time (everything is
inlined).

Multilingual UI (EN / DE / FR) with a language filter; headlines stay in
their original language and link straight to the source.

A **Top Story** lead card sits at the top of the page, auto-selected each
build as the newest front-page (World/Politics/Business) story, with a
fallback to the newest item overall. It has its own per-language version, so
switching the filter to DE or FR swaps the hero to that language's lead
instead of leaving a gap. Like the rest of the page it uses no images, only
typography — so the zero-external-requests promise still holds.

## What you get

```
world-news-hub/
├── build.py                    # generator: fetch feeds → docs/index.html
├── feeds.py                    # the source list (edit this to taste)
├── requirements.txt
├── .github/workflows/update.yml  # hourly cron
├── docs/
│   └── index.html              # generated page (served by GitHub Pages)
└── README.md
```

## One-time setup

1. **Create the repo** (e.g. `world-news-hub`) under your account
   (`halvar20000`) and push these files to the `main` branch.

   ```bash
   cd world-news-hub
   git init && git add . && git commit -m "World News Hub"
   git branch -M main
   git remote add origin https://github.com/halvar20000/world-news-hub.git
   git push -u origin main
   ```

2. **Enable Pages:** repo → *Settings* → *Pages* → *Build and deployment* →
   Source = **Deploy from a branch**, Branch = **main**, Folder = **/docs**.
   Your site goes live at `https://halvar20000.github.io/world-news-hub/`.

3. **Allow Actions to push:** repo → *Settings* → *Actions* → *General* →
   *Workflow permissions* → **Read and write permissions** → Save.

That's it. The workflow runs every hour (`cron: "7 * * * *"`), and also on
demand from the *Actions* tab (*Run workflow*). Scheduled runs can be delayed
a few minutes at peak times — that's normal GitHub behaviour, not an error.

## Run it locally

```bash
pip install -r requirements.txt
python build.py          # writes docs/index.html
open docs/index.html     # macOS; or just double-click it
```

## Editing the sources

All sources live in `feeds.py`, grouped by category, each tagged with a
language (`en` / `de` / `fr`). Add or remove lines freely — the generator
**skips any feed that is unreachable or empty**, so a bad URL never breaks
the build. Tunables at the bottom of the file:

- `ITEMS_PER_FEED` — max items taken from each feed (keeps prolific sources
  like Nature or heise from dominating a category).
- `MAX_PER_CATEGORY` — hard cap on cards per category.

**Language balance:** within each category, items are selected round-robin
across languages (EN → DE → FR) rather than by pure recency, so a
high-volume English source can't crowd German or French off the page before
you filter. Recency is preserved within each language. German coverage spans
all five categories (tagesschau, DW, Der Spiegel, Süddeutsche, ZEIT, n-tv,
Tagesspiegel, heise, Golem, Netzpolitik, t3n, Spektrum, wissenschaft.de,
scinexx, Ärzteblatt, Handelsblatt, manager magazin, WirtschaftsWoche,
finanzen.net, Sportschau, kicker, 3D-grenzenlos, 3Druck.com). French can be
expanded the same way — just add `("fr", …)` lines to `feeds.py`.

### A note on Reuters & AP

You asked for the major wire services. Reuters discontinued its public RSS
feeds (~2020) and AP doesn't offer one, so that wire-service tier is covered
instead by **BBC, Al Jazeera, The Guardian, NPR, DW, France 24, tagesschau,
Le Monde and RFI** — all reliable, all with stable public feeds. If you ever
get a licensed Reuters/AP feed URL, just drop it into `feeds.py`.

## Categories included

- **World, Politics & Business**
- **Technology & AI**
- **Science & Health**
- **Financial Information**
- **Sports, Sim Racing & 3D Printing** (your hobby lane)

## Privacy / house style

Matches your SimRacing Hub conventions: independent, no ads, no tracking, no
third-party requests, no cookies. Footer trust line included in all three
languages.
