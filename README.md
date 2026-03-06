# Automated News Aggregator API

A production-style backend system that **automatically fetches news from rotating query terms every minute** from [NewsAPI.org](https://newsapi.org) and serves them through a blazing-fast REST API — built with **FastAPI**, **Celery**, **Redis**, and **MySQL**.

---

## Table of Contents

- [Overview](#overview)
- [System Architecture](#system-architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Setup & Installation](#setup--installation)
- [Running the Application](#running-the-application)
- [API Reference](#api-reference)
- [Example Response](#example-response)
- [How the Data Flow Works](#how-the-data-flow-works)
- [Key Design Decisions](#key-design-decisions)

---

## Overview

This project solves a real-world engineering problem: **how do you serve news articles to thousands of users instantly, without making them wait for a slow external API call?**

The solution is a **decoupled architecture**:

- A **background scheduler** fetches fresh news from NewsAPI.org every 60 seconds and caches it in a MySQL database.
- A **FastAPI web server** serves articles from the local database in milliseconds — with zero external API calls at query time.

This means users always get a near-instant response, and the news data is always kept up-to-date automatically.

---

## System Architecture

The application runs as **3 independent services** that communicate via Redis:

```
┌──────────────────────────────────────────────────────────────┐
│                         USER / CLIENT                        │
│              GET /news?date=2024-03-04                       │
└──────────────────────────┬───────────────────────────────────┘
                           │ HTTP Request
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                  SERVICE 1: FastAPI Server                   │
│                      (app/main.py)                           │
│                                                              │
│  • Receives GET /news?date=... request                       │
│  • Queries MySQL for articles on that date                   │
│  • Middleware injects total_time_taken into every response   │
│  • Returns JSON in milliseconds                              │
└──────────────────────────┬───────────────────────────────────┘
                           │ Reads from
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                      MySQL Database                          │
│                     (news_articles table)                    │
│                                                              │
│  Stores: title, author, source, description, url,           │
│          published_at, published_date, content               │
└──────────────────────────▲───────────────────────────────────┘
                           │ Writes to
                           │
┌──────────────────────────┴───────────────────────────────────┐
│                SERVICE 2: Celery Worker                      │
│                      (app/worker.py)                         │
│                                                              │
│  • Receives "fetch news" task from Redis queue               │
│  • Calls NewsAPI.org /v2/everything                       │
│  • Deduplicates articles by URL                              │
│  • Inserts only new articles into MySQL                      │
└──────────────────────────▲───────────────────────────────────┘
                           │ Task sent via Redis
                           │
┌──────────────────────────┴───────────────────────────────────┐
│               SERVICE 3: Celery Beat Scheduler               │
│                      (app/worker.py)                         │
│                                                              │
│  • Acts as an "alarm clock"                                  │
│  • Every 60 seconds, sends a task to Redis                   │
│  • Does NOT fetch news itself — just triggers the Worker     │
└──────────────────────────────────────────────────────────────┘
                           │
┌──────────────────────────▼───────────────────────────────────┐
│                    Redis (Message Broker)                    │
│                                                              │
│  • In-memory queue between Scheduler and Worker              │
│  • Scheduler drops task → Worker picks it up                 │
│  • Handles async decoupling of services                      │
└──────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Component | Technology | Purpose |
|---|---|---|
| Web Framework | FastAPI | REST API server with automatic Swagger docs |
| Background Tasks | Celery | Distributed task queue for async news fetching |
| Task Scheduler | Celery Beat | Cron-style scheduler (fires every 60 seconds) |
| Message Broker | Redis | Queue between Beat and Worker |
| Database | MySQL | Persistent storage for news articles |
| ORM | SQLAlchemy | Database models and query abstraction |
| Data Validation | Pydantic | Request/response schema validation |
| News Source | NewsAPI.org | /v2/everything endpoint with rotating query terms and page-based crawling |
| Logging | Python logging | Structured logs across all 3 services |

---

## Project Structure

```
News_Api_JArvis/
│
├── .env                    # Secret keys (not committed to git)
├── requirements.txt        # Python dependencies
├── init_db.py              # One-time script to create the MySQL database
│
└── app/
    ├── main.py             # FastAPI app — defines GET /news endpoint + middleware
    ├── models.py           # SQLAlchemy ORM model (NewsArticle table)
    ├── schemas.py          # Pydantic schemas for request/response validation
    ├── database.py         # MySQL engine and session factory
    ├── config.py           # Settings loaded from .env via pydantic-settings
    ├── logger.py           # Shared logger factory used by all services
    ├── worker.py           # Celery app, Beat schedule, and fetch task definition
    │
    └── services/
        └── news_api.py     # HTTP client that calls NewsAPI.org
```

---

## Prerequisites

Make sure the following are installed and running on your machine before setup:

- **Python 3.8+**
- **MySQL Server** (running on port 3306)
- **Redis Server** (running on port 6379)
  - On Windows: install via WSL2 (`sudo apt install redis-server && redis-server`)
  - On Linux/macOS: `sudo apt install redis-server` or `brew install redis`
- A free **NewsAPI.org** API key — get one at [https://newsapi.org/register](https://newsapi.org/register)

---

## Setup & Installation

### Step 1 — Clone the repository

```bash
git clone https://github.com/your-username/News_Api_JArvis.git
cd News_Api_JArvis
```

### Step 2 — Create a virtual environment and install dependencies

```bash
python -m venv venv

# On Windows:
.\venv\Scripts\Activate

# On Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
```

### Step 3 — Create the `.env` file

Create a file named `.env` in the project root with your credentials:

```env
MYSQL_USER="root"
MYSQL_PASSWORD="your_mysql_password"
MYSQL_HOST="localhost"
MYSQL_PORT="3306"
MYSQL_DB="news_db"

NEWS_API_KEY="your_newsapi_key_here"
NEWS_QUERY_TERMS="bitcoin,technology,finance,ai,startups"

CELERY_BROKER_URL="redis://localhost:6379/0"
CELERY_RESULT_BACKEND="redis://localhost:6379/0"
```

### Step 4 — Initialize the database

Run the helper script once to create the `news_db` database in MySQL:

```bash
python init_db.py
```

Expected output:
```
Connecting to MySQL as root@localhost:3306...
Database 'news_db' created or already exists.
```

The `news_articles` table is created automatically when FastAPI starts (via SQLAlchemy's `create_all`).

---

## Running the Application

You need **3 separate terminal windows** all running simultaneously. In each terminal, activate the virtual environment first.

### Terminal 1 — Start the FastAPI Web Server

```bash
uvicorn app.main:app --reload
```

The API will be live at `http://127.0.0.1:8000`

### Terminal 2 - Start the Celery Worker

```bash
celery -A app.worker.celery_app worker -l INFO --pool=solo
```

This worker listens for tasks from Redis and executes the news-fetching logic.

Each run uses one rotating query term from NEWS_QUERY_TERMS and crawls the next page for that term.

Optional for Linux/macOS: if you want higher concurrency, install eventlet and run celery -A app.worker.celery_app worker -l INFO -P eventlet.

### Terminal 3 - Start the Celery Beat Scheduler

```bash
celery -A app.worker.celery_app beat -l INFO
```

This scheduler fires the fetch task every 60 seconds automatically.

Once all 3 terminals are running, the system is fully operational. Within the first minute, news articles will begin appearing in the database.

---

## API Reference

### `GET /news`

Fetches all news articles stored in the database for a given date.

**Query Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `date` | `YYYY-MM-DD` | Yes | The publication date to filter articles by |

**Example Request:**

```
GET http://127.0.0.1:8000/news?date=2024-03-04
```

**Interactive Docs (Swagger UI):**

```
http://127.0.0.1:8000/docs
```

FastAPI auto-generates a full interactive Swagger UI where you can test the endpoint directly in your browser — no Postman needed.

---

## Example Response

The custom middleware automatically measures how long the server took to process the request and injects `total_time_taken` into every JSON response.

```json
{
  "data": [
    {
      "id": 1,
      "source_name": "TechCrunch",
      "author": "Jane Doe",
      "title": "A breakthrough in AI technology announced",
      "description": "Researchers have announced a new model that sets a record...",
      "url": "https://techcrunch.com/2024/03/04/ai-breakthrough",
      "published_at": "2024-03-04T12:00:00",
      "published_date": "2024-03-04",
      "created_at": "2024-03-04T12:01:03.453000",
      "content": "Full article text here..."
    },
    {
      "id": 2,
      "source_name": "BBC News",
      "author": "John Smith",
      "title": "Global markets rise on positive economic data",
      "description": "Stock markets around the world surged today after...",
      "url": "https://bbc.com/news/business-12345",
      "published_at": "2024-03-04T09:30:00",
      "published_date": "2024-03-04",
      "created_at": "2024-03-04T09:31:05.112000",
      "content": "Full article text here..."
    }
  ],
  "total_time_taken": "8.43 ms"
}
```

**If no articles exist for the requested date**, the endpoint returns an empty list with the processing time:

```json
{
  "data": [],
  "total_time_taken": "3.12 ms"
}
```

---

## How the Data Flow Works

Here is the complete lifecycle of data through the system:

```
1. [Every 60s] Celery Beat fires → sends "fetch_news" task to Redis

2. [Celery Worker] picks up task from Redis queue
   -> selects one query term from NEWS_QUERY_TERMS (round-robin)
   -> reads page number for that query from Redis state
   -> calls NewsAPI.org: GET /v2/everything?q=<term>&page=<n>&apiKey=...
   -> receives JSON list of articles
   -> increments page for that same query term in Redis (for next cycle)

3. [Celery Worker] processes each article:
   → checks if article URL already exists in MySQL (deduplication)
   → if new: parses publishedAt datetime, extracts date component
   → inserts new NewsArticle row into MySQL

4. [User Request] GET /news?date=2024-03-04
   → FastAPI queries MySQL: SELECT * WHERE published_date = '2024-03-04'
   → Middleware measures response time
   → Returns JSON with articles + total_time_taken field
```

---

## Key Design Decisions

**Decoupled fetching from serving**
The web server never calls NewsAPI.org directly. If NewsAPI is slow or down, the REST API remains fast and available because it only reads from the local MySQL database.

**Redis as a message broker**
Redis acts as a fault-tolerant queue between the scheduler and the worker. If the worker is momentarily busy, the task waits in Redis — no tasks are dropped.

**URL-based deduplication**
Before inserting any article, the worker checks if the URL already exists in the database. This prevents duplicate rows even if the same article appears across multiple fetch cycles.

**Rotating query terms + per-query page crawl**
The worker rotates through terms from `NEWS_QUERY_TERMS` and keeps a separate page counter per term in Redis. This helps discover broader result sets over time instead of repeatedly requesting only page 1 for a single query.

**Separate `published_date` column**
The `published_at` (datetime) field is stored alongside a derived `published_date` (date) column. This makes date-based filtering via the API query (`?date=...`) simple and fast with a database index.

**Middleware for response timing**
A custom FastAPI middleware intercepts every response, calculates elapsed time in milliseconds, and injects `total_time_taken` into the JSON body — giving real-time performance visibility to API consumers.

**Structured logging**
All 3 services use a shared `setup_logger()` factory that outputs timestamped, leveled logs to stdout — making it easy to trace the full lifecycle of any request or background task.

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
