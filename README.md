web page link: https://mahindraecolecentrale-my.sharepoint.com/:u:/g/personal/nidhi_goyal_mahindrauniversity_edu_in/IQBrkI9X-fELQqj29HNVlAqhAcaYUsKuz5Zf8tiBiAfuv44?e=aae9eo
---
title: GeoMarketGPT
emoji: 📊
colorFrom: indigo
colorTo: blue
sdk: docker
pinned: false
---
web page link: https://mahindraecolecentrale-my.sharepoint.com/:u:/g/personal/nidhi_goyal_mahindrauniversity_edu_in/IQBrkI9X-fELQqj29HNVlAqhAcaYUsKuz5Zf8tiBiAfuv44?e=aae9eo
# GeoMarketGPT

**Generative Geopolitical Financial Intelligence System** — A real-time, agent-driven platform that ingests live geopolitical events and market data to predict sector impacts, run generative scenario simulations, and automatically synthesize institutional-grade intelligence briefs.

![GeoMarketGPT Dashboard](https://github.com/Slio1013/GenAI-project/assets/placeholder_image.png)

## 🚀 Key Features

*   **Generative AI Workflows**:
    *   **Intelligence Brief Builder**: Synthesizes real-time geopolitical signals into institutional-grade JSON/PDF reports autonomously.
    *   **Scenario Simulator**: AI-powered "what-if" analysis predicting market fallout, supply chain disruptions, and sector sentiment across user-defined hypothetical events.
    *   **Historical RAG Explorer**: Searches thousands of embedded historical events (via ChromaDB) to identify market analogues and precedents.
*   **High-Fidelity Dashboard**: Built entirely in Streamlit with custom injected CSS, featuring dark-mode glassmorphic layouts, dynamic metrics, and a "Bloomberg-Terminal" aesthetic.
*   **Google Gemini Integration**: Fully optimized for `gemini-3.1-flash-lite` inference via LangGraph's multi-agent orchestration pipeline.
*   **Graceful Degradation**: Automatically falls back to localized fallback data injections if external public APIs (like GDELT or Tiingo) hit rate limits.

---

## 🛠️ How to Setup on a New PC

GeoMarketGPT is **100% containerized**. You do not need to install Python, Postgres, Redis, or ChromaDB on your host machine. Docker will handle the entire infrastructure.

### Prerequisites
1.  Download and install **[Docker Desktop](https://www.docker.com/products/docker-desktop/)**.
2.  Ensure Docker Engine is running on your machine.

### Step-by-Step Installation

**1. Clone the Repository**
```bash
git clone https://github.com/Slio1013/GenAI-project.git
cd GenAI-project
```

**2. Configure Environment Variables**
The project requires API keys to fetch external intelligence and generate responses.
*   Copy the example environment file:
    ```bash
    cp .env.example .env
    ```
*   Open `.env` in any text editor and add your API keys:
    *   `OPENAI_API_KEY`: Your Google Gemini API Key (or OpenAI key if using a different provider).
    *   `TIINGO_API_TOKEN`: Your Tiingo stock data key (optional, will fallback to Yahoo Finance if omitted or exhausted).

**3. Choose Your Operating Mode**
Inside the `.env` file, you must configure the `MOCK_MODE` variable depending on your use case:
*   **Live Mode (`MOCK_MODE=false`)**: The platform will make live external calls to the Gemini API, GDELT, and Market Data endpoints to generate real-time AI intelligence. **Requires valid API keys.**
*   **Mock Mode (`MOCK_MODE=true`)**: The platform runs entirely offline using pre-generated offline data seeds. Perfect for local UI testing, development, and demonstrations without burning API quota or needing internet access.

**4. Build and Launch Containers**
Run the following command to download the base OS images, install dependencies, and boot all 6 microservices (API, Frontend, Postgres, Redis, Chroma, Celery).
```bash
docker compose build
docker compose up -d
```
*Wait ~1-2 minutes for the databases to initialize.*

**5. Initialize the Database (First Run Only)**
If this is your first time booting the project on this PC, you need to seed the database tables:
```bash
docker exec -it geomarketgpt-api bash scripts/setup_env.sh
```

**6. Access the Platform**
*   **Streamlit UI**: Navigate to `http://localhost:8501`
*   **FastAPI Backend Docs**: Navigate to `http://localhost:8000/docs`

---

## 🧠 System Architecture

```text
┌──────────────────────────────────────────────────────────────────────────┐
│                         Streamlit Frontend                               │
│  Intelligence Reports | Scenario Simulation | RAG Explorer | Agent Tools │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │ HTTP/REST (api:8000)
┌────────────────────────────────▼─────────────────────────────────────────┐
│                           FastAPI Backend                                │
│                                                                          │
│  ┌─────────────────────── Service Layer ─────────────────────────────┐   │
│  │ ┌────────┐ ┌──────────┐ ┌────────────┐ ┌─────────┐ ┌─────────────┐│   │
│  │ │ GDELT  │ │  Reddit  │ │ Simulation │ │ RAG     │ │   Report    ││   │
│  │ │ Ingest │ │  Ingest  │ │ Engine     │ │ Engine  │ │  Generator  ││   │
│  │ └────────┘ └──────────┘ └────────────┘ └─────────┘ └─────────────┘│   │
│  │ ┌────────────────────────────────────────────────────────────────┐│   │
│  │ │         Multi-Agent LangGraph Orchestrator (Gemini)            ││   │
│  │ │  News Intel → Sentiment → Historical → Market → Risk → Report  ││   │
│  │ └────────────────────────────────────────────────────────────────┘│   │
│  └───────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────┘
                                 │
┌───────────┬───────────┬───────────────┬───────────────┬────────────────┐
│ PostgreSQL│   Redis   │   ChromaDB    │  Celery (4)   │   Data Volumes │
│ (Events,  │ (Cache,   │(Vectors 384d, │ Async Tasks   │ /data/historical│
│ Sessions) │  Queue)   │ Embeddings)   │               │ /data/reports  │
└───────────┴───────────┴───────────────┴───────────────┴────────────────┘
```

## 🔄 Automated Ingestion Pipeline
*   **GDELT 2.0**: Ingests geopolitical events every 20 minutes. (Includes fail-safe fallback events if GDELT rate limits).
*   **Reddit API**: Tracks retail sentiment across r/wallstreetbets, r/investing, etc.
*   **Tiingo / Yahoo Finance**: Tracks pricing, momentum, and volatility across 25 major global sector ETFs.

## 📄 License
MIT License.
