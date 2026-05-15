# GeoMarketGPT Architecture

## System Overview

GeoMarketGPT is a modular, event-driven, multi-agent AI platform that:

1. **Ingests** real-time geopolitical data (GDELT), social sentiment (Reddit), and market data (Tiingo)
2. **Stores** structured data in PostgreSQL, vectors in ChromaDB, and cache in Redis
3. **Processes** data through specialized AI agents (Geopolitical, Sentiment, Market, RAG, Report, Simulation)
4. **Orchestrates** agents in sequential or parallel workflows
5. **Retrieves** historical context via RAG for informed analysis
6. **Generates** reports in multiple formats
7. **Simulates** what-if scenarios for risk assessment

## Architecture Principles

- **Async-First**: All I/O operations use async/await throughout
- **Modular**: Each service is independently testable and deployable
- **Event-Driven**: Agents communicate through shared context
- **RAG-Enhanced**: Historical data retrieval augments LLM reasoning
- **Observable**: Structured logging, metrics, and distributed tracing

## Data Flow

```
[GDELT API] ──► [Ingestion Worker] ──► [PostgreSQL + ChromaDB]
[Reddit API] ──► [Ingestion Worker] ──► [PostgreSQL + ChromaDB]
[Tiingo API] ──► [Ingestion Worker] ──► [PostgreSQL + ChromaDB]

User Query ──► [RAG Agent] ──► [ChromaDB Retrieval]
                  │
                  ▼
         [Geopolitical Agent] ──► [Market Agent] ──► [Sentiment Agent]
                  │                                        │
                  └──────────┬────────────────────────────┘
                             ▼
                    [Report Generator]
                             │
                             ▼
                    [Structured Report]
```

## Multi-Agent Workflow

### Sequential Mode
```
Agent A ──► Agent B ──► Agent C ──► Report
```
Each agent receives the output of the previous agent as context.

### Parallel Mode
```
Agent A ──┐
Agent B ──┼──► Aggregate ──► Report
Agent C ──┘
```
All agents run simultaneously; results are aggregated.

## RAG Pipeline

```
Query ──► Embedding ──► ChromaDB Similarity Search
                 │
                 ▼
        Retrieved Documents
                 │
                 ▼
        LLM Context Assembly
                 │
                 ▼
        Generated Response
```

## Service Layer Responsibilities

| Service | Responsibility |
|---------|---------------|
| `gdelt/` | Fetch and parse GDELT 2.0 events, article search |
| `reddit/` | Async Reddit API client, sentiment analysis, ticker extraction |
| `tiingo/` | Stock prices, IEX data, news, metadata |
| `chroma/` | Vector storage, embeddings, similarity search |
| `agent/` | LangGraph-based multi-agent system |
| `rag/` | Retrieval-Augmented Generation engine |
| `report/` | Report generation (markdown, HTML, JSON) |

## Security Model

- API authentication via JWT tokens
- API keys stored in environment variables (never in code)
- Rate limiting per service client
- Input validation at API layer via Pydantic
- SQL injection prevention via SQLAlchemy ORM
- CORS middleware configured for frontend access

## Monitoring

- **Sentry**: Error tracking and performance monitoring
- **Prometheus**: Application metrics (request count, latency, error rate)
- **structlog**: Structured JSON logging with context
- **Health Checks**: Database, Redis, and service-level health endpoints

## Scaling Considerations

- Stateless API servers (horizontal scaling)
- Redis-based Celery task queue for background processing
- Connection pooling for database and HTTP clients
- ChromaDB runs as a separate service
- Rate limiting for external API calls
