from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from app.logging_config import get_logger
from app.models.geopol_event import GeoPolEvent

logger = get_logger(__name__)

SECTOR_KEYWORDS: Dict[str, List[str]] = {
    "energy": ["oil", "gas", "petroleum", "energy", "renewable", "solar", "wind", "nuclear", "coal", "opec", "crude", "refinery", "pipeline", "fracking"],
    "defense": ["military", "defense", "weapon", "arms", "army", "navy", "air force", "missile", "munitions", "soldier", "tank", "naval", "aircraft", "drone", "artillery"],
    "technology": ["tech", "semiconductor", "software", "cyber", "ai", "artificial intelligence", "chip", "silicon", "data", "computing", "encryption", "hack", "cyberattack"],
    "finance": ["bank", "financial", "market", "stock", "bond", "treasury", "interest rate", "inflation", "central bank", "monetary", "fiscal", "debt", "deficit", "currency", "forex"],
    "healthcare": ["health", "medical", "pharma", "drug", "vaccine", "hospital", "pandemic", "epidemic", "disease", "clinical", "biotech", "covid"],
    "commodities": ["gold", "silver", "copper", "wheat", "corn", "commodity", "steel", "aluminum", "lithium", "rare earth", "mineral", "mining"],
    "transportation": ["shipping", "airline", "logistics", "supply chain", "port", "rail", "freight", "cargo", "maritime", "shipping lane", "chokepoint"],
    "agriculture": ["agriculture", "farm", "crop", "food supply", "fertilizer", "grain", "livestock", "fishery", "food security"],
    "real_estate": ["real estate", "housing", "property", "mortgage", "commercial real estate", "construction"],
    "telecommunications": ["telecom", "5g", "broadband", "network", "wireless", "fiber", "satellite"],
}

COUNTRY_ALIASES: Dict[str, str] = {
    "usa": "United States",
    "u.s.": "United States",
    "united states of america": "United States",
    "america": "United States",
    "uk": "United Kingdom",
    "britain": "United Kingdom",
    "u.k.": "United Kingdom",
    "uae": "United Arab Emirates",
    "russia": "Russian Federation",
    "china": "People's Republic of China",
    "prc": "People's Republic of China",
    "dprk": "North Korea",
    "south korea": "Republic of Korea",
    "iran": "Islamic Republic of Iran",
}

KNOWN_COUNTRIES: List[str] = [
    "United States", "China", "Russia", "United Kingdom", "Germany", "France",
    "Japan", "India", "Brazil", "Canada", "Australia", "South Korea", "North Korea",
    "Iran", "Israel", "Saudi Arabia", "Turkey", "Ukraine", "Poland", "Spain",
    "Italy", "Netherlands", "Sweden", "Norway", "Finland", "Denmark", "Switzerland",
    "Austria", "Belgium", "Ireland", "Portugal", "Greece", "Czech Republic",
    "Romania", "Hungary", "Bulgaria", "Serbia", "Croatia", "Slovakia", "Slovenia",
    "Lithuania", "Latvia", "Estonia", "Iraq", "Syria", "Afghanistan", "Pakistan",
    "Indonesia", "Malaysia", "Philippines", "Vietnam", "Thailand", "Taiwan",
    "South Africa", "Nigeria", "Egypt", "Kenya", "Argentina", "Chile", "Colombia",
    "Mexico", "Venezuela", "Cuba", "Qatar", "Kuwait", "Oman", "Bahrain", "Jordan",
    "Lebanon", "Yemen", "Libya", "Algeria", "Morocco", "Sudan", "Ethiopia",
    "Somalia", "Angola", "Mozambique", "Kazakhstan", "Uzbekistan", "Azerbaijan",
    "Armenia", "Georgia", "Belarus", "Moldova", "Myanmar", "Cambodia", "Laos",
    "Bangladesh", "Sri Lanka", "Nepal", "Mongolia", "European Union", "NATO",
]

THEME_CATEGORIES: Dict[str, List[str]] = {
    "conflict": ["armed", "conflict", "war", "attack", "military", "strike", "bomb", "missile", "invasion", "ceasefire", "truce", "rebel", "insurgent", "terror", "sanction", "troop"],
    "diplomacy": ["diplomat", "treaty", "agreement", "summit", "negotiation", "ambassador", "alliance", "pact", "accord", "memorandum", "resolution", "conference"],
    "economic": ["tariff", "trade", "sanction", "embargo", "inflation", "gdp", "recession", "debt", "deficit", "budget", "tax", "stimulus", "interest rate", "monetary", "fiscal"],
    "election": ["election", "vote", "poll", "ballot", "candidate", "campaign", "presidential", "parliament", "democracy", "inauguration"],
    "disaster": ["earthquake", "hurricane", "flood", "wildfire", "tsunami", "pandemic", "epidemic", "drought", "cyclone", "volcano", "landslide", "famine"],
    "protest": ["protest", "demonstration", "rally", "riot", "strike", "boycott", "civil unrest", "revolution", "uprising", "march"],
    "policy": ["regulation", "legislation", "decree", "executive order", "policy", "law", "bill", "act", "constitutional", "reform", "mandate"],
    "cyber": ["cyberattack", "hack", "breach", "ransomware", "malware", "phishing", "data leak", "cyber espionage", "cyber warfare"],
}

COMMON_STOP_TICKERS = {
    "A", "I", "THE", "FOR", "AND", "NOT", "ARE", "ALL", "BUT", "ITS", "HAS", "HAD",
    "HOW", "WHY", "WHO", "YOU", "WAS", "WERE", "CAN", "WILL", "JUST", "THAT", "THIS",
    "WITH", "FROM", "YOUR", "HAVE", "BEEN", "BEING", "ALSO", "VERY", "MUCH", "MANY",
    "SOME", "ANY", "EACH", "EVER", "NEVER", "NOW", "THEN", "THAN", "WHAT", "WHEN",
    "WHERE", "WHICH", "WHOSE", "ONE", "TWO", "NEW", "OLD", "GET", "USE", "SAY", "SHE",
    "HE", "HER", "HIM", "HIS", "SAID", "GOT", "MAY", "LET", "PUT", "SET", "RUN",
    "DID", "WAY", "LONG", "DAY", "YEAR", "WEEK", "MONTH", "END", "NEXT", "LAST",
    "FIRST", "BACK", "GOOD", "BIG", "EVEN", "STILL", "ALREADY", "ALWAYS", "OFTEN",
    "SURE", "REAL", "SAME", "ANOTHER", "BOTH", "EITHER", "NEITHER", "WHETHER",
    "THOUGH", "ALTHOUGH", "UNLESS", "BECAUSE", "SINCE", "WHILE", "DURING", "BEFORE",
    "AFTER", "ABOVE", "BELOW", "BETWEEN", "THROUGH", "WITHIN", "WITHOUT", "ALONG",
    "AMONG", "AROUND", "BEHIND", "BEYOND", "INSIDE", "OUTSIDE", "UNDER", "UPON",
    "UP", "DOWN", "OFF", "OVER", "OUT", "INTO", "ONTO", "UPON", "PER", "VIA",
}

TICKER_PATTERN = re.compile(r"\b[A-Z]{1,5}\b")


class GDELTParser:
    """Advanced GDELT parser with entity extraction, country/themes identification, and NLP enrichment."""

    @staticmethod
    def extract_sectors(text: str) -> List[str]:
        text_lower = text.lower()
        matched = []
        for sector, keywords in SECTOR_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                matched.append(sector)
        return list(set(matched))

    @staticmethod
    def extract_countries(text: str, raw_metadata: Optional[Dict[str, Any]] = None) -> List[str]:
        found: List[str] = []
        if raw_metadata:
            locations = raw_metadata.get("locations", [])
            if isinstance(locations, list):
                for loc in locations:
                    country = None
                    if isinstance(loc, dict):
                        country = loc.get("country") or loc.get("name", "")
                    elif isinstance(loc, str):
                        country = loc
                    if country and country not in found:
                        found.append(country)
            loc_str = raw_metadata.get("location", "")
            if isinstance(loc_str, list):
                for l in loc_str:
                    if isinstance(l, dict) and l.get("country") not in found:
                        found.append(l["country"])
            elif loc_str and loc_str not in found:
                found.append(loc_str)

        text_lower = text.lower()
        for country in KNOWN_COUNTRIES:
            if country.lower() in text_lower and country not in found:
                found.append(country)

        for alias, canonical in COUNTRY_ALIASES.items():
            if alias in text_lower and canonical not in found:
                found.append(canonical)

        return found

    @staticmethod
    def extract_entities(raw: Dict[str, Any]) -> Dict[str, List[str]]:
        entities: Dict[str, List[str]] = {"persons": [], "organizations": [], "locations": []}

        persons_raw = raw.get("persons", "")
        if isinstance(persons_raw, str):
            entities["persons"] = [p.strip() for p in persons_raw.split(";") if p.strip()]
        elif isinstance(persons_raw, list):
            entities["persons"] = [str(p) for p in persons_raw if p]

        orgs_raw = raw.get("organizations", "")
        if isinstance(orgs_raw, str):
            entities["organizations"] = [o.strip() for o in orgs_raw.split(";") if o.strip()]
        elif isinstance(orgs_raw, list):
            entities["organizations"] = [str(o) for o in orgs_raw if o]

        locs_raw = raw.get("locations", [])
        if isinstance(locs_raw, list):
            for loc in locs_raw:
                if isinstance(loc, dict):
                    name = loc.get("name", loc.get("fullname", loc.get("country", "")))
                    if name:
                        entities["locations"].append(name)
                elif isinstance(loc, str):
                    entities["locations"].append(loc)

        actors = GDELTParser.extract_actors(raw)
        if actors:
            for actor in actors:
                if actor not in entities["organizations"] and len(actor) > 2:
                    if any(c.islower() for c in actor):
                        entities["persons"].append(actor)
                    else:
                        entities["organizations"].append(actor)

        entities["persons"] = list(set(entities["persons"]))
        entities["organizations"] = list(set(entities["organizations"]))
        entities["locations"] = list(set(entities["locations"]))
        return entities

    @staticmethod
    def extract_themes(raw: Dict[str, Any]) -> List[str]:
        themes: List[str] = []
        themes_raw = raw.get("themes", "")
        if isinstance(themes_raw, str):
            themes = [t.strip().replace("_", " ").replace("-", " ").lower() for t in themes_raw.split(";") if t.strip()]
        elif isinstance(themes_raw, list):
            themes = [str(t).replace("_", " ").replace("-", " ").lower() for t in themes_raw if t]
        return themes

    @staticmethod
    def categorize_themes(themes: List[str], text: str) -> Dict[str, float]:
        categories: Dict[str, float] = {}
        text_lower = text.lower()

        for category, keywords in THEME_CATEGORIES.items():
            score = 0.0
            for keyword in keywords:
                if keyword in text_lower:
                    score += 1.0
            if score > 0:
                categories[category] = round(min(score / 3.0, 1.0), 4)

        for theme in themes:
            for category, keywords in THEME_CATEGORIES.items():
                if any(kw in theme for kw in keywords):
                    categories[category] = categories.get(category, 0) + 0.5

        if not categories:
            categories["other"] = 1.0

        total = sum(categories.values())
        if total > 0:
            categories = {k: round(v / total, 4) for k, v in categories.items()}

        return dict(sorted(categories.items(), key=lambda x: x[1], reverse=True))

    @staticmethod
    def compute_tone_analysis(raw: Dict[str, Any]) -> Dict[str, Any]:
        tone_str = raw.get("tone", "")
        if isinstance(tone_str, str):
            parts = tone_str.split(",")
            if len(parts) >= 1:
                tone_val = float(parts[0]) if parts[0] else 0.0
            else:
                tone_val = float(tone_str) if tone_str else 0.0

            pos_score = float(parts[1]) if len(parts) > 1 and parts[1] else 0.0
            neg_score = float(parts[2]) if len(parts) > 2 and parts[2] else 0.0
            polarity = float(parts[3]) if len(parts) > 3 and parts[3] else 0.0
            activity_ref = float(parts[4]) if len(parts) > 4 and parts[4] else 0.0
            self_ref = float(parts[5]) if len(parts) > 5 and parts[5] else 0.0
        else:
            tone_val = float(tone_str) if tone_str else 0.0
            pos_score = 0.0
            neg_score = 0.0
            polarity = 0.0
            activity_ref = 0.0
            self_ref = 0.0

        return {
            "tone_score": round(tone_val, 4),
            "positive_score": round(pos_score, 4),
            "negative_score": round(neg_score, 4),
            "polarity": round(polarity, 4),
            "activity_reference": round(activity_ref, 4),
            "self_reference": round(self_ref, 4),
            "normalized": round(max(-1.0, min(1.0, tone_val / 100.0)), 4),
        }

    @staticmethod
    def compute_severity(raw: Dict[str, Any]) -> float:
        tone_data = GDELTParser.compute_tone_analysis(raw)
        base = abs(tone_data["normalized"])

        goldstein = raw.get("goldsteinscale", 0.0)
        if goldstein:
            base = max(base, abs(float(goldstein)) / 10.0)

        num_mentions = int(raw.get("nummentions", 0) or 0)
        mention_factor = min(1.0, num_mentions / 2000.0)
        base += mention_factor * 0.15

        num_sources = int(raw.get("numsources", 0) or 0)
        source_factor = min(1.0, num_sources / 500.0)
        base += source_factor * 0.15

        event_code = raw.get("eventcode", "")
        if event_code.startswith(("20", "21", "22", "23", "24", "25", "18", "19")):
            base += 0.2
        elif event_code.startswith(("14", "15")):
            base += 0.1

        return round(max(0.0, min(1.0, base)), 4)

    @staticmethod
    def extract_tickers(text: str) -> List[str]:
        words = text.split()
        tickers = []
        for word in words:
            clean = word.strip("$¢£¥€.,!?;:'\"()[]{}")
            if TICKER_PATTERN.fullmatch(clean) and clean.isupper():
                if clean not in COMMON_STOP_TICKERS:
                    tickers.append(clean)
        return list(set(tickers))

    @staticmethod
    def extract_actors(raw: Dict[str, Any]) -> List[str]:
        actors = []
        for key in ("actor1name", "actor2name", "actor1type1", "actor2type1",
                     "actor1type2", "actor2type2", "actor1type3", "actor2type3"):
            val = raw.get(key, "")
            if val and val not in actors:
                actors.append(val.strip())
        return actors

    @staticmethod
    def parse_date(raw: Dict[str, Any]) -> datetime:
        date_str = (raw.get("dateadded", "") or raw.get("seendate", "") or
                     raw.get("date", "") or raw.get("day", ""))
        if date_str:
            clean = date_str.strip()
            if len(clean) >= 14:
                try:
                    return datetime.strptime(clean[:14], "%Y%m%d%H%M%S")
                except ValueError:
                    pass
            if len(clean) == 10:
                try:
                    return datetime.strptime(clean[:10], "%Y%m%d%H%M%S")
                except ValueError:
                    pass
            if "T" in clean:
                try:
                    return datetime.fromisoformat(clean.split(".")[0])
                except (ValueError, TypeError):
                    pass
            try:
                from dateutil import parser as dateparser
                return dateparser.parse(clean)
            except (ImportError, ValueError, TypeError):
                pass
        return datetime.now(timezone.utc)

    @staticmethod
    def parse_article(raw: Dict[str, Any]) -> Optional[GeoPolEvent]:
        try:
            title = raw.get("title", "").strip() or "Untitled Event"
            description = raw.get("summary", "").strip() or raw.get("content", "").strip() or title
            full_text = f"{title} {description}"

            event_date = GDELTParser.parse_date(raw)
            themes = GDELTParser.extract_themes(raw)
            entities = GDELTParser.extract_entities(raw)
            countries = GDELTParser.extract_countries(full_text, raw)
            tone_data = GDELTParser.compute_tone_analysis(raw)
            sectors = GDELTParser.extract_sectors(full_text)
            tickers = GDELTParser.extract_tickers(full_text)
            category_scores = GDELTParser.categorize_themes(themes, full_text)
            top_event_type = max(category_scores, key=category_scores.get) if category_scores else "other"
            severity = GDELTParser.compute_severity(raw)
            actors = GDELTParser.extract_actors(raw)

            source_url = raw.get("url", "")
            domain = raw.get("domain", "")
            language = raw.get("language", "")
            source_country = raw.get("sourcecountry", "")

            return GeoPolEvent(
                source="gdelt",
                title=title,
                description=description,
                event_date=event_date,
                location=countries[0] if countries else "Unknown",
                event_type=top_event_type,
                severity=severity,
                actors=actors,
                affected_sectors=sectors,
                source_url=source_url,
                mentions=int(raw.get("nummentions", raw.get("mentions", 0)) or 0),
                gdelt_raw={
                    "raw": raw,
                    "themes": themes,
                    "categories": category_scores,
                    "tone": tone_data,
                    "entities": entities,
                    "countries": countries,
                    "tickers": tickers,
                    "domain": domain,
                    "language": language,
                    "source_country": source_country,
                },
            )
        except Exception as e:
            logger.warning("Failed to parse GDELT article: %s", e)
            return None

    @staticmethod
    def parse_event(raw: Dict[str, Any]) -> Optional[GeoPolEvent]:
        try:
            title = raw.get("name", "").strip() or raw.get("title", "") or "Untitled Event"
            description = raw.get("description", "").strip() or raw.get("summary", "").strip() or title
            full_text = f"{title} {description}"
            event_date = GDELTParser.parse_date(raw)
            actors = GDELTParser.extract_actors(raw)
            countries = GDELTParser.extract_countries(full_text, raw)
            sectors = GDELTParser.extract_sectors(full_text)
            tickers = GDELTParser.extract_tickers(full_text)
            severity = GDELTParser.compute_severity(raw)
            themes = GDELTParser.extract_themes(raw)
            category_scores = GDELTParser.categorize_themes(themes, full_text)
            tone_data = GDELTParser.compute_tone_analysis(raw)
            top_event_type = max(category_scores, key=category_scores.get) if category_scores else "other"

            return GeoPolEvent(
                source="gdelt",
                title=title,
                description=description,
                event_date=event_date,
                location=countries[0] if countries else "Unknown",
                event_type=raw.get("eventcode", top_event_type),
                severity=severity,
                actors=actors,
                affected_sectors=sectors,
                source_url=raw.get("url", ""),
                mentions=int(raw.get("nummentions", 0) or 0),
                gdelt_raw={
                    "raw": raw,
                    "categories": category_scores,
                    "tone": tone_data,
                    "countries": countries,
                    "tickers": tickers,
                    "themes": themes,
                },
            )
        except Exception as e:
            logger.warning("Failed to parse GDELT event: %s", e)
            return None

    @staticmethod
    def batch_parse(articles: List[Dict[str, Any]]) -> List[GeoPolEvent]:
        parsed = []
        for raw in articles:
            event = GDELTParser.parse_article(raw)
            if event:
                parsed.append(event)
        return parsed

    @staticmethod
    def batch_parse_events(event_list: List[Dict[str, Any]]) -> List[GeoPolEvent]:
        parsed = []
        for raw in event_list:
            event = GDELTParser.parse_event(raw)
            if event:
                parsed.append(event)
        return parsed

    @staticmethod
    def compute_signal_strength(event: GeoPolEvent) -> Dict[str, Any]:
        raw = event.gdelt_raw or {}
        tone = raw.get("tone", {}) if isinstance(raw, dict) else {}

        signal_score = event.severity * 0.4
        signal_score += abs(tone.get("normalized", 0)) * 0.2

        mention_bonus = min(1.0, event.mentions / 1000.0) * 0.2
        signal_score += mention_bonus

        sector_count = len(event.affected_sectors)
        sector_bonus = min(1.0, sector_count / 5.0) * 0.2
        signal_score += sector_bonus

        return {
            "signal_strength": round(min(1.0, signal_score), 4),
            "is_high_signal": signal_score >= 0.6,
            "is_medium_signal": 0.3 <= signal_score < 0.6,
            "is_low_signal": signal_score < 0.3,
            "components": {
                "severity_weight": round(event.severity * 0.4, 4),
                "tone_weight": round(abs(tone.get("normalized", 0)) * 0.2, 4),
                "mention_weight": round(mention_bonus, 4),
                "sector_weight": round(sector_bonus, 4),
            },
        }
