#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
World News Hub — static site generator.

Fetches RSS/Atom feeds defined in feeds.py, balances and de-duplicates the
items, and writes a single self-contained docs/index.html (no external
requests at runtime). Designed to be run hourly by a GitHub Actions cron.
"""

import html
import re
import socket
import sys
import time
from datetime import datetime, timezone

try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo("Europe/Paris")
except Exception:  # pragma: no cover
    TZ = timezone.utc

import feedparser

from feeds import CATEGORIES, ITEMS_PER_FEED, MAX_PER_CATEGORY

try:
    from worldcup import fetch_worldcup
except Exception:  # pragma: no cover - WC add-on is optional
    fetch_worldcup = lambda *a, **k: None

socket.setdefaulttimeout(25)
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

OUT = "docs/index.html"

TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")


def clean(text, limit=190):
    if not text:
        return ""
    text = TAG_RE.sub(" ", text)
    text = html.unescape(text)
    text = WS_RE.sub(" ", text).strip()
    if len(text) > limit:
        cut = text[:limit].rsplit(" ", 1)[0]
        text = cut + "\u2026"
    return text


def entry_ts(e):
    for key in ("published_parsed", "updated_parsed"):
        t = e.get(key)
        if t:
            try:
                return int(time.mktime(t))  # struct_time -> epoch (UTC-ish)
            except Exception:
                pass
    return int(time.time())


def fetch_category(cat):
    items = []
    for lang, source, url in cat["feeds"]:
        try:
            d = feedparser.parse(url, agent=UA)
        except Exception as ex:
            print(f"  ! {source}: {ex}", file=sys.stderr)
            continue
        n = len(d.entries)
        if not n:
            print(f"  - {source}: no entries (skipped)", file=sys.stderr)
            continue
        print(f"  + {source}: {n} entries", file=sys.stderr)
        for e in d.entries[:ITEMS_PER_FEED]:
            title = clean(e.get("title", ""), 160)
            link = e.get("link", "")
            if not title or not link:
                continue
            items.append({
                "title": title,
                "link": link,
                "summary": clean(e.get("summary", e.get("description", "")), 200),
                "source": source,
                "lang": lang,
                "ts": entry_ts(e),
            })
    # de-duplicate on link, then on lowered title
    seen_links, seen_titles, deduped = set(), set(), []
    for it in items:
        lt = it["title"].lower()
        if it["link"] in seen_links or lt in seen_titles:
            continue
        seen_links.add(it["link"])
        seen_titles.add(lt)
        deduped.append(it)

    # group by language, newest first within each language
    by_lang = {}
    for it in deduped:
        by_lang.setdefault(it["lang"], []).append(it)
    for q in by_lang.values():
        q.sort(key=lambda x: x["ts"], reverse=True)

    # round-robin across languages so no language gets crowded out by a
    # high-volume source in another language; recency is preserved within
    # each language. Languages cycled in en/de/fr order when present.
    queues = [by_lang[l] for l in ("en", "de", "fr") if by_lang.get(l)]
    out = []
    while queues and len(out) < MAX_PER_CATEGORY:
        still = []
        for q in queues:
            if len(out) >= MAX_PER_CATEGORY:
                break
            out.append(q.pop(0))
            if q:
                still.append(q)
        queues = still
    return out


# ---------------------------------------------------------------- UI strings
UI = {
    "en": {
        "tagline": "Hourly world news from trusted wire services & public broadcasters",
        "updated": "Updated", "all": "All", "sources": "Sources", "top": "Top Story",
        "auto": "This page rebuilds every hour and reloads itself automatically.",
        "trust": "Independent \u00b7 No ads \u00b7 No tracking \u00b7 Headlines link to the original source",
        "empty": "No items available right now \u2014 the next hourly build will refill this section.",
        "ago": "ago", "now": "just now",
        "u_m": "min", "u_h": "h", "u_d": "d",
        "datefmt": "%A, %d %B %Y \u00b7 %H:%M",
        "wc-title": "FIFA World Cup 2026",
        "wc-sub": "USA \u00b7 Canada \u00b7 Mexico \u00b7 11 Jun \u2013 19 Jul 2026",
        "wc-progress": "matches played",
        "wc-results": "Latest results", "wc-today": "Today & live",
        "wc-upcoming": "Upcoming", "wc-live": "LIVE",
        "wc-none-today": "No matches scheduled today.",
        "wc-none-up": "No upcoming matches.",
        "wc-none-res": "No results yet.",
        "wc-full": "Full schedule \u2014 all matches",
        "wc-news": "World Cup headlines",
        "wc-times": "Kick-off times shown in your local time (Europe/Paris).",
    },
    "de": {
        "tagline": "St\u00fcndliche Weltnachrichten von vertrauensw\u00fcrdigen Agenturen & \u00f6ffentlich-rechtlichen Sendern",
        "updated": "Aktualisiert", "all": "Alle", "sources": "Quellen", "top": "Top-Meldung",
        "auto": "Diese Seite wird st\u00fcndlich neu erzeugt und l\u00e4dt sich automatisch neu.",
        "trust": "Unabh\u00e4ngig \u00b7 Keine Werbung \u00b7 Kein Tracking \u00b7 Schlagzeilen verlinken zur Originalquelle",
        "empty": "Derzeit keine Eintr\u00e4ge \u2014 der n\u00e4chste st\u00fcndliche Lauf f\u00fcllt diesen Bereich.",
        "ago": "", "now": "gerade eben",
        "u_m": "Min.", "u_h": "Std.", "u_d": "T",
        "datefmt": "%A, %d. %B %Y \u00b7 %H:%M",
        "wc-title": "Fu\u00dfball-WM 2026",
        "wc-sub": "USA \u00b7 Kanada \u00b7 Mexiko \u00b7 11. Juni \u2013 19. Juli 2026",
        "wc-progress": "Spiele gespielt",
        "wc-results": "Neueste Ergebnisse", "wc-today": "Heute & live",
        "wc-upcoming": "Demn\u00e4chst", "wc-live": "LIVE",
        "wc-none-today": "Heute keine Spiele angesetzt.",
        "wc-none-up": "Keine anstehenden Spiele.",
        "wc-none-res": "Noch keine Ergebnisse.",
        "wc-full": "Kompletter Spielplan \u2014 alle Spiele",
        "wc-news": "WM-Schlagzeilen",
        "wc-times": "Ansto\u00dfzeiten in deiner Ortszeit (Europe/Paris).",
    },
    "fr": {
        "tagline": "Actualit\u00e9s mondiales horaires d'agences et de m\u00e9dias publics fiables",
        "updated": "Mis \u00e0 jour", "all": "Tout", "sources": "Sources", "top": "\u00c0 la une",
        "auto": "Cette page est reconstruite chaque heure et se recharge automatiquement.",
        "trust": "Ind\u00e9pendant \u00b7 Sans publicit\u00e9 \u00b7 Sans tra\u00e7age \u00b7 Les titres renvoient \u00e0 la source originale",
        "empty": "Aucun \u00e9l\u00e9ment pour le moment \u2014 la prochaine mise \u00e0 jour horaire remplira cette section.",
        "ago": "", "now": "\u00e0 l'instant",
        "u_m": "min", "u_h": "h", "u_d": "j",
        "datefmt": "%A %d %B %Y \u00b7 %H:%M",
        "wc-title": "Coupe du monde 2026",
        "wc-sub": "\u00c9tats-Unis \u00b7 Canada \u00b7 Mexique \u00b7 11 juin \u2013 19 juil. 2026",
        "wc-progress": "matches jou\u00e9s",
        "wc-results": "Derniers r\u00e9sultats", "wc-today": "Aujourd'hui & en direct",
        "wc-upcoming": "\u00c0 venir", "wc-live": "EN DIRECT",
        "wc-none-today": "Aucun match aujourd'hui.",
        "wc-none-up": "Aucun match \u00e0 venir.",
        "wc-none-res": "Pas encore de r\u00e9sultats.",
        "wc-full": "Calendrier complet \u2014 tous les matches",
        "wc-news": "Actu Coupe du monde",
        "wc-times": "Heures de coup d'envoi affich\u00e9es dans votre fuseau (Europe/Paris).",
    },
}


# ----------------------------------------------------------- World Cup block
def _wc_row(m):
    """One match row: localized kickoff time (filled by JS), teams + score."""
    e = html.escape
    status = m.get("status", "upcoming")
    if status == "finished" and m.get("score"):
        mid = f'<span class="wc-sc">{e(m["score"])}</span>'
    elif status == "live":
        mid = '<span class="wc-livechip" data-i18n="wc-live"></span>'
    else:
        mid = '<span class="wc-vs">–</span>'
    meta = " · ".join(x for x in (m.get("group", ""), m.get("ground", "")) if x)
    return (
        f'<div class="wc-m s-{status}">'
        f'<time class="wc-ts" data-ts="{m["ts"]}"></time>'
        f'<div class="wc-pair"><span class="wc-tn">{e(m["team1"])}</span>'
        f'{mid}<span class="wc-tn wc-tn-r">{e(m["team2"])}</span></div>'
        f'<div class="wc-meta">{e(meta)}</div></div>'
    )


def worldcup_section_html(wc):
    """Render the whole featured World Cup banner, or '' if there's no data."""
    if not wc:
        return ""
    e = html.escape

    def col(items, none_key):
        if not items:
            return f'<p class="wc-none" data-i18n="{none_key}"></p>'
        return "".join(_wc_row(m) for m in items)

    upcoming = [m for m in wc["upcoming"] if not m.get("today")]
    live_dot = '<span class="wc-live-dot"></span>' if wc["live"] else ""
    stage = f'<span class="wc-stage">{e(wc["stage"])}</span>' if wc.get("stage") else ""

    # full schedule grouped by phase
    phases = []
    for grp in wc["all"]:
        rows = "".join(_wc_row(m) for m in grp["matches"])
        phases.append(
            f'<div class="wc-phase"><h4>{e(grp["phase"])}</h4>{rows}</div>'
        )
    full = (
        '<details class="wc-full"><summary><span data-i18n="wc-full"></span></summary>'
        f'<div class="wc-full-body">{"".join(phases)}</div></details>'
    )

    # news cards reuse the standard .card markup so the language filter and
    # the "x min ago" timer apply to them automatically.
    news_cards = []
    for it in wc["news"]:
        news_cards.append(
            f'<article class="card" data-lang="{it["lang"]}" data-ts="{it["ts"]}">'
            f'<div class="meta"><span class="src">{e(it["source"])}</span>'
            f'<span class="lang l-{it["lang"]}">{it["lang"].upper()}</span>'
            f'<time class="ago" data-ts="{it["ts"]}"></time></div>'
            f'<h3><a href="{e(it["link"])}" target="_blank" rel="noopener noreferrer">{e(it["title"])}</a></h3>'
            f'</article>'
        )
    news = (
        '<div class="wc-news"><h3 data-i18n="wc-news"></h3>'
        f'<div class="grid">{"".join(news_cards)}</div></div>'
    ) if news_cards else ""

    return (
        '<section id="worldcup" class="wc">'
        '<div class="wc-head">'
        '<div class="wc-title"><span class="wc-ball">⚽</span>'
        '<span data-i18n="wc-title"></span></div>'
        '<div class="wc-sub" data-i18n="wc-sub"></div>'
        f'<div class="wc-prog">{live_dot}{stage}'
        f'<span><b>{wc["played"]}</b>/{wc["total"]} '
        '<span data-i18n="wc-progress"></span></span></div>'
        '</div>'
        '<div class="wc-cols">'
        '<div class="wc-col"><h3 data-i18n="wc-results"></h3>'
        f'{col(wc["results"], "wc-none-res")}</div>'
        '<div class="wc-col"><h3 data-i18n="wc-today"></h3>'
        f'{col(wc["today"], "wc-none-today")}</div>'
        '<div class="wc-col"><h3 data-i18n="wc-upcoming"></h3>'
        f'{col(upcoming, "wc-none-up")}</div>'
        '</div>'
        f'{full}'
        '<p class="wc-times" data-i18n="wc-times"></p>'
        f'{news}'
        '</section>'
    )


def pick_lead(pool, lang=None):
    """Newest story, preferring the World/Politics/Business front page."""
    cand = [it for it in pool if (lang is None or it["lang"] == lang)]
    if not cand:
        return None
    front = [it for it in cand if it["cat"] == "world"]
    return max(front or cand, key=lambda x: x["ts"])


def lead_card_html(L):
    if not L:
        return '<a class="lead" id="lead" style="display:none"></a>'
    e = html.escape
    return (
        f'<a class="lead" id="lead" href="{e(L["link"])}" target="_blank" '
        f'rel="noopener noreferrer" data-lang="{L["lang"]}" style="--c:{L["accent"]}">'
        f'<span class="lead-badge" data-i18n="top"></span>'
        f'<div class="lead-meta"><span class="src">{e(L["source"])}</span>'
        f'<span class="lang">{L["lang"].upper()}</span>'
        f'<time class="ago" data-ts="{L["ts"]}"></time></div>'
        f'<h2 class="lead-title">{e(L["title"])}</h2>'
        f'<p class="lead-sum">{e(L["summary"])}</p></a>'
    )


def render(data, built_at, wc=None):
    e = html.escape
    iso = built_at.astimezone(timezone.utc).isoformat()

    # flat pool tagged with category id + accent, for top-story selection
    pool = []
    for c in data:
        for it in c["items"]:
            pool.append({**it, "cat": c["id"], "accent": c["accent"]})
    leads = {"all": pick_lead(pool), "en": pick_lead(pool, "en"),
             "de": pick_lead(pool, "de"), "fr": pick_lead(pool, "fr")}
    lead_all = leads["all"]
    lead_link = lead_all["link"] if lead_all else None

    nav = "".join(
        f'<a href="#{c["id"]}" style="--c:{c["accent"]}">'
        f'<span data-i18n="cat-{c["id"]}">{e(c["title"]["en"])}</span></a>'
        for c in data
    )

    sections = []
    for c in data:
        cards = []
        for it in c["items"]:
            if lead_link and it["link"] == lead_link:
                continue  # the hero already features this story
            summ = f'<p class="sm">{e(it["summary"])}</p>' if it["summary"] else ""
            cards.append(
                f'<article class="card" data-lang="{it["lang"]}" data-ts="{it["ts"]}">'
                f'<div class="meta"><span class="src">{e(it["source"])}</span>'
                f'<span class="lang l-{it["lang"]}">{it["lang"].upper()}</span>'
                f'<time class="ago" data-ts="{it["ts"]}"></time></div>'
                f'<h3><a href="{e(it["link"])}" target="_blank" rel="noopener noreferrer">{e(it["title"])}</a></h3>'
                f'{summ}</article>'
            )
        srcs = " \u00b7 ".join(sorted({f["1"] if isinstance(f, dict) else f[1] for f in c["feeds"]}))
        body = "".join(cards) if cards else f'<p class="empty" data-i18n="empty"></p>'
        sections.append(
            f'<section id="{c["id"]}" class="cat" style="--c:{c["accent"]}">'
            f'<div class="cat-head"><h2 data-i18n="cat-{c["id"]}">{e(c["title"]["en"])}</h2>'
            f'<span class="cat-src">{e(srcs)}</span></div>'
            f'<div class="grid">{body}</div></section>'
        )

    # title translations as JSON-ish for the language switcher
    cat_titles = {c["id"]: c["title"] for c in data}
    import json
    cat_json = json.dumps(cat_titles, ensure_ascii=False)
    ui_json = json.dumps(UI, ensure_ascii=False)
    leads_clean = {k: ({"title": v["title"], "link": v["link"],
                        "summary": v["summary"], "source": v["source"],
                        "lang": v["lang"], "ts": v["ts"], "accent": v["accent"]}
                       if v else None) for k, v in leads.items()}
    leads_json = json.dumps(leads_clean, ensure_ascii=False)

    return TEMPLATE.format(
        nav=nav,
        worldcup=worldcup_section_html(wc),
        lead=lead_card_html(lead_all),
        sections="".join(sections),
        iso=iso,
        cat_json=cat_json,
        ui_json=ui_json,
        leads_json=leads_json,
    )


TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="index,follow">
<title>World News Hub \u2014 hourly, categorised, trusted sources</title>
<meta name="description" content="World news updated every hour from trusted wire services and public broadcasters. Categorised, multilingual (EN/DE/FR), no ads, no tracking.">
<style>
:root{{
  --paper:#f6f2ea; --ink:#1c1a17; --muted:#6f6a62; --line:#d9d2c5;
  --card:#fffdf8; --accent:#a3261f; --maxw:1180px;
}}
*{{box-sizing:border-box;margin:0;padding:0}}
html{{scroll-behavior:smooth}}
body{{
  background:var(--paper); color:var(--ink);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  line-height:1.5; -webkit-font-smoothing:antialiased;
  background-image:radial-gradient(circle at 1px 1px, rgba(0,0,0,.025) 1px, transparent 0);
  background-size:22px 22px;
}}
.wrap{{max-width:var(--maxw);margin:0 auto;padding:0 22px}}
a{{color:inherit}}
/* ---- masthead ---- */
header.mast{{border-bottom:3px double var(--ink);background:var(--paper);
  position:sticky;top:0;z-index:30;backdrop-filter:saturate(1.1) blur(2px)}}
.mast-top{{display:flex;align-items:flex-end;justify-content:space-between;
  gap:18px;padding:14px 0 10px;flex-wrap:wrap}}
.brand{{font-family:Georgia,"Times New Roman",serif;font-weight:700;
  font-size:clamp(28px,5vw,46px);letter-spacing:-.5px;line-height:1}}
.brand .dot{{color:var(--accent)}}
.tagline{{font-size:13px;color:var(--muted);max-width:48ch;margin-top:6px}}
.clock{{text-align:right;font-family:ui-monospace,"SFMono-Regular",Menlo,Consolas,monospace;
  font-size:12px;color:var(--muted);line-height:1.7;white-space:nowrap}}
.clock b{{color:var(--ink)}}
.live{{display:inline-block;width:8px;height:8px;border-radius:50%;
  background:#cf3b2c;margin-right:5px;animation:pulse 2s infinite}}
@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:.25}}}}
/* ---- controls row ---- */
.controls{{display:flex;align-items:center;justify-content:space-between;
  gap:14px;border-top:1px solid var(--line);padding:8px 0;flex-wrap:wrap}}
nav.cats{{display:flex;gap:4px;flex-wrap:wrap}}
nav.cats a{{font-size:12.5px;font-weight:600;text-decoration:none;padding:5px 10px;
  border-radius:999px;border:1px solid var(--line);color:var(--ink);
  display:inline-flex;align-items:center;gap:6px;transition:.15s}}
nav.cats a::before{{content:"";width:8px;height:8px;border-radius:50%;background:var(--c)}}
nav.cats a:hover{{background:var(--ink);color:var(--paper);border-color:var(--ink)}}
.langsw{{display:flex;gap:4px}}
.langsw button{{font:600 12.5px/1 inherit;cursor:pointer;border:1px solid var(--line);
  background:var(--card);color:var(--ink);padding:6px 11px;border-radius:7px;transition:.15s}}
.langsw button.on{{background:var(--ink);color:var(--paper);border-color:var(--ink)}}
/* ---- lead / top story ---- */
.lead{{display:block;text-decoration:none;background:var(--card);
  border:1px solid var(--line);border-top:5px solid var(--c);border-radius:5px;
  padding:22px 26px 24px;margin:26px 0 32px;position:relative;
  box-shadow:0 12px 34px -20px rgba(0,0,0,.55);transition:transform .14s, box-shadow .14s}}
.lead:hover{{transform:translateY(-2px);box-shadow:0 18px 40px -22px rgba(0,0,0,.6)}}
.lead-badge{{display:inline-block;background:var(--c);color:#fff;font-size:10.5px;
  font-weight:700;letter-spacing:1.8px;text-transform:uppercase;padding:4px 11px;
  border-radius:3px;margin-bottom:13px}}
.lead-meta{{display:flex;align-items:center;gap:10px;font-size:11.5px;color:var(--muted);
  text-transform:uppercase;letter-spacing:.4px;margin-bottom:9px}}
.lead-meta .src{{font-weight:700;color:var(--c)}}
.lead-meta .lang{{border:1px solid var(--line);border-radius:3px;padding:1px 5px;font-size:9.5px}}
.lead-meta .ago{{margin-left:auto;font-variant-numeric:tabular-nums}}
.lead-title{{font-family:Georgia,"Times New Roman",serif;font-weight:700;
  font-size:clamp(24px,4.2vw,40px);line-height:1.12;letter-spacing:-.6px;color:var(--ink)}}
.lead:hover .lead-title{{text-decoration:underline;text-decoration-color:var(--c);text-underline-offset:3px}}
.lead-sum{{font-size:15.5px;color:#46423b;margin-top:11px;max-width:72ch;line-height:1.5}}
.lead-sum:empty{{display:none}}
/* ---- categories ---- */
main{{padding:26px 0 10px}}
.cat{{margin-bottom:34px;scroll-margin-top:140px}}
.cat-head{{display:flex;align-items:baseline;gap:12px;border-bottom:2px solid var(--c);
  padding-bottom:6px;margin-bottom:16px;flex-wrap:wrap}}
.cat-head h2{{font-family:Georgia,"Times New Roman",serif;font-size:clamp(20px,3vw,27px);
  color:var(--c);letter-spacing:-.3px}}
.cat-src{{font-size:11px;color:var(--muted);margin-left:auto;letter-spacing:.2px}}
.grid{{display:grid;gap:14px;grid-template-columns:repeat(auto-fill,minmax(290px,1fr))}}
.card{{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--c);
  border-radius:4px;padding:14px 15px;display:flex;flex-direction:column;gap:7px;
  transition:transform .12s, box-shadow .12s}}
.card:hover{{transform:translateY(-2px);box-shadow:0 8px 22px -12px rgba(0,0,0,.4)}}
.card .meta{{display:flex;align-items:center;gap:8px;font-size:11px;color:var(--muted);
  text-transform:uppercase;letter-spacing:.4px}}
.card .src{{font-weight:700;color:var(--c)}}
.card .lang{{font-size:9.5px;font-weight:700;border:1px solid var(--line);border-radius:3px;
  padding:1px 4px;letter-spacing:.5px}}
.card .ago{{margin-left:auto;font-variant-numeric:tabular-nums}}
.card h3{{font-family:Georgia,"Times New Roman",serif;font-size:16.5px;line-height:1.3;font-weight:600}}
.card h3 a{{text-decoration:none}}
.card h3 a:hover{{text-decoration:underline;text-decoration-color:var(--c)}}
.card .sm{{font-size:13px;color:#46423b;line-height:1.45}}
.empty{{color:var(--muted);font-style:italic;padding:8px 2px}}
/* ---- World Cup featured block ---- */
.wc{{--c:#15803d;background:linear-gradient(180deg,#0f3d24,#123f27);color:#eafbf0;
  border-radius:7px;padding:20px 22px 22px;margin:26px 0 30px;
  box-shadow:0 16px 40px -22px rgba(0,0,0,.7)}}
.wc a{{color:#eafbf0}}
.wc-head{{display:flex;flex-wrap:wrap;align-items:baseline;gap:8px 16px;
  border-bottom:1px solid rgba(255,255,255,.2);padding-bottom:12px;margin-bottom:16px}}
.wc-title{{font-family:Georgia,"Times New Roman",serif;font-weight:700;
  font-size:clamp(20px,3.4vw,30px);letter-spacing:-.4px;display:flex;align-items:center;gap:9px}}
.wc-ball{{font-size:.9em}}
.wc-sub{{font-size:13px;color:#bfe6cd}}
.wc-prog{{margin-left:auto;font-size:12.5px;color:#bfe6cd;display:flex;
  align-items:center;gap:9px;flex-wrap:wrap}}
.wc-prog b{{color:#fff}}
.wc-stage{{background:rgba(255,255,255,.12);border-radius:999px;padding:2px 10px;
  font-weight:600;color:#fff}}
.wc-live-dot{{display:inline-block;width:9px;height:9px;border-radius:50%;
  background:#ff5b4a;animation:wcpulse 1.6s infinite}}
@keyframes wcpulse{{0%{{box-shadow:0 0 0 0 rgba(255,91,74,.6)}}70%{{box-shadow:0 0 0 8px rgba(255,91,74,0)}}100%{{box-shadow:0 0 0 0 rgba(255,91,74,0)}}}}
.wc-cols{{display:grid;gap:16px;grid-template-columns:repeat(auto-fit,minmax(248px,1fr))}}
.wc-col h3{{font-size:11.5px;text-transform:uppercase;letter-spacing:1.2px;
  color:#9ddcb3;margin-bottom:10px;font-weight:700}}
.wc-m{{background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.1);
  border-left:3px solid var(--c);border-radius:5px;padding:8px 11px;margin-bottom:8px}}
.wc-m.s-live{{border-left-color:#ff5b4a;background:rgba(255,91,74,.13)}}
.wc-ts{{font-size:10.5px;color:#9ddcb3;text-transform:uppercase;letter-spacing:.5px;
  font-variant-numeric:tabular-nums;display:block;margin-bottom:4px}}
.wc-pair{{display:grid;grid-template-columns:1fr auto 1fr;align-items:center;gap:8px}}
.wc-tn{{font-weight:600;font-size:14px;line-height:1.2}}
.wc-tn-r{{text-align:right}}
.wc-sc{{font-family:Georgia,serif;font-weight:700;font-size:16px;color:#fff;
  background:rgba(0,0,0,.28);border-radius:4px;padding:1px 9px;
  font-variant-numeric:tabular-nums;white-space:nowrap}}
.wc-vs{{color:#7fbf99;font-size:13px}}
.wc-livechip{{background:#ff5b4a;color:#fff;font-size:9.5px;font-weight:700;
  letter-spacing:.8px;padding:3px 7px;border-radius:3px;white-space:nowrap}}
.wc-meta{{font-size:10.5px;color:#8fcfa6;margin-top:4px}}
.wc-none{{font-size:13px;color:#9ddcb3;font-style:italic;padding:6px 2px}}
.wc-full{{margin-top:16px;border-top:1px solid rgba(255,255,255,.18);padding-top:12px}}
.wc-full summary{{cursor:pointer;font-size:13px;font-weight:600;color:#cdeed8;list-style:none}}
.wc-full summary::-webkit-details-marker{{display:none}}
.wc-full summary::before{{content:"▸ ";color:#9ddcb3}}
.wc-full[open] summary::before{{content:"▾ "}}
.wc-full-body{{display:grid;gap:14px;margin-top:12px;
  grid-template-columns:repeat(auto-fill,minmax(238px,1fr))}}
.wc-phase h4{{font-size:11px;text-transform:uppercase;letter-spacing:1px;color:#9ddcb3;
  margin-bottom:6px;border-bottom:1px solid rgba(255,255,255,.12);padding-bottom:3px}}
.wc-times{{font-size:11px;color:#7fbf99;margin-top:12px;font-style:italic}}
.wc-news{{margin-top:16px;border-top:1px solid rgba(255,255,255,.18);padding-top:14px}}
.wc-news>h3{{font-size:11.5px;text-transform:uppercase;letter-spacing:1.2px;
  color:#9ddcb3;margin-bottom:10px;font-weight:700}}
.wc-news .grid{{display:grid;gap:12px;grid-template-columns:repeat(auto-fill,minmax(250px,1fr))}}
.wc-news .card{{background:rgba(255,255,255,.07);border-color:rgba(255,255,255,.12);
  border-left-color:var(--c)}}
.wc-news .card:hover{{box-shadow:0 8px 22px -12px rgba(0,0,0,.6)}}
.wc-news .card .src{{color:#9ddcb3}}
.wc-news .card .meta{{color:#8fcfa6}}
.wc-news .card h3 a{{color:#fff}}
.wc-news .card .lang{{border-color:rgba(255,255,255,.25)}}
/* ---- footer ---- */
footer{{border-top:3px double var(--ink);margin-top:24px;padding:20px 0 40px;
  font-size:12.5px;color:var(--muted);text-align:center}}
footer .trust{{font-weight:600;color:var(--ink)}}
footer .auto{{margin-top:6px}}
@media(max-width:560px){{.clock{{text-align:left}}.cat-src{{display:none}}}}
</style>
</head>
<body>
<header class="mast">
  <div class="wrap">
    <div class="mast-top">
      <div>
        <div class="brand">World News<span class="dot">.</span>Hub</div>
        <div class="tagline" data-i18n="tagline"></div>
      </div>
      <div class="clock">
        <div><span class="live"></span><span data-i18n="updated"></span>: <b id="built"></b></div>
        <div id="since"></div>
      </div>
    </div>
    <div class="controls">
      <nav class="cats">{nav}</nav>
      <div class="langsw" id="langsw">
        <button data-l="all" class="on" data-i18n="all"></button>
        <button data-l="en">EN</button>
        <button data-l="de">DE</button>
        <button data-l="fr">FR</button>
      </div>
    </div>
  </div>
</header>

<main class="wrap">{worldcup}{lead}{sections}</main>

<footer class="wrap">
  <div class="trust" data-i18n="trust"></div>
  <div class="auto" data-i18n="auto"></div>
</footer>

<script>
const BUILT_ISO = "{iso}";
const CATS = {cat_json};
const UI = {ui_json};
const LEADS = {leads_json};
let uiLang = "en";   // chrome language
let filter = "all";  // article language filter
let leadLink = null; // currently-featured story (to avoid grid duplication)

function setLead(){{
  const el = document.getElementById("lead");
  if(!el) return;
  const data = LEADS[filter] || (filter==="all" ? LEADS["all"] : null);
  if(!data){{ el.style.display = "none"; leadLink = null; return; }}
  leadLink = data.link;
  el.style.display = "";
  el.href = data.link;
  el.dataset.lang = data.lang;
  el.style.setProperty("--c", data.accent);
  el.querySelector(".src").textContent = data.source;
  el.querySelector(".lang").textContent = data.lang.toUpperCase();
  el.querySelector("time.ago").dataset.ts = data.ts;
  el.querySelector(".lead-title").textContent = data.title;
  el.querySelector(".lead-sum").textContent = data.summary || "";
}}

function applyI18n(){{
  const t = UI[uiLang];
  document.documentElement.lang = uiLang;
  document.querySelectorAll("[data-i18n]").forEach(el=>{{
    const k = el.getAttribute("data-i18n");
    if(k.startsWith("cat-")){{
      const id = k.slice(4);
      if(CATS[id]) el.textContent = CATS[id][uiLang] || CATS[id]["en"];
    }} else if(t[k]!==undefined){{
      el.textContent = t[k];
    }}
  }});
  document.getElementById("built").textContent = fmtBuilt();
  updateAgos();
  updateMatchTimes();
}}

function fmtMatch(ts){{
  const d = new Date(ts*1000);
  const loc = {{en:"en-GB", de:"de-DE", fr:"fr-FR"}}[uiLang];
  return d.toLocaleString(loc, {{weekday:"short",day:"2-digit",month:"short",
    hour:"2-digit",minute:"2-digit",timeZone:"Europe/Paris"}});
}}
function updateMatchTimes(){{
  document.querySelectorAll("time.wc-ts").forEach(el=>{{
    el.textContent = fmtMatch(parseInt(el.dataset.ts,10));
  }});
}}

function fmtBuilt(){{
  const d = new Date(BUILT_ISO);
  const loc = {{en:"en-GB", de:"de-DE", fr:"fr-FR"}}[uiLang];
  return d.toLocaleString(loc, {{weekday:"long",day:"2-digit",month:"long",
    year:"numeric",hour:"2-digit",minute:"2-digit"}});
}}

function rel(ts){{
  const t = UI[uiLang];
  const s = Math.max(0, Math.floor(Date.now()/1000 - ts));
  if(s < 60) return t.now;
  const m = Math.floor(s/60);
  if(m < 60) return label(m, t.u_m, t);
  const h = Math.floor(m/60);
  if(h < 24) return label(h, t.u_h, t);
  return label(Math.floor(h/24), t.u_d, t);
}}
function label(n, unit, t){{
  if(uiLang==="de") return "vor " + n + " " + unit;
  if(uiLang==="fr") return "il y a " + n + " " + unit;
  return n + " " + unit + " " + t.ago;
}}

function updateAgos(){{
  document.querySelectorAll("time.ago").forEach(el=>{{
    el.textContent = rel(parseInt(el.dataset.ts,10));
  }});
  const t = UI[uiLang];
  const mins = Math.floor((Date.now() - new Date(BUILT_ISO))/60000);
  const since = document.getElementById("since");
  since.textContent = mins<=0 ? t.now : (label(mins, t.u_m, t));
}}

function applyFilter(){{
  document.querySelectorAll(".card").forEach(c=>{{
    const langOk = (filter==="all" || c.dataset.lang===filter);
    const a = c.querySelector("h3 a");
    const isLead = leadLink && a && a.getAttribute("href")===leadLink;
    c.style.display = (langOk && !isLead) ? "" : "none";
  }});
  document.querySelectorAll("section.cat").forEach(sec=>{{
    const any = [...sec.querySelectorAll(".card")].some(c=>c.style.display!=="none");
    const hasCards = sec.querySelector(".card");
    sec.style.display = (!hasCards || any) ? "" : "none";
  }});
}}

document.getElementById("langsw").addEventListener("click", e=>{{
  const b = e.target.closest("button"); if(!b) return;
  document.querySelectorAll("#langsw button").forEach(x=>x.classList.remove("on"));
  b.classList.add("on");
  filter = b.dataset.l;
  if(filter!=="all") uiLang = filter;        // switch chrome to chosen language
  setLead(); applyI18n(); applyFilter();
}});

setLead();
applyI18n();
applyFilter();
setInterval(updateAgos, 60*1000);                 // refresh "x min ago"
setTimeout(()=>location.reload(), 60*60*1000);    // pick up the next hourly build
</script>
</body>
</html>"""


def main():
    built_at = datetime.now(TZ)
    print(f"Building World News Hub @ {built_at.isoformat()}", file=sys.stderr)
    data = []
    for cat in CATEGORIES:
        print(f"[{cat['id']}]", file=sys.stderr)
        items = fetch_category(cat)
        print(f"  = {len(items)} items kept", file=sys.stderr)
        data.append({**cat, "items": items})

    total = sum(len(c["items"]) for c in data)
    if total == 0:
        print("WARNING: no items fetched at all (network blocked?)", file=sys.stderr)

    print("[worldcup]", file=sys.stderr)
    try:
        wc = fetch_worldcup(built_at)
    except Exception as ex:
        print(f"  ! worldcup add-on failed: {ex}", file=sys.stderr)
        wc = None

    html_out = render(data, built_at, wc)
    import os
    os.makedirs("docs", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html_out)
    print(f"Wrote {OUT} ({total} items across {len(data)} categories)", file=sys.stderr)


if __name__ == "__main__":
    main()
