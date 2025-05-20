# 🧠 Multi-Agent Orchestrator with RAG, Web Search, and More – Backend

This is the backend component for a multi-agent orchestration system with support for RAG (Retrieval-Augmented Generation), web search, and task execution via FastAPI, Celery, Redis, PostgreSQL, and Qdrant.

---

## 📁 Project Structure

```bash
backend/
├── api/                        # FastAPI routers and endpoints
├── data/                       # Volume mounts (Postgres, Redis, Qdrant)
├── logs/                       # Logs directory
├── src/                        # Core logic, services, workers
├── venv/                       # Python virtual environment (excluded in .gitignore)
├── .env.example                # Environment variable template
├── .env                        # Your local environment config
├── app_fastapi.py              # FastAPI entry point
├── docker-compose.dev.yaml     # Docker Compose for development
├── docker-compose.prod.yaml    # Docker Compose for production
├── Dockerfile.api.dev          # FastAPI dev Dockerfile
├── Dockerfile.api.prod         # FastAPI production Dockerfile
├── Dockerfile.worker           # Celery worker Dockerfile
├── requirements.txt            # Python dependencies for API
├── requirements.worker.txt     # Python dependencies for Celery worker
└── README.md                   # This documentation
```

---

## 📦 1. Installation and Setup

### 1.1. Prerequisites

* [Docker](https://docs.docker.com/get-docker/)
* [Git](https://git-scm.com/downloads)
* Python 3.9+

### 1.2. Clone and Setup

```bash
git clone https://github.com/buithanhdam/maowrag-unlimited-ai-agent.git
cd maowrag-unlimited-ai-agent/backend
```

### 1.3. Create a Virtual Environment

* **macOS/Linux**:

  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

* **Windows**:

  ```bash
  python -m venv venv
  .\venv\Scripts\activate
  ```

### 1.4. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 🔧 2. Environment Variables Setup

1. Copy the example file:

   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your keys and configuration:

```env
# API Keys
GOOGLE_API_KEY=
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
TAVILY_API_KEY=

# URLs
BACKEND_API_URL=
QDRANT_URL=
CELERY_BROKER_URL=

# PostgreSQL
DB_USER=postgres
DB_PASSWORD=1
DB_HOST=postgres
DB_PORT=5432
DB_NAME=maowrag

# AWS
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION_NAME=ap-southeast-2
AWS_STORAGE_TYPE=s3
AWS_ENDPOINT_URL=https://s3.ap-southeast-2.amazonaws.com
```

---

## 🚀 3. Running the Application Locally

### 3.1. Install FFmpeg for media processing

* **Ubuntu**:

  ```bash
  sudo apt install ffmpeg
  ```

* **macOS**:

  ```bash
  brew install ffmpeg
  ```

* **Windows**:

  1. Download from [ffmpeg.org](https://ffmpeg.org/download.html)
  2. Add `ffmpeg/bin` to PATH
  3. Verify: `ffmpeg -version`

### 3.2. Run Services (PostgreSQL, Qdrant, Redis) with Docker

You can manually start each one using Docker images or use Docker Compose (see section 5).

### 3.3. Run Celery Worker

```bash
celery -A src.celery_worker worker --loglevel=info
```

### 3.4. Run FastAPI App

```bash
uvicorn app_fastapi:app --host 0.0.0.0 --port 8000 --reload
```

Visit [http://localhost:8000](http://localhost:8000)

---

## 🐳 4. Using Docker

### 4.1. Start All Services (Dev)

```bash
docker-compose -f docker-compose.dev.yaml up --build
```

### 4.2. Services Included

| Service         | Port(s)    | Dockerfile           |
| --------------- | ---------- | -------------------- |
| FastAPI Backend | 8000       | `Dockerfile.api.dev` |
| PostgreSQL      | 5432       | official image       |
| Qdrant          | 6333, 6334 | official image       |
| Redis           | 6379       | official image       |
| Celery Worker   | N/A        | `Dockerfile.worker`  |

### 4.3. Stop All Services

```bash
docker-compose -f docker-compose.dev.yaml down
```

### 4.4. Network

* Docker network: `maowrag-backend-dev` (bridge)

---

## 🧰 5. Troubleshooting

* Make sure `.env` is properly configured.
* Check if any ports (e.g. 8000, 5432, 6379, 6333) are already in use.
* Use `--build` when updating Docker:

  ```bash
  docker-compose -f docker-compose.dev.yaml up --build
  ```