# Multi-Agent Orchestrator with RAG, Web Search, and More

## Overview

This repository is an advanced implementation of AI agent techniques, focusing on:

- **Multi-Agent Orchestration** for coordinating multiple agents in AI workflows.
- **Retrieval-Augmented Generation (RAG)** framework to improve AI-generated responses.
- **AI Agent Techniques** such as **Planning (ReAct flow)**, **Reflection**, etc. for enhanced reasoning.

## Table of Contents

1. [Multi-Agent Orchestrator](#1-multi-agent-orchestrator)
2. [Introduction to RAG](#2-introduction-to-rag)
3. [Advanced RAG Techniques](#3-advanced-rag-techniques)
4. [Other AI Technologies](#4-other-ai-technologies)
5. [Running Frontend Only as API](#5-running-frontend-only-as-api)
6. [Running Backend Only as API](#6-running-backend-only-as-api)
7. [Running the Project with Docker](#7-running-the-project-with-docker)
8. [Contributing](#8-contributing)
9. [License](#9-license)
10. [References](#10-references)

---

## 1. Multi-Agent Orchestrator

This project enhances LLM capabilities using **multi-agent workflows**, integrating:

- **ReAct** for planning and execution.
- **Reflection** for iterative learning.
- **Multi-Agent Coordination** for complex problem-solving.

### Workflow:

1. User input is classified to determine the appropriate agent.
2. The orchestrator selects the best agent based on historical context and agent capabilities.
3. The selected agent processes the input and generates a response.
4. The orchestrator updates conversation history and returns the response.

For further exploration:

- [Agentic Patterns Repo](https://github.com/neural-maze/agentic_patterns/)
- [Multi-Agent Orchestrator](https://github.com/awslabs/multi-agent-orchestrator)

![Multi-Agent Workflow](https://raw.githubusercontent.com/awslabs/multi-agent-orchestrator/main/img/flow.jpg)

---

## 2. Introduction to RAG

Large Language Models (LLMs) have limitations in handling private or recent data. The **Retrieval-Augmented Generation (RAG)** framework mitigates this by retrieving relevant external documents before generating responses.

![final diagram](https://github.com/user-attachments/assets/508b3a87-ac46-4bf7-b849-145c5465a6c0)

### Key Components of RAG:

1. **Indexing:** Splits documents into chunks, creates embeddings, and stores them in a vector database.
2. **Retriever:** Finds the most relevant documents based on the user query.
3. **Augment:** Combines retrieved documents with the query for context.
4. **Generate:** Uses the LLM to generate accurate responses.

---

## 3. Advanced RAG Techniques

This repository supports several advanced RAG techniques:

| Technique        | Tools                                                  | Description                                                            |
| ---------------- | ------------------------------------------------------ | ---------------------------------------------------------------------- |
| Naive RAG        | LlamaIndex, Qdrant, Google Gemini                      | Basic retrieval-based response generation.                             |
| Hybrid RAG       | LlamaIndex, Qdrant, Google Gemini                      | Combines vector search with BM25 for better results.                   |
| Hyde RAG         | LlamaIndex, Qdrant, Google Gemini                      | Uses hypothetical document embeddings to improve retrieval accuracy.   |
| RAG Fusion       | LlamaIndex, LangSmith, Qdrant, Google Gemini           | Generates sub-queries, ranks results using Reciprocal Rank Fusion.     |
| Contextual RAG   | LlamaIndex, Qdrant, Google Gemini, Anthropic           | Compresses retrieved documents to keep only the most relevant details. |
| Unstructured RAG | LlamaIndex, Qdrant, FAISS, Google Gemini, Unstructured | Handles text, tables, and images for diverse content retrieval.        |

---

## 4. Other AI Technologies

- 🤖 Supports **Claude 3**, **GPT-4**, **Gemini**. For optimal performance: Use the **Gemini** family of models.
- 🧠 Advanced AI planning and reasoning capabilities
- 🔍 Contextual keyword extraction for focused research
- 🌐 Seamless web browsing and information gathering
- 💻 Code writing in multiple programming languages
- 📊 Dynamic agent state tracking and visualization
- 💬 Natural language interaction via chat interface
- 📂 Project-based organization and management
- 🔌 Extensible architecture for adding new features and integrations

---

## 5. Running Frontend Only as API

### 5.1 Run Frontend Separately (Optional)

```bash
cd frontend
npm install
npm run dev
```

- Access API: http://localhost:3000

### 5.2 Frontend Features

* Prompt interface for multi-agent tasks
* Drag and drop file upload
* Agent memory and conversation UI
* Integration with backend via REST APIs

---

## 6. Running Backend Only as API
* Located in `backend/`
* Provides RAG, web search, knowledge ingestion, and task orchestration
* Uses:

  * PostgreSQL (structured memory)
  * Qdrant (vector store for embeddings)
  * Redis (task queue)
  * FFmpeg (audio/video support)

To run the backend separately, follow the instructions in the [backend README](backend/README.md).

---

## 7. Running the Project with Docker

### Prerequisites

- [Install Docker](https://docs.docker.com/get-docker/)
- [Install Docker Compose](https://docs.docker.com/compose/install/)

### Prerequisites for Audio/Video Processing

To process audio/video files, FFmpeg is required:

#### For Ubuntu/Debian
```bash
sudo apt update
sudo apt install ffmpeg
```

#### For macOS (Homebrew)
```bash
brew install ffmpeg
```

#### For Windows
1. Download FFmpeg from [FFmpeg official website](https://ffmpeg.org/download.html).
2. Extract the files and add the `bin` folder to your system's PATH.
3. Restart your terminal and verify installation with:
   ```bash
   ffmpeg -version
   ```

### Steps

#### 1. Clone the Project

```bash
git clone https://github.com/buithanhdam/maowrag-unlimited-ai-agent.git
cd maowrag-unlimited-ai-agent
```

#### 2. Configure Environment Variables

```bash
cp ./frontend/.env.example ./frontend/.env
cp ./backend/.env.example ./backend/.env
```
and fill values

- For backend:
```plaintext
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
- For backend:

```plaintext
# For frontend .env
NEXT_PUBLIC_BACKEND_API_URL=http://localhost:8001
```

#### 3. Build and Run the Project

```bash
docker-compose up --build
```

This will launch:

| Service            | Port    | Description                |
| ------------------ | ------- | -------------------------- |
| FastAPI API        | `:8000` | Backend API                |
| Frontend (Next.js) | `:3000` | Web UI                     |
| PostgreSQL         | `:5432` | Database                   |
| Redis              | `:6379` | Celery broker              |
| Qdrant             | `:6333` | Vector DB                  |
| Celery Worker      | N/A     | Background task processing |

#### 4. Access the Application

- Frontend UI: http://localhost:3000
- Backend API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

#### 5. Stop the Project

```bash
docker-compose down
```

---

## 8. Contributing

Contributions are welcome! Please submit an issue or a pull request to improve this project.

---

## 9. License

This project is licensed under the MIT License.

---

## 10. References

- [Agentic Patterns Repo](https://github.com/neural-maze/agentic_patterns/)
- [Multi-Agent Orchestrator](https://github.com/awslabs/multi-agent-orchestrator)
- [kotaemon](https://github.com/Cinnamon/kotaemon)
- [multi-agent](https://github.com/buithanhdam/multi-agent)
- [RAG Cookbook](https://github.com/athina-ai/rag-cookbook)
- [RAG-application-with-multi-agent](https://github.com/buithanhdam/rag-app-agent-llm)