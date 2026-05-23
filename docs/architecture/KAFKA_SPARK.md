# Event-Driven Architecture (Kafka + Spark)

EmpowerWork thesis demo: decouple heavy work with **Apache Kafka** and batch analytics with **Apache Spark** (PySpark). Set `USE_SPARK=false` only if you need pandas fallback.

## Why Kafka?

| Without Kafka | With Kafka |
|---------------|------------|
| CV parsing blocks HTTP | `ApplicationSubmitted` → `cv_worker` |
| Groq chat blocks HTTP | `ChatRequested` → `chat_worker` + Redis poll |
| Job indexing inline | `JobCreated` → `job_embedding_worker` → ChromaDB |

## Why Spark?

Workers write events to `data/lake/dt=YYYY-MM-DD/*.jsonl`. Spark (or pandas fallback) aggregates metrics → `data/reports/latest.json` → Admin dashboard.

---

## Windows setup (PowerShell)

### Common mistakes from the terminal

| What you typed | Problem | Fix |
|----------------|---------|-----|
| `EVENTS_ENABLED=true` | Bash syntax; PowerShell does not set env vars this way | Use `.env` file or `$env:EVENTS_ENABLED="true"` |
| `docker compose ...` → `dockerDesktopLinuxEngine` not found | **Docker Desktop is not running** | Open Docker Desktop, wait until it says Running, retry |
| `ModuleNotFoundError: pymysql` / `kafka` | Backend deps not installed | `pip install -r api/requirements.txt` |
| `No module named pyspark` | PySpark not installed | `.\scripts\run-spark-analytics.ps1` or Docker Spark job below |

### One-command setup

```powershell
cd C:\Users\Khale\Downloads\MT-NEW-main\MT-NEW-main
.\scripts\setup-events.ps1
```

This installs Python packages and creates `.env` + `frontend/.env` from examples.

### Environment variables

**Option A (recommended):** edit `.env` in project root (created by setup script):

```env
EVENTS_ENABLED=true
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
REDIS_URL=redis://localhost:6379/0
DB_HOST=localhost
DB_USER=root
DB_PASS=
DB_NAME=rag_jobs
GROQ_API_KEY=your_key_here
USE_SPARK=true
SPARK_MASTER=local[*]
```

**Option B:** current session only in PowerShell:

```powershell
$env:EVENTS_ENABLED = "true"
$env:KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"
$env:REDIS_URL = "redis://localhost:6379/0"
```

`frontend/.env`:

```env
VITE_API_URL=http://localhost:8000
VITE_EVENTS_ENABLED=true
```

### Docker (Kafka + Redis only)

1. Start **Docker Desktop**
2. Run:

```powershell
docker compose -f docker-compose.events.yml up -d
```

Uses official **`apache/kafka:3.8.1`** (KRaft, no Zookeeper). If an image tag fails, run `docker pull apache/kafka:3.8.1` first.

### Spark analytics (after workers write to `data/lake`)

**Option A — local PySpark (needs Java 11+):**

```powershell
.\scripts\run-spark-analytics.ps1
```

**Option B — Spark inside Docker (no local Java):**

```powershell
docker compose -f docker-compose.events.yml run --rm spark-analytics
```

Uses **`apache/spark:3.5.3`** with `spark-submit --master local[*]`. Report: `data/reports/latest.json` with `"engine": "pyspark"`.

**Option C — Spark cluster UI (thesis demo):**

```powershell
docker compose -f docker-compose.events.yml --profile spark-cluster up -d
```

Then set `SPARK_MASTER=spark://localhost:7077` and run `.\scripts\run-spark-analytics.ps1`. Spark UI: http://localhost:8082

### Run the stack

**Terminal 1 — API:**

```powershell
uvicorn backend.src.main:app --reload --port 8000
```

**Terminal 2 — workers** (only if `EVENTS_ENABLED=true` and Docker is up):

```powershell
python scripts/run_workers.py
```

**Terminal 3 — frontend:**

```powershell
cd frontend
npm run dev
```

**After some Kafka activity** — Spark report for Admin dashboard:

```powershell
.\scripts\run-spark-analytics.ps1
```

### Without Docker

Set in `.env`:

```env
EVENTS_ENABLED=false
```

The app uses the **original synchronous** CV parsing and chat (no Kafka/Redis required).

---

## Linux / macOS quick start

```bash
docker compose -f docker-compose.events.yml up -d
pip install -r api/requirements.txt
cp .env.example .env   # edit keys
uvicorn backend.src.main:app --reload --port 8000
python scripts/run_workers.py
```

Kafka UI: http://localhost:8080

## Topics

| Topic | Events |
|-------|--------|
| `application.events` | ApplicationSubmitted, CvParsed, ApplicationFailed |
| `job.events` | JobCreated, JobUpdated, JobDeleted |
| `chat.events` | ChatRequested, ChatCompleted, ChatFailed |

## Files

- [`docker-compose.events.yml`](../../docker-compose.events.yml)
- [`scripts/setup-events.ps1`](../../scripts/setup-events.ps1)
- [`scripts/run-spark-analytics.ps1`](../../scripts/run-spark-analytics.ps1)
- [`backend/src/events/`](../../backend/src/events/)
- [`backend/workers/`](../../backend/workers/)
- [`backend/spark_jobs/analytics_daily.py`](../../backend/spark_jobs/analytics_daily.py)

## Azure production vs local thesis demo

| Environment | `EVENTS_ENABLED` | Kafka/Workers | Spark report |
|-------------|------------------|---------------|--------------|
| **Azure (App Service)** | `false` | Not hosted — sync CV/chat | Run locally → `.\scripts\upload-spark-report.ps1` → Blob |
| **Local thesis** | `true` | `docker compose ... up -d` + `run_workers.py` | `spark-analytics` or `run-spark-analytics.ps1` |

Full Azure guide: **[docs/azure/DEPLOYMENT.md](../azure/DEPLOYMENT.md)**

## Thesis limitations

- Single Kafka broker
- Spark batch: PySpark `local[*]` or optional `spark-cluster` profile
- At-least-once delivery
