# **Real-time Voice Chat FastAPI Service Documentation (SMARTFLOW)**

---

## **Quick Start (Setup & Usage)**

### **Backend (FastAPI)**
1. Install Python dependencies:
   ```sh
   pip install -r requirements.txt
   ```
2. Ensure `ffmpeg` is installed and available in your PATH (required for audio conversion).
3. Start the backend server:
   ```sh
   py -m uvicorn main:app --reload
   ```
   Or use your preferred entrypoint (e.g., `py run.py`).

### **Frontend (React)**
1. Go to the `client` folder:
   ```sh
   cd client
   npm install
   npm start
   ```
2. The React app runs on [http://localhost:3000](http://localhost:3000) by default.

### **Configuration**
- Set environment variables in `.env` (see `config.py` for options):
  - `WS_AUTH_TOKEN` (optional, for WebSocket authentication)
  - Database, Pinecone, LLM, and API keys as needed

---

## **1. State (System Overview / Current State)**

* Users interact via **voice** and **text** (React frontend).
* Voice is **transcribed to text** using **Voxtral 24b** (DeepInfra/OpenAI-compatible API).
* Real-time voice streaming via **WebSocket** (browser → FastAPI backend).
* Text and voice input sent to a **single LLM model**.
* LLM response is augmented by **document context** stored in PDFs (indexed in Pinecone).
* **Chat history** is stored in **PostgreSQL**.
* **Documents** are **automatically indexed** into **Pinecone** vector DB.
* **Assets** (audio, PDFs) are stored locally in `assets/`.
* Modularized backend (services/streaming.py, services/stt.py, etc.) and frontend (React hooks for streaming).

---

## **2. Modules (Components)**

| Module      | Responsibility                                                    |
| ----------- | ----------------------------------------------------------------- |
| `routes`    | API endpoints: `/chat`, `/voice`, `/documents`                    |
| `services`  | Core logic: LLM, STT (Voxtral), vector DB (Pinecone), PDF parsing |
| `models`    | Pydantic schemas for request/response validation                  |
| `db`        | PostgreSQL connection and chat history queries                    |
| `assets`    | Storage for uploaded audio and documents                          |
| `config.py` | Centralized configuration for DB, Pinecone, LLM, Voxtral          |
| `client/`   | React frontend (audio recording, streaming, chat UI)              |
| `client/src/hooks/useWebSocketStream.js` | React hook for real-time voice streaming |

---

## **3. Actions (User & System Actions)**

1. **User sends voice** → transcribed by **Voxtral** → text stored in DB.
2. **User sends text message** → text stored in DB.
3. **System retrieves context** → searches Pinecone vector DB for top-k relevant documents.
4. **LLM generates reply** → combines user input + context → returns response.
5. **System stores reply** → text + optional audio reply + metadata.
6. **Document upload** → PDF parsed → embeddings stored in Pinecone automatically.


Index configured for llama-text-embed-v2:
Modality = Text
Vector type = Dense
Max input = 2,048 tokens
Starter limits = 5M tokens
Dimension = 1024
Metric = cosine


---

## **4. Routes (API Endpoints)**

| Route               | Method | Input                | Output                   | Description                                 |
| ------------------- | ------ | -------------------- | ------------------------ | ------------------------------------------- |
| `/voice/upload`     | POST   | Audio file, user\_id | Transcription, LLM reply | Upload audio, get transcription + LLM reply |
| `/chat/send`        | POST   | user\_id, text       | LLM reply                | Send text message, receive response         |
| `/documents/upload` | POST   | PDF file             | Status                   | Upload document, auto-index to Pinecone     |
| `/chat/history`     | GET    | user\_id             | List\[ChatMessage]       | Retrieve full chat history                  |

---

## **5. Tasks (Backend Processes)**

* **Transcribe audio** using Voxtral API.
* **Parse PDFs** using `pdfplumber` → extract text → generate embeddings.
* **Vector DB operations**: store & query embeddings in Pinecone.
* **Store chat history**: Postgres tables: `users`, `chats`, `documents`.
* **Generate LLM response** using context + user message.

---

## **6. Flows (Workflow Diagrams)**

### **Voice Chat Flow**

```
User -> /voice/upload -> STT (Voxtral) -> DB Store -> Context Retrieval (Pinecone)
    -> LLM Response -> DB Store -> Return reply to user
```

### **Document Upload Flow**

```
User -> /documents/upload -> PDF parse (pdfplumber)
    -> Generate embeddings -> Pinecone vector DB -> Indexed for context
```

### **Text Chat Flow**

```
User -> /chat/send -> DB Store -> Context Retrieval -> LLM -> DB Store -> Return
```

---

## **7. Links (Dependencies / Integrations)**

* **Voxtral 24b** for speech-to-text
* **OpenAI or internal LLM** for generating replies
* **Pinecone** for vector DB / semantic search
* **PostgreSQL** for chat history
* **pdfplumber** for PDF text extraction
* **FastAPI** for backend API
* **Starlette / WebSockets** for real-time streaming (optional)

---

## **8. Outputs (Expected Results)**

* **Text transcription** from audio
* **LLM replies** enhanced with document context
* **Stored chat history** for each user
* **Indexed document embeddings** in Pinecone
* **Real-time streaming of voice-to-text and LLM replies** (planned)

---

## **9. Warnings / Considerations**

* Real-time streaming requires WebSocket implementation.
* Audio files may be large → consider file size limits.
* Pinecone and LLM API calls are **rate-limited** → handle retries.
* PDF parsing can fail on encrypted or malformed files.
* Data privacy: all audio and chat history is stored in plain storage → consider encryption if needed.
* Automatic indexing may consume high compute if many PDFs are uploaded.

---

# **Project Phases for Real-time Voice Chat Service**

---

## **Phase 1: Core Text-based Chat**

**Objective:** Build the minimal functional system using text messages before adding audio streaming.

**Tasks:**

* Set up **FastAPI** project structure.
* Implement **PostgreSQL** connection and schema for users, chats, documents.
* Create **/chat/send** endpoint:

  * Accepts user text input.
  * Stores message in DB.
  * Generates **LLM response** (mock or real).
* Implement **document storage** & PDF parsing (manual upload).
* Integrate **Pinecone** vector DB for context retrieval.
* Test **text chat workflow** end-to-end.

**Deliverable:**

* Users can send text, get LLM replies with context from documents, and store chat history.

---

## **Phase 2: Audio Upload & Transcription**

**Objective:** Add voice input capability with file uploads.

**Tasks:**

* Implement **/voice/upload** endpoint:

  * Accept audio files (`.wav`, `.mp3`).
  * Store audio in `assets/audio/`.
  * Transcribe using **Voxtral API**.
  * Send transcription to LLM + retrieve context.
  * Store both transcription and LLM reply in DB.
* Implement Pydantic schemas for audio + transcription.
* Optional: generate audio reply if needed.

**Deliverable:**

* Users can upload voice files and get text replies with context.

---

## **Phase 3: Real-time Voice Streaming**

**Objective:** Enable live voice streaming and real-time transcription.

**Tasks:**

* Implement **WebSocket endpoints** for real-time audio streaming.
* Integrate **Voxtral streaming API** for live transcription.
* Stream transcription to client as it’s generated.
* Send partial/full transcription to LLM for near real-time replies.
* Handle multiple concurrent users.

**Deliverable:**

* Real-time voice chat with live transcription and LLM replies.

---

## **Phase 4: Automated Document Indexing**

**Objective:** Auto-index documents in Pinecone for semantic search.

**Tasks:**

* Implement **PDF upload endpoint** `/documents/upload`.
* Parse PDFs automatically using **pdfplumber**.
* Generate embeddings for each document segment.
* Store embeddings in **Pinecone** vector DB.
* Set up **automatic indexing** for new uploads.

**Deliverable:**

* All documents uploaded are automatically available for context retrieval in chats.

---

## **Phase 5: Chat History & Analytics**

**Objective:** Enhance user experience and system monitoring.

**Tasks:**

* Store full chat history: text + audio file references.
* Implement **/chat/history** endpoint.
* Add metadata: timestamps, document references, user IDs.
* Optional: analytics dashboard (most frequent queries, document usage, etc.)
* Implement pagination for chat history.

**Deliverable:**

* Users can view their complete chat history, including transcription and replies.

---

## **Phase 6: Optimization & Scalability**

**Objective:** Prepare system for production use.

**Tasks:**

* Optimize **Pinecone queries** for large datasets.
* Add **caching** for frequent document retrieval.
* Implement **background tasks** for heavy processes (audio transcription, PDF parsing, vector indexing).
* Add **rate-limiting** for API usage.
* Implement **security**: optional user authentication, encrypt stored audio and chat data.
* Logging and error monitoring.

**Deliverable:**

* Production-ready, scalable, secure real-time voice chat system.

---


