from __future__ import annotations

import pytest
from datetime import datetime, timezone

from app.services.gdelt.parser import GDELTParser
from app.services.gdelt.client import GDELTClient


class TestGDELTParser:
    def test_extract_sectors_energy(self):
        text = "oil prices surge due to middle east conflict"
        sectors = GDELTParser.extract_sectors(text)
        assert "energy" in sectors

    def test_extract_sectors_defense(self):
        text = "military spending increases defense budget"
        sectors = GDELTParser.extract_sectors(text)
        assert "defense" in sectors

    def test_extract_sectors_empty(self):
        sectors = GDELTParser.extract_sectors("")
        assert sectors == []

    def test_extract_actors(self):
        raw = {
            "actor1name": "United States",
            "actor2name": "Russia",
            "actor1type1": "Government",
            "actor2type1": "Government",
        }
        actors = GDELTParser.extract_actors(raw)
        assert "United States" in actors
        assert "Russia" in actors
        assert "Government" in actors

    def test_compute_severity(self):
        raw = {"tone": -5.0, "goldsteinscale": -3.0, "nummentions": 500}
        severity = GDELTParser.compute_severity(raw)
        assert 0.0 <= severity <= 1.0

    def test_compute_severity_zero_mentions(self):
        raw = {"tone": 0, "goldsteinscale": 0, "nummentions": 0}
        severity = GDELTParser.compute_severity(raw)
        assert severity >= 0.0

    def test_parse_event(self):
        raw = {
            "title": "Test Event",
            "summary": "A test geopolitical event",
            "seendate": "20240101000000",
            "url": "https://example.com",
            "tone": -2.0,
            "goldsteinscale": -1.0,
            "nummentions": 100,
            "actor1name": "CountryA",
            "eventcode": "201",
        }
        event = GDELTParser.parse_event(raw)
        assert event is not None
        assert event.title == "Test Event"
        assert event.source == "gdelt"

    def test_parse_event_missing_fields(self):
        event = GDELTParser.parse_event({})
        assert event is not None
        assert event.title == "Untitled Event"

    def test_batch_parse(self):
        events = [
            {"title": "Event 1", "seendate": "20240101000000"},
            {"title": "Event 2", "seendate": "20240102000000"},
            {},
        ]
        parsed = GDELTParser.batch_parse(events)
        assert len(parsed) == 3
