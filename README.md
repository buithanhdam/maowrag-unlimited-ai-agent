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
5. [Running Backend Only as API](#5-running-backend-only-as-api)
6. [Running the Project with Docker](#6-running-the-project-with-docker)
7. [Project Structure](#7-project-structure)
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

## 5. Running Backend Only as API

To run the backend separately, follow the instructions in the [backend README](backend/README.md).

---

## 6. Running the Project with Docker

### Prerequisites

- [Install Docker](https://docs.docker.com/get-docker/)
- [Install Docker Compose](https://docs.docker.com/compose/install/)

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

and fill values:

```plaintext
# For backend .env
GOOGLE_API_KEY=<your_google_api_key>
OPENAI_API_KEY=<your_openai_api_key>
ANTHROPIC_API_KEY=<your_anthropic_api_key>
BACKEND_API_URL=http://localhost:8000
QDRANT_URL=http://localhost:6333

MYSQL_USER=your_mysql_user
MYSQL_PASSWORD=your_mysql_password
MYSQL_HOST=your_mysql_host
MYSQL_PORT=your_mysql_port
MYSQL_DB=your_mysql_db
MYSQL_ROOT_PASSWORD=root_password

AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION_NAME=
AWS_STORAGE_TYPE=
AWS_ENDPOINT_URL=

# For frontend .env
NEXT_PUBLIC_BACKEND_API_URL=http://localhost:8000
```

#### 3. Build and Run the Project

```bash
docker-compose up --build
```

#### 4. Set Up MySQL Database (if needed)

```bash
docker exec -it your-container-name mysql -u root -p
```
- Enter `root password` (configured in `.env` or `docker-compose.yml`).

Run SQL queries:

```sql
CREATE USER 'user'@'%' IDENTIFIED BY '1';
GRANT ALL PRIVILEGES ON maowrag.* TO 'user'@'%';
FLUSH PRIVILEGES;
CREATE DATABASE maowrag;
```

#### 5. Access the Application

- **Frontend**: `http://localhost:3000`
- **Backend**: `http://localhost:8000`
- **Qdrant**: Ports `6333`, `6334`
- **MySQL**: Port `3306`

#### 6. Stop the Project

```bash
docker-compose down
```

---

## 7. Project Structure

```
📦 maowrag-unlimited-ai-agent
├── backend/       # Backend source code
│   ├── Dockerfile.backend
│   ├── requirements.txt
├── frontend/      # Frontend source code
│   ├── Dockerfile.frontend
│   ├── next.config.js
├── docker-compose.yml  # Docker Compose setup
├── Jenkinsfile    # CI/CD configuration
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