# LLM Chat Prototype

A small, clean chatbot you can build on. React chat UI, a FastAPI backend, and
real streaming responses from OpenAI, Anthropic or Gemini behind a single
adapter. It also ships with a mock provider, so it runs end to end with no API
key while you work on the UI.

Author: A. Amini

## What it does

- Chat interface with streaming replies, token by token
- Conversation context kept on the client and sent with each turn
- A configurable system prompt
- One provider interface, four implementations (mock / OpenAI / Anthropic / Gemini)
- Basic error handling surfaced in the UI
- New conversation / reset
- A bounded history window so the context sent to the model stays controlled

Out of scope on purpose: auth, analytics, RAG, persistence. This is a base to
build on, not a product.

## How it is put together

```
backend/        FastAPI
  app/
    main.py            /api/chat (streaming), /api/health, /api/config
    config.py          settings from .env
    schemas.py         request/response models
    providers/
      base.py          the LLMProvider interface
      mock.py          canned streaming reply, no key needed
      openai_provider.py
      anthropic_provider.py
      gemini_provider.py
      factory.py       picks the provider from config
frontend/       React + Vite
  src/
    App.jsx            chat state, streaming render, reset
    api.js             reads the streamed response
    styles.css
```

The backend streams Server-Sent Events. Each frame is one JSON object:
`{"type":"token","value":"..."}`, then a final `{"type":"done"}`, or
`{"type":"error","message":"..."}` if a provider fails. The frontend reads the
stream and appends tokens to the last message as they arrive.

Context is handled on the client: the browser holds the full message list and
sends it with every request. The backend trims it to the last `MAX_HISTORY`
turns before calling the model, which keeps token cost bounded. For a prototype
this is simpler and cheaper than a server-side session store, and it is easy to
move server-side later if needed.

## Run it

### 1. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

It starts on the mock provider, so it works right away.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The dev server proxies `/api` to the backend.

## Use a real model

Edit `backend/.env`:

```env
PROVIDER=openai
MODEL=gpt-4o-mini
API_KEY=sk-...
```

Or Anthropic:

```env
PROVIDER=anthropic
MODEL=claude-3-5-sonnet-latest
API_KEY=sk-ant-...
```

Or Gemini:

```env
PROVIDER=gemini
MODEL=gemini-1.5-flash
API_KEY=...
```

Install only the SDK you use; the others are imported lazily. Restart the
backend after changing `.env`. The provider and model show in the top-right
badge in the UI.

## Adding another provider

Implement `LLMProvider.stream()` in a new file under `app/providers/`, then add
one branch to `factory.py`. The rest of the app does not change.
