# -*- coding: utf-8 -*-
"""
World Cup 2026 add-on for World News Hub.

Fetches the public-domain openfootball schedule (fixtures + results, no API
key) and a handful of football news feeds, then hands build.py a structured
bundle: latest results, today's / live matches, upcoming fixtures, the full
schedule grouped by phase, and a short news strip.

Design notes
------------
* Zero external requests at view time is preserved: everything here runs at
  *build* time (hourly, in GitHub Actions). The output is inlined into the
  static page like the rest of the site.
* Kickoff times in the source look like "20:00 UTC-6". We parse the offset,
  turn each kickoff into a real UTC epoch, and let the page's JavaScript
  render it in the reader's locale, pinned to Europe/Paris (matching the
  site clock). Team names are kept as the data provides them (English).
* The whole section auto-hides after the tournament (see HIDE_AFTER), so the
  page returns to normal with no manual cleanup.
* Robust by design: any network/parse failure returns None and build.py
  simply omits the section — a bad fetch never breaks the news build.
"""

import re
import socket
import sys
import time
from datetime import date, datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo
    PARIS = ZoneInfo("Europe/Paris")
except Exception:  # pragma: no cover
    PARIS = timezone.utc

import feedparser

try:
    from urllib.request import Request, urlopen
except Exception:  # pragma: no cover
    Request = urlopen = None

import json

# ---------------------------------------------------------------- config
SCHEDULE_URL = ("https://raw.githubusercontent.com/openfootball/"
                "worldcup.json/master/2026/worldcup.json")

# The section disappears from this date onward (final is 19 Jul 2026; we keep
# it one extra day so the result lingers, then it auto-removes itself).
HIDE_AFTER = date(2026, 7, 21)

# A live match is assumed to last ~2h40 from kickoff (covers ET + a buffer).
LIVE_WINDOW_MIN = 160

# How many cards to show in each of the three focus columns.
N_RESULTS = 10      # most recent finished matches
N_UPCOMING = 10     # next fixtures

# Football news feeds for the WC news strip (lang, source, url).
NEWS_FEEDS = [
    ("en", "BBC Football",      "http://feeds.bbci.co.uk/sport/football/rss.xml"),
    ("en", "Guardian Football", "https://www.theguardian.com/football/rss"),
    ("de", "kicker",            "https://newsfeed.kicker.de/news/fussball/wm"),
    ("de", "Sportschau",        "https://www.sportschau.de/index~rss2.xml"),
    ("fr", "L'Équipe Foot",     "https://www.lequipe.fr/rss/actu_rss_Football.xml"),
]
N_NEWS = 9

# Keywords that mark an item as World-Cup-relevant (used to prefer WC news,
# then back-fill with general football headlines).
WC_KEYWORDS = ("world cup", "worldcup", "wm 2026", "weltmeister", "wm-",
               " wm ", "coupe du monde", "mondial", "fifa")

TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")
TIME_RE = re.compile(r"(\d{1,2}):(\d{2})\s*UTC\s*([+-]\d{1,2})?", re.I)

socket.setdefaulttimeout(25)
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def _clean(text, limit=160):
    if not text:
        return ""
    import html as _html
    text = TAG_RE.sub(" ", text)
    text = _html.unescape(text)
    text = WS_RE.sub(" ", text).strip()
    if len(text) > limit:
        text = text[:limit].rsplit(" ", 1)[0] + "…"
    return text


def _kickoff_epoch(date_str, time_str):
    """Turn ('2026-06-13', '18:00 UTC-4') into a UTC epoch int.

    Falls back to 12:00 UTC on the given date if the time can't be parsed,
    and flags whether a real kickoff time was found.
    """
    try:
        y, mo, d = (int(x) for x in date_str.split("-"))
    except Exception:
        return None, False
    m = TIME_RE.search(time_str or "")
    if m:
        hh, mm = int(m.group(1)), int(m.group(2))
        off = int(m.group(3)) if m.group(3) else 0
        try:
            dt = datetime(y, mo, d, hh, mm, tzinfo=timezone(timedelta(hours=off)))
            return int(dt.timestamp()), True
        except Exception:
            pass
    # plain "19:00" with no UTC marker -> treat as UTC
    m2 = re.match(r"\s*(\d{1,2}):(\d{2})", time_str or "")
    if m2:
        try:
            dt = datetime(y, mo, d, int(m2.group(1)), int(m2.group(2)),
                          tzinfo=timezone.utc)
            return int(dt.timestamp()), True
        except Exception:
            pass
    dt = datetime(y, mo, d, 12, 0, tzinfo=timezone.utc)
    return int(dt.timestamp()), False


def _score_str(score):
    """Render an openfootball score object as e.g. '2–0', '1–1 (a.e.t.)',
    or '0–0 (pens 4–2)'. Returns (text, ft_list) or (None, None)."""
    if not isinstance(score, dict):
        return None, None
    ft = score.get("ft")
    if not (isinstance(ft, list) and len(ft) == 2):
        return None, None
    base = f"{ft[0]}–{ft[1]}"
    pens = score.get("p")
    if isinstance(pens, list) and len(pens) == 2:
        return f"{base} (pens {pens[0]}–{pens[1]})", ft
    if score.get("et"):
        return f"{base} (a.e.t.)", ft
    return base, ft


def _fetch_schedule():
    """Download and parse the openfootball 2026 schedule into match dicts."""
    raw = None
    if Request and urlopen:
        try:
            req = Request(SCHEDULE_URL, headers={"User-Agent": UA})
            with urlopen(req) as resp:
                raw = resp.read().decode("utf-8", "replace")
        except Exception as ex:
            print(f"  ! worldcup schedule: {ex}", file=sys.stderr)
            return []
    if not raw:
        return []
    try:
        doc = json.loads(raw)
    except Exception as ex:
        print(f"  ! worldcup schedule parse: {ex}", file=sys.stderr)
        return []

    matches = []
    for mt in doc.get("matches", []):
        ts, has_time = _kickoff_epoch(mt.get("date", ""), mt.get("time", ""))
        if ts is None:
            continue
        text, ft = _score_str(mt.get("score"))
        matches.append({
            "round": mt.get("round", ""),
            "group": mt.get("group", ""),
            "ground": mt.get("ground", ""),
            "team1": mt.get("team1", ""),
            "team2": mt.get("team2", ""),
            "ts": ts,
            "has_time": has_time,
            "score": text,        # None when not yet played
            "ft": ft,
        })
    return matches


def _classify(matches, now_ts):
    """Tag each match finished / live / upcoming and split into buckets."""
    live, today, results, upcoming = [], [], [], []
    today_paris = datetime.fromtimestamp(now_ts, PARIS).date()
    for m in matches:
        played = m["score"] is not None
        kicked = now_ts >= m["ts"]
        in_window = m["ts"] <= now_ts < m["ts"] + LIVE_WINDOW_MIN * 60
        m_date = datetime.fromtimestamp(m["ts"], PARIS).date()
        if played:
            m["status"] = "finished"
            results.append(m)
        elif in_window:
            m["status"] = "live"
            live.append(m)
        else:
            m["status"] = "upcoming"
            upcoming.append(m)
        if m_date == today_paris:
            m["today"] = True
            today.append(m)
        else:
            m["today"] = False
    results.sort(key=lambda x: x["ts"], reverse=True)   # newest result first
    upcoming.sort(key=lambda x: x["ts"])                 # soonest first
    today.sort(key=lambda x: x["ts"])
    live.sort(key=lambda x: x["ts"])
    return live, today, results, upcoming


def _current_stage(matches, now_ts):
    """Best guess at the active phase, for the header line."""
    future = [m for m in matches if m["ts"] >= now_ts]
    pool = future or matches
    nxt = min(pool, key=lambda x: abs(x["ts"] - now_ts)) if pool else None
    return nxt["round"] if nxt else ""


def _fetch_news(now_ts):
    items = []
    for lang, source, url in NEWS_FEEDS:
        try:
            d = feedparser.parse(url, agent=UA)
        except Exception as ex:
            print(f"  ! {source}: {ex}", file=sys.stderr)
            continue
        for e in d.entries[:12]:
            title = _clean(e.get("title", ""), 150)
            link = e.get("link", "")
            if not title or not link:
                continue
            ts = int(time.time())
            for key in ("published_parsed", "updated_parsed"):
                t = e.get(key)
                if t:
                    try:
                        ts = int(time.mktime(t))
                        break
                    except Exception:
                        pass
            blob = (title + " " + _clean(e.get("summary", ""), 200)).lower()
            wc = any(k in blob for k in WC_KEYWORDS)
            items.append({"title": title, "link": link, "source": source,
                          "lang": lang, "ts": ts, "wc": wc})
    # de-dupe on link / title
    seen, dedup = set(), []
    for it in items:
        key = (it["link"], it["title"].lower())
        if key in seen:
            continue
        seen.add(key)
        dedup.append(it)
    # prefer World-Cup items, newest first; then back-fill with general
    wc_items = sorted([i for i in dedup if i["wc"]], key=lambda x: x["ts"], reverse=True)
    rest = sorted([i for i in dedup if not i["wc"]], key=lambda x: x["ts"], reverse=True)
    chosen = (wc_items + rest)[:N_NEWS]
    return chosen


def fetch_worldcup(now=None):
    """Return the full World Cup bundle, or None if hidden / unavailable.

    Shape:
        {
          "stage": str,
          "played": int, "total": int,
          "live": [...], "today": [...],
          "results": [...], "upcoming": [...],
          "all": [ {phase, matches:[...]} , ... ],   # full schedule grouped
          "news": [...],
        }
    """
    now = now or datetime.now(PARIS)
    if now.date() >= HIDE_AFTER:
        print("  - worldcup: tournament over, section hidden", file=sys.stderr)
        return None

    now_ts = int(now.timestamp())
    matches = _fetch_schedule()
    if not matches:
        return None

    live, today, results, upcoming = _classify(matches, now_ts)
    played = len(results)
    total = len(matches)
    stage = _current_stage(matches, now_ts)

    # full schedule, grouped by phase in chronological order
    order, groups = [], {}
    for m in sorted(matches, key=lambda x: x["ts"]):
        phase = m["group"] or m["round"]
        if phase not in groups:
            groups[phase] = []
            order.append(phase)
        groups[phase].append(m)
    all_grouped = [{"phase": p, "matches": groups[p]} for p in order]

    news = _fetch_news(now_ts)

    print(f"  + worldcup: {played}/{total} played, {len(live)} live, "
          f"{len(today)} today, {len(news)} news", file=sys.stderr)

    return {
        "stage": stage,
        "played": played,
        "total": total,
        "live": live,
        "today": today,
        "results": results[:N_RESULTS],
        "upcoming": upcoming[:N_UPCOMING],
        "all": all_grouped,
        "news": news,
    }
