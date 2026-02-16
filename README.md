# ARIS — AI-Powered Socratic Tutor

ARIS is an interactive whiteboard app that pairs an **Excalidraw canvas** with an **AI tutor**. Students draw, write, or diagram on the canvas, then talk to ARIS via voice — ARIS sees the canvas, hears the student, and responds with Socratic guidance in real time.

## Architecture

| Layer | Tech | Purpose |
|-------|------|---------|
| **Frontend** | React 19 + Vite + TypeScript | Excalidraw canvas + voice UI |
| **Backend** | FastAPI + Uvicorn | Vision analysis, speech-to-text/TTS, Socratic response generation |
| **AI** | OpenAI GPT-4o-mini, Whisper, TTS | Canvas understanding, transcription, voice responses |

```
┌─────────────┐        HTTP / WS        ┌─────────────┐       ┌───────────┐
│   Frontend   │ ◄────────────────────► │   Backend    │ ◄───► │  OpenAI   │
│  :5173       │   /talk  /analyze      │  :8000       │       │  API      │
│  Excalidraw  │   /stream              │  FastAPI     │       └───────────┘
└─────────────┘                         └─────────────┘
```

---

## Prerequisites

- **Python 3.11+**
- **Node.js 18+** and **npm**
- An **OpenAI API key** ([platform.openai.com](https://platform.openai.com))

---

## Getting Started

### 1. Clone the repo

```bash
git clone https://github.com/kjoshiDTX/aris.git
cd aris
```

> The `backend` and `frontend` live on separate branches. Check out the branch you need:
>
> ```bash
> git checkout backend    # backend source only
> git checkout frontend   # frontend source only
> ```

---

### 2. Backend Setup

```bash
git checkout backend
cd backend
```

#### Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
```

#### Install dependencies

```bash
pip install -r requirements.txt
```

#### Configure environment variables

Create a `.env` file in the `backend/` directory:

```env
OPENAI_API_KEY=sk-your-key-here
OPENAI_TTS_VOICE=alloy          # Options: alloy, echo, fable, onyx, nova, shimmer
```

#### Run the server

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at **http://localhost:8000**. Verify with:

```bash
curl http://localhost:8000/health
```

---

### 3. Frontend Setup

Open a **new terminal**:

```bash
git checkout frontend
cd frontend
```

#### Install dependencies

```bash
npm install
```

#### (Optional) Configure backend URL

By default the frontend connects to `http://localhost:8000`. To change this, create a `.env` file:

```env
VITE_BACKEND_URL=http://localhost:8000
```

#### Start the dev server

```bash
npm run dev
```

The app will open at **http://localhost:5173**.

---

## Usage

1. Open **http://localhost:5173** in your browser.
2. Draw, write, or diagram on the Excalidraw canvas.
3. Click **🎙️ Talk to ARIS** and speak your question.
4. Click **⏹️ Stop & Send** — ARIS will:
   - Transcribe your speech
   - Analyze what's on the canvas
   - Respond with Socratic guidance via audio

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Service health check |
| `POST` | `/talk` | Voice interaction — send audio + canvas image, get audio response |
| `POST` | `/analyze` | Canvas analysis — send image, get Socratic text feedback |
| `WS` | `/stream` | Real-time audio streaming (WebSocket) |

---

## Project Structure

```
backend/
├── main.py                 # FastAPI app, routes, lifespan
├── prompts.py              # System prompts for Socratic tutoring
├── requirements.txt        # Python dependencies
└── services/
    ├── speech_service.py   # Whisper STT + OpenAI TTS
    └── vision_service.py   # GPT-4o vision analysis

frontend/
├── index.html
├── package.json
├── vite.config.ts
└── src/
    ├── App.tsx             # Main app — Excalidraw + voice UI
    ├── App.css             # Styles
    ├── hooks/
    │   ├── useAudioStream.ts
    │   └── useDebounce.ts
    └── utils/
        └── canvasUtils.ts  # Canvas capture helper
```

---

## License

MIT
