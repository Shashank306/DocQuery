# DocQuery - RAG-based Document Chat App

DocQuery is a full-stack application allowing users to upload documents and interact with them via a chatbot interface. It utilizes Hybrid Retrieval-Augmented Generation (RAG) combining dense and keyword-based retrieval for intelligent Q&A.

---

## ⚙️ Tech Stack

### 🔧 Backend
- **FastAPI**
- **SQLModel** (with SQLite or PostgreSQL)
- **LangChain** (document loading, text splitting)
- **Weaviate** (Hybrid search - vector + BM25)
- **GROQ LLM**
- **JWT Authentication**
- **Pydantic Settings** (for `.env` config)
- **Structured Logging** (`structlog`)

### 🎨 Frontend
- **Vite + ReactJS**
- **Tailwind CSS**
- **Axios** for HTTP calls
- **React Router**, **Toast**, and Modal-based UX

---

## 🔐 Authentication

- JWT-based Auth (Access + Refresh tokens)
- `/signup`, `/login`, `/me` endpoints
- Role-based routes can be easily added

---

## 📁 Document Upload + Ingestion

- Supports folder-based upload via modal
- Accepts `.pdf`, `.txt`, `.csv`, `.json`
- Ingests docs using `DirectoryLoader`, extracts + chunks text
- Metadata (file name, user_id, etc.) is stored
- Uses **LangChain** + **Weaviate** for vector/BM25 indexing

---

## 💬 Chat with Docs (Hybrid RAG)

- Each user creates sessions (chat threads)
- For each session:
  - Upload folder of documents
  - Ask context-aware questions
  - See updated session name based on first question
- Uses Hybrid retrieval:
  - Dense vector similarity (OpenAI/GROQ embeddings)
  - BM25 keyword relevance
- Session + history-aware prompts

---

## 🧠 Vector Store

- **Weaviate** with:
  - Hybrid search (BM25 + vector)
  - User/session-based filtering
- Indexes:
  - Document chunks
  - Metadata for traceability

---

## 🌐 Routes

### API Endpoints

#### Auth
- `POST /api/v1/auth/signup`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`

#### Sessions
- `GET /api/v1/sessions/sessions`
- `POST /api/v1/sessions/sessions`

#### Upload
- `POST /api/v1/upload/batch/folder`

#### Search
- `POST /api/v1/query/search`
- `GET /api/v1/query/history?skip=0&limit=100`

---

## ⚠️ File Constraints

- Upload only allowed extensions: `.pdf`, `.txt`
- Max file size configurable in `.env`
- Rate-limited upload endpoints
- Secure MIME checks + extension whitelist

<!-- ---

<!-- ## ✅ To Do (For Deployment Readiness)

- [ ] Add HTTPS + Docker Compose
- [ ] Add LLM switcher (OpenRouter, Together, Groq, Ollama)
- [ ] Use persistent DB (PostgreSQL)
- [ ] Add retry + backoff logic in frontend
- [ ] File deduplication
- [ ] Chunk deduplication via hashing
- [ ] Semantic document highlighting
- [ ] Delete/edit chats -->

--- -->

## 📦 Folder Structure
```
├── backend/
│ ├── app/
│ │ ├── auth/ # JWT logic, hashing, Pydantic models
│ │ ├── ingestion/ # Document loading, chunking
│ │ ├── retrieval/ # Weaviate hybrid logic
│ │ ├── llm/ # Search + prompt building
│ │ ├── models/ # SQLModel definitions
│ │ ├── api/ # Route grouping
│ │ ├── core/ # Config, logging
│ │ └── main.py # FastAPI entrypoint
│ └── requirements.txt
├── frontend/
│ ├── src/
│ │ ├── components/ # Sidebar, ButtonLoading,Uplaoding
│ │ ├── pages/ # Login, Signup, Chat
│ │ ├── utils/ # Auth headers, toasts, axios
│ │ └── main.jsx # Root entry
│ └── index.html
└── README.md
```


## 🔑 ENV Sample
```
# .env
SECRET_KEY=your_jwt_secret_key
ACCESS_TOKEN_EXPIRE_MINUTES=60
DATABASE_URL=sqlite:///./rag_db.db
WEAVIATE_HOST=http://localhost:8080
GROQ_API_KEY=your_key
```

🚀 Running Locally
1. Clone repo
2. Start Weaviate (Docker)
3. Run backend:

cd backend
uvicorn app.main:app --reload

4.Run frontend:

cd frontend
npm install
npm run dev

