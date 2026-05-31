# -*- coding: utf-8 -*-
"""
Curated, reliable news sources for World News Hub.

Each feed: (lang, source_name, url)
lang is one of: "en", "de", "fr"

Sources are major wire services / public broadcasters and respected
specialist outlets. Note on Reuters & AP: neither offers a usable public
RSS feed anymore (Reuters discontinued theirs ~2020; AP has none), so
their wire-service tier is covered here by BBC, Al Jazeera, The Guardian,
NPR, DW, France24, tagesschau, Le Monde and RFI instead.

The generator skips any feed that is unreachable or empty, so the list can
safely include feeds that a restricted network might block.
"""

CATEGORIES = [
    {
        "id": "world",
        "accent": "#a3261f",
        "title": {"en": "World, Politics & Business",
                  "de": "Welt, Politik & Wirtschaft",
                  "fr": "Monde, Politique & Économie"},
        "feeds": [
            ("en", "BBC World",        "http://feeds.bbci.co.uk/news/world/rss.xml"),
            ("en", "BBC Business",     "http://feeds.bbci.co.uk/news/business/rss.xml"),
            ("en", "Al Jazeera",       "https://www.aljazeera.com/xml/rss/all.xml"),
            ("en", "The Guardian",     "https://www.theguardian.com/world/rss"),
            ("en", "NPR News",         "https://feeds.npr.org/1001/rss.xml"),
            ("de", "tagesschau",       "https://www.tagesschau.de/index~rss2.xml"),
            ("de", "DW Deutsch",       "https://rss.dw.com/rdf/rss-de-all"),
            ("de", "ZEIT Online",      "https://newsfeed.zeit.de/index"),
            ("de", "Der Spiegel",      "https://www.spiegel.de/schlagzeilen/tops/index.rss"),
            ("de", "S\u00fcddeutsche",      "https://rss.sueddeutsche.de/rss/Topthemen"),
            ("de", "n-tv",             "https://www.n-tv.de/rss"),
            ("de", "Tagesspiegel",     "https://www.tagesspiegel.de/contentexport/feed/home"),
            ("fr", "France 24",        "https://www.france24.com/fr/rss"),
            ("fr", "Le Monde",         "https://www.lemonde.fr/rss/une.xml"),
            ("fr", "RFI",              "https://www.rfi.fr/fr/rss"),
        ],
    },
    {
        "id": "tech",
        "accent": "#2f4b7c",
        "title": {"en": "Technology & AI",
                  "de": "Technologie & KI",
                  "fr": "Technologie & IA"},
        "feeds": [
            ("en", "BBC Technology",   "http://feeds.bbci.co.uk/news/technology/rss.xml"),
            ("en", "Ars Technica",     "https://feeds.arstechnica.com/arstechnica/index"),
            ("en", "The Verge",        "https://www.theverge.com/rss/index.xml"),
            ("en", "MIT Tech Review",  "https://www.technologyreview.com/feed/"),
            ("de", "heise online",     "https://www.heise.de/rss/heise-atom.xml"),
            ("de", "t3n",              "https://t3n.de/rss.xml"),
            ("de", "Golem",            "https://rss.golem.de/rss.php?feed=RSS2.0"),
            ("de", "Netzpolitik",      "https://netzpolitik.org/feed/"),
            ("fr", "Numerama",         "https://www.numerama.com/feed/"),
        ],
    },
    {
        "id": "science",
        "accent": "#1f7a5a",
        "title": {"en": "Science & Health",
                  "de": "Wissenschaft & Gesundheit",
                  "fr": "Science & Santé"},
        "feeds": [
            ("en", "BBC Science",      "http://feeds.bbci.co.uk/news/science_and_environment/rss.xml"),
            ("en", "BBC Health",       "http://feeds.bbci.co.uk/news/health/rss.xml"),
            ("en", "ScienceDaily",     "https://www.sciencedaily.com/rss/all.xml"),
            ("en", "Nature",           "https://www.nature.com/nature.rss"),
            ("de", "Spektrum",         "https://www.spektrum.de/alias/rss/spektrum-de-rss-feed/996406"),
            ("de", "wissenschaft.de",  "https://www.wissenschaft.de/feed/"),
            ("de", "scinexx",          "https://www.scinexx.de/feed/"),
            ("de", "\u00c4rzteblatt",       "https://www.aerzteblatt.de/rss/news.asp"),
            ("fr", "Futura Sciences",  "https://www.futura-sciences.com/rss/actualites.xml"),
        ],
    },
    {
        "id": "finance",
        "accent": "#9a6b00",
        "title": {"en": "Financial Information",
                  "de": "Finanzinformationen",
                  "fr": "Informations Financières"},
        "feeds": [
            ("en", "CNBC",             "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114"),
            ("en", "MarketWatch",      "http://feeds.marketwatch.com/marketwatch/topstories/"),
            ("en", "Yahoo Finance",    "https://finance.yahoo.com/news/rssindex"),
            ("en", "Investing.com",    "https://www.investing.com/rss/news.rss"),
            ("en", "Financial Times",  "https://www.ft.com/rss/home"),
            ("de", "Handelsblatt",     "https://www.handelsblatt.com/contentexport/feed/schlagzeilen"),
            ("de", "finanzen.net",     "https://www.finanzen.net/rss/news"),
            ("de", "manager magazin",  "https://www.manager-magazin.de/news/index.rss"),
            ("de", "WirtschaftsWoche", "https://www.wiwo.de/contentexport/feed/rss/schlagzeilen"),
            ("fr", "Les Échos",        "https://services.lesechos.fr/rss/les-echos-economie.xml"),
        ],
    },
    {
        "id": "sports",
        "accent": "#6a3d8a",
        "title": {"en": "Sports, Sim Racing & 3D Printing",
                  "de": "Sport, Sim Racing & 3D-Druck",
                  "fr": "Sport, Sim Racing & Impression 3D"},
        "feeds": [
            ("en", "BBC Sport",        "http://feeds.bbci.co.uk/sport/rss.xml"),
            ("en", "Traxion",          "https://traxion.gg/feed/"),
            ("en", "OverTake",         "https://www.overtake.gg/news/index.rss"),
            ("en", "3DPrint.com",      "https://3dprint.com/feed/"),
            ("en", "All3DP",           "https://all3dp.com/feed/"),
            ("en", "Hackaday",         "https://hackaday.com/blog/feed/"),
            ("de", "Sportschau",       "https://www.sportschau.de/index~rss2.xml"),
            ("de", "kicker",           "https://newsfeed.kicker.de/news/aktuell"),
            ("de", "3D-grenzenlos",    "https://www.3d-grenzenlos.de/feed/"),
            ("de", "3Druck.com",       "https://3druck.com/feed/"),
        ],
    },
]

# How many items to pull per individual feed (keeps any single prolific
# source from dominating a category).
ITEMS_PER_FEED = 5
# Hard cap on cards shown per category (selection is balanced across
# languages first, then filled by recency).
MAX_PER_CATEGORY = 30
