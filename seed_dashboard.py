import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from app.services.ingestion.storage import geopol_storage
from app.models.geopol_event import GeoPolEvent

async def seed_data():
    print("Seeding realistic geopolitical events...")
    
    events = [
        GeoPolEvent(
            source="gdelt",
            title="Tensions escalate in South China Sea over new maritime boundaries",
            description="Recent naval maneuvers and diplomatic protests have increased instability in the region as multiple nations contest newly announced maritime boundaries. Impact on shipping lanes is being monitored closely.",
            event_date=datetime.now(timezone.utc) - timedelta(hours=2),
            location="South China Sea",
            event_type="conflict",
            severity=0.75,
            actors=["China", "Philippines", "Vietnam", "USA"],
            affected_sectors=["energy", "transportation", "defense"],
            source_url="https://example.com/news/1"
        ),
        GeoPolEvent(
            source="gdelt",
            title="EU announces new tech regulations targeting AI safety",
            description="The European Commission has unveiled a comprehensive framework for AI regulation, focusing on high-risk applications and transparency requirements. Tech majors are reviewing compliance costs.",
            event_date=datetime.now(timezone.utc) - timedelta(hours=5),
            location="Brussels",
            event_type="policy",
            severity=0.6,
            actors=["European Union", "Google", "Microsoft", "OpenAI"],
            affected_sectors=["technology", "finance"],
            source_url="https://example.com/news/2"
        ),
        GeoPolEvent(
            source="gdelt",
            title="OPEC+ considers deeper production cuts amid slowing demand",
            description="Major oil producers are discussing further supply reductions to stabilize prices as global economic data suggests a potential slowdown in energy consumption.",
            event_date=datetime.now(timezone.utc) - timedelta(hours=8),
            location="Vienna",
            event_type="economic",
            severity=0.8,
            actors=["OPEC", "Saudi Arabia", "Russia"],
            affected_sectors=["energy", "transportation", "agriculture"],
            source_url="https://example.com/news/3"
        ),
        GeoPolEvent(
            source="gdelt",
            title="Major cyberattack disrupts regional energy grid",
            description="A sophisticated ransomware attack has temporarily disabled power distribution networks in several Eastern European cities. Authorities suspect state-sponsored actors.",
            event_date=datetime.now(timezone.utc) - timedelta(hours=12),
            location="Eastern Europe",
            event_type="cyber",
            severity=0.85,
            actors=["Unknown Hackers", "Regional Utilities"],
            affected_sectors=["technology", "energy", "real_estate"],
            source_url="https://example.com/news/4"
        ),
        GeoPolEvent(
            source="gdelt",
            title="Federal Reserve signals 'higher for longer' interest rate path",
            description="Central bank officials emphasized the need to maintain restrictive monetary policy until inflation targets are firmly met, causing ripples across global bond markets.",
            event_date=datetime.now(timezone.utc) - timedelta(hours=15),
            location="Washington D.C.",
            event_type="economic",
            severity=0.7,
            actors=["Federal Reserve", "US Treasury"],
            affected_sectors=["finance", "real_estate", "technology"],
            source_url="https://example.com/news/5"
        ),
        GeoPolEvent(
            source="gdelt",
            title="Breakthrough in semiconductor trade talks between US and Japan",
            description="Negotiators have reached a preliminary agreement to cooperate on advanced chip manufacturing and supply chain resilience, reducing reliance on third-party suppliers.",
            event_date=datetime.now(timezone.utc) - timedelta(hours=18),
            location="Tokyo",
            event_type="diplomacy",
            severity=0.5,
            actors=["USA", "Japan", "TSMC", "Intel"],
            affected_sectors=["technology", "defense"],
            source_url="https://example.com/news/6"
        ),
        GeoPolEvent(
            source="gdelt",
            title="Political unrest flares up in major South American lithium hub",
            description="Protests regarding mining rights and environmental impact have halted operations at several key lithium extraction sites, raising concerns about global EV battery supplies.",
            event_date=datetime.now(timezone.utc) - timedelta(hours=22),
            location="South America",
            event_type="protest",
            severity=0.65,
            actors=["Local Communities", "Mining Companies", "National Government"],
            affected_sectors=["commodities", "technology", "transportation"],
            source_url="https://example.com/news/7"
        ),
        GeoPolEvent(
            source="gdelt",
            title="NATO increases military presence in Baltic region",
            description="In response to regional security shifts, NATO has announced a rotation of additional combat-ready troops and advanced aerial surveillance assets to its eastern flank.",
            event_date=datetime.now(timezone.utc) - timedelta(days=1),
            location="Baltics",
            event_type="conflict",
            severity=0.7,
            actors=["NATO", "Russia", "Poland", "Germany"],
            affected_sectors=["defense", "energy"],
            source_url="https://example.com/news/8"
        ),
        GeoPolEvent(
            source="gdelt",
            title="Global shipping rates surge due to canal drought restrictions",
            description="Persistent drought conditions have forced further transit limitations in major global shipping canals, leading to significant delays and increased freight costs.",
            event_date=datetime.now(timezone.utc) - timedelta(days=1, hours=4),
            location="Panama / Egypt",
            event_type="disaster",
            severity=0.6,
            actors=["Suez Canal Authority", "Maersk", "MSC"],
            affected_sectors=["transportation", "agriculture", "commodities"],
            source_url="https://example.com/news/9"
        ),
        GeoPolEvent(
            source="gdelt",
            title="New pharmaceutical patent laws passed in India",
            description="The Indian government has revised its intellectual property laws for drug manufacturing, potentially impacting the global generic medicine market and big pharma margins.",
            event_date=datetime.now(timezone.utc) - timedelta(days=1, hours=10),
            location="New Delhi",
            event_type="policy",
            severity=0.55,
            actors=["Indian Government", "Pfizer", "Sun Pharma"],
            affected_sectors=["healthcare", "finance"],
            source_url="https://example.com/news/10"
        )
    ]
    
    # Add 10 more slightly older events
    for i in range(11, 21):
        events.append(GeoPolEvent(
            source="gdelt",
            title=f"Regional Geopolitical Shift Update {i}",
            description=f"Ongoing monitoring of political and economic indicators suggests a continuing shift in regional stability. Analysts are closely watching for secondary market impacts.",
            event_date=datetime.now(timezone.utc) - timedelta(days=i//5, hours=i*2),
            location="Global",
            event_type="other",
            severity=0.4,
            actors=["Regional Stakeholders"],
            affected_sectors=["finance"],
            source_url=f"https://example.com/news/{i}"
        ))

    count = await geopol_storage.save_events(events)
    print(f"Successfully seeded {count} events.")

if __name__ == "__main__":
    asyncio.run(seed_data())
