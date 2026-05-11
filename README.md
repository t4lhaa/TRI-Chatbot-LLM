<div align="center">

<img src="https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python" />
<img src="https://img.shields.io/badge/Framework-Flask-black?style=flat-square&logo=flask" />
<img src="https://img.shields.io/badge/LLM-GPT--4o--mini-412991?style=flat-square&logo=openai" />
<img src="https://img.shields.io/badge/Memory-ChromaDB-orange?style=flat-square" />
<img src="https://img.shields.io/badge/Architecture-ReAct%20%2B%20RAG-green?style=flat-square" />

# 🤖 TRI CHATBOT
### Autonomous Agent Architecture — ReAct + RAG + Dynamic Tool Execution

*An AI agent that reasons, acts, remembers — and never forgets.*

</div>

---

## 🧩 The Problem It Solves

Standard LLMs are **stateless**, **context-limited**, and **isolated** from the real world. They can't browse live data, run tools, or remember past conversations. TriChatbot solves all three:

| Problem | Solution |
|---------|----------|
| Context window limit | ChromaDB offloads old memory, retrieves it via cosine similarity |
| No real-world access | 12+ live tool integrations (weather, news, search, currency…) |
| Stateless per session | Per-user persistent memory + full session management |
| No file understanding | Parses PDF, DOCX, XLSX, CSV, code files up to 50 MB |

---

## 🧠 How It Works — The ReAct Loop

Every query goes through a structured 5-step reasoning pipeline:

```
User Query
    │
    ▼
┌─────────────────────────────────────────────────────┐
│  STEP 1 · THOUGHT     →  Agent reasons about query   │
│  STEP 2 · ACTION      →  Selects tool + JSON args    │
│  STEP 3 · OBSERVATION →  Receives tool output        │
│  STEP 4 · MEMORY      →  Stores/retrieves ChromaDB   │
│  STEP 5 · SYNTHESIS   →  Streams final answer        │
└─────────────────────────────────────────────────────┘
    │
    ▼
Streamed response (SSE)
```

The agent runs this loop **up to 10 times** per query until it reaches a confident answer.

---

## ✨ Features

### Core
- **ReAct loop** with multi-step reasoning and tool chaining
- **RAG memory** — ChromaDB stores conversation history as vector embeddings; retrieved via cosine similarity when context fills up → effectively **infinite memory**
- **Real-time streaming** via Server-Sent Events (SSE) — watch the agent think step by step

### Extra Work (Beyond Proposal)
- 🔒 **Per-user isolated memory** — each user gets their own `user_{username}_memory` ChromaDB collection; zero data leakage between accounts
- 👤 **Full auth system** — signup/login, SHA-256 password hashing, age verification, persistent sessions
- 🖼️ **Multimodal vision** — paste or upload images; agent reasons over base-64 encoded visuals
- 📁 **50 MB file engine** — upload PDF, DOCX, XLSX, CSV, C++, Python (30+ formats); parsed and injected into context
- 🌐 **Live API integrations** — Weather, News, Currency Exchange; all keys secured in `.env` (never hardcoded)
- 🌙 **Dark/Light mode UI** with a polished, responsive chat interface

---

## 🛠️ Tools Available

```
Calculator        Web Search (DuckDuckGo)    Wikipedia
Weather           News Headlines             Country Info
Currency Converter  Dictionary               File Reader
ChromaDB Memory   Image Vision              File Upload
```

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────┐
│              Browser (index.html)            │
│   Dark/Light UI · Auth · Chat · File Upload  │
└─────────────────────┬────────────────────────┘
                      │ HTTP / SSE
┌─────────────────────▼────────────────────────┐
│              Flask Server (run.py)           │
│  Sessions · Auth · File Ingestion · Routing  │
└─────────────────────┬────────────────────────┘
                      │
┌─────────────────────▼────────────────────────┐
│              AI Agent (agent.py)             │
│                                              │
│  ┌─────────────┐    ┌─────────────────────┐  │
│  │  ReAct Loop │    │   ChromaDB (RAG)    │  │
│  │  5-step     │◄──►│   cosine similarity │  │
│  │  reasoning  │    │   per-user isolated │  │
│  └──────┬──────┘    └─────────────────────┘  │
│         │                                    │
│  ┌──────▼──────────────────────────────────┐ │
│  │         12+ Tool Functions              │ │
│  │  Weather · News · Search · Currency…   │ │
│  └─────────────────────────────────────────┘ │
└──────────────────────────────────────────────┘
                      │
              OpenRouter API
              (gpt-4o-mini)
```

---

## 📦 Tech Stack

| Layer | Technology |
|-------|-----------|
| LLM | OpenRouter API — `gpt-4o-mini` |
| Embeddings | `sentence-transformers` — `all-MiniLM-L6-v2` |
| Vector Memory | ChromaDB |
| Backend | Flask + Flask-CORS |
| Streaming | Server-Sent Events (SSE) |
| Frontend | HTML / CSS / JavaScript |
| Document Parsing | PyMuPDF · python-docx · openpyxl |
| Security | `python-dotenv` — keys in `.env` only |

---

## 🗂️ Project Structure

```
trichatbot/
├── agent.py        # ReAct loop · ChromaDB RAG · tool dispatch · embeddings
├── run.py          # Flask server · auth · sessions · file ingestion · SSE
├── index.html      # Web UI · dark/light mode · streaming chat · file upload
├── requirements.txt
└── .env.example
```

---

## 🔐 Security

- API keys loaded via `python-dotenv` — **never exposed** in source code or frontend
- Passwords hashed with **SHA-256** before storage
- Each user's memory is **sandboxed** in a separate ChromaDB collection
- `.env` is gitignored by default

---

## ✅ Tested For

- **Context overflow** — extended 100+ turn conversations; ChromaDB offload and retrieval verified
- **Tool dispatch** — JSON schema arguments validated across all 12 tools
- **Memory isolation** — confirmed users cannot access each other's stored memories
- **File parsing** — PDF, DOCX, XLSX, CSV, Python, C++ files all parsed and injected correctly

---

## 🏁 Conclusion

TriChatbot proves that combining ReAct + RAG turns a standard LLM into something genuinely useful — infinite memory via ChromaDB, live tool execution, and full user isolation. The extra work (multimodal vision, auth system, file engine, streaming UI, secure .env) pushed it well beyond a course project into something production-ready. The architecture is modular, so swapping the LLM or adding new tools is trivial. Solid foundation for anything built on top.
