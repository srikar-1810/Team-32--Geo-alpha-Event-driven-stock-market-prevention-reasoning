# GeoMarketGPT API Reference

## Base URL

Development: `http://localhost:8000/api/v1`
Production: `/api/v1`

## Authentication

Most endpoints require a JWT Bearer token:
```
Authorization: Bearer <token>
```

## Endpoints

### Health Check

```
GET /health
```

Response:
```json
{
    "name": "GeoMarketGPT",
    "version": "0.1.0",
    "environment": "development",
    "timestamp": "2024-01-01T00:00:00Z",
    "status": "ok",
    "checks": {
        "database": "healthy",
        "redis": "healthy"
    }
}
```

### Geopolitical Events

#### List Events
```
GET /geopol/events?page=1&page_size=20&event_type=conflict&min_severity=0.5
```

#### Get Event
```
GET /geopol/events/{event_id}
```

#### Ingest Event
```
POST /geopol/events/ingest
```
Request:
```json
{
    "source": "gdelt",
    "title": "Event Title",
    "description": "Event description",
    "event_date": "2024-01-01T00:00:00Z",
    "location": "Region",
    "event_type": "conflict",
    "severity": 0.7,
    "actors": ["ActorA"],
    "affected_sectors": ["energy"],
    "source_url": "https://..."
}
```

#### Get Summary
```
GET /geopol/summary
```

### Sentiment Analysis

#### Analyze Sentiment
```
GET /sentiment/analysis?query=AAPL&source=reddit
```

#### Get Trends
```
GET /sentiment/trends?ticker=AAPL&hours=24
```

### Market Data

#### Get Market Data
```
GET /markets/data/SPY?start_date=2024-01-01&end_date=2024-01-30
```

#### Assess Impact
```
GET /markets/impact?event_id=event-123
```

#### Assess Portfolio
```
POST /markets/portfolio/impact
```

### RAG

#### Query RAG
```
POST /rag/query
```
```json
{
    "query": "Impact of sanctions on energy sector",
    "collection": "geopol_events",
    "top_k": 5
}
```

#### Index Document
```
POST /rag/index
```
```json
{
    "collection": "geopol_events",
    "content": "Document text...",
    "metadata": {"source": "gdelt"}
}
```

### AI Agents

#### List Agents
```
GET /agents
```

#### Run Agent
```
POST /agents/run/{agent_id}
```
```json
{
    "input_data": {"query": "Analysis text..."}
}
```

#### Run Orchestration
```
POST /agents/orchestrate
```
```json
{
    "agents": ["geopol-agent", "market-agent"],
    "input_data": {"query": "Market analysis"},
    "workflow_type": "sequential"
}
```

### Reports

#### Generate Report
```
POST /reports/generate
```
```json
{
    "title": "Daily Briefing",
    "format": "markdown",
    "sections": ["Executive Summary"]
}
```

### Simulation

#### Create Scenario
```
POST /simulation/scenarios
```
```json
{
    "name": "Conflict Scenario",
    "description": "Description...",
    "parameters": []
}
```

#### Run Scenario
```
POST /simulation/scenarios/{scenario_id}/run
```

### Backtesting

#### Run Backtest
```
POST /backtest/run
```
```json
{
    "strategy": "mean_reversion",
    "tickers": ["SPY"],
    "start_date": "2024-01-01",
    "end_date": "2024-01-30",
    "initial_capital": 100000.0
}
```

## Error Responses

```json
{
    "error": "VALIDATION_ERROR",
    "message": "Description of error",
    "details": {},
    "timestamp": "2024-01-01T00:00:00Z"
}
```

Error codes: `VALIDATION_ERROR`, `NOT_FOUND`, `SERVICE_ERROR`, `RATE_LIMIT`, `AGENT_ERROR`, `CONFIG_ERROR`, `INTERNAL_ERROR`
