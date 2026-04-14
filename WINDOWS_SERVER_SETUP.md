# Windows Server Setup

This file lists the exact steps to move and run the `Audit-agent` application on another Windows server.

## 1. Prerequisites

- Windows Server with PowerShell access
- Python `3.13.x` installed and available as `py -3.13`
- Git installed
- Redis-compatible service running on the server
  - Recommended for Windows: `Memurai`
- Internet access for `pip install`
- OpenAI API key if using OpenAI
- Ollama installed only if using Ollama for chat/embeddings

## 2. Copy The Code

Clone or copy the repo to the target server:

```powershell
cd C:\
git clone <YOUR_GITHUB_REPO_URL> Audit-agent
cd C:\Audit-agent
```

If you are copying a ZIP instead of cloning, extract it to:

```text
C:\Audit-agent
```

## 3. Create Virtual Environment

Create a fresh environment on the server:

```powershell
cd C:\Audit-agent
py -3.13 -m venv .venv-clean
.\.venv-clean\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

## 4. Configure Environment Variables

Create `.env` from the template:

```powershell
Copy-Item .env.example .env
```

Update `.env` with real values.

Minimum required values:

```env
OPENAI_API_KEY=your-real-key
OPENAI_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small

DATABASE_URL=sqlite:///./audit_agent.db
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
USE_MOCK_TASK=false
SECRET_KEY=put-a-long-random-secret-here
API_HOST=0.0.0.0
API_PORT=8000
```

If using Ollama instead of OpenAI:

```env
LLM_PROVIDER=ollama
LLM_MODEL=qwen3:8b
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=nomic-embed-text
OLLAMA_BASE_URL=http://localhost:11434
```

## 5. Start Redis / Memurai

The app requires Redis for Celery.

If using Memurai, ensure the service is running before starting backend or worker.

Default broker/backend expected by the app:

```text
redis://localhost:6379/0
```

## 6. Initialize Database

Run this once on the new server:

```powershell
cd C:\Audit-agent
.\.venv-clean\Scripts\Activate.ps1
python -m backend.app.core.init_db
```

This creates the SQLite DB and seeds the default admin user.

Default demo login:

```text
username: admin
password: admin123
```

Change it later if needed.

## 7. Start The Application

Open 3 separate terminals.

### Terminal 1: Backend

```powershell
cd C:\Audit-agent
.\.venv-clean\Scripts\Activate.ps1
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

### Terminal 2: Worker

```powershell
cd C:\Audit-agent
.\.venv-clean\Scripts\Activate.ps1
powershell -ExecutionPolicy Bypass -File .\start_celery.ps1
```

### Terminal 3: Frontend

```powershell
cd C:\Audit-agent
.\.venv-clean\Scripts\Activate.ps1
python -m http.server 3000 --bind 127.0.0.1 -d frontend
```

## 8. Verify The App

Check these URLs:

- Frontend: `http://127.0.0.1:3000`
- Backend docs: `http://localhost:8000/docs`
- Backend health: `http://localhost:8000/`

Run import checks if needed:

```powershell
python -c "from backend.app.core.rag_service import RAGService; print('rag import ok')"
python -c "from backend.app.main import app; print('app import ok')"
```

## 9. Verify End-To-End Flow

After login, test this sequence:

1. Submit one audit
2. Confirm it appears in `My Audits`
3. Confirm worker picks it up
4. Open results
5. Open `Fix It` chat and ask one question

## 10. Optional Cleanup Before Move

Do not copy local virtualenv folders to the server.

These should not be committed or copied:

- `.venv-clean/`
- `venvagent/`
- `.pytest_cache/`

You may also choose not to move local generated data:

- `chroma_db/`
- `audit_agent.db`

If you want a clean server install, let the new server regenerate them.

## 11. Optional Production Hardening

For a more stable server setup later:

- run backend as a Windows service
- run worker as a Windows service
- run Redis/Memurai as a service
- place frontend behind IIS or Nginx instead of `http.server`
- replace SQLite with PostgreSQL for multi-user/server usage
- secure `.env` and rotate API keys
- configure Windows Firewall for ports `8000` and `3000` if remote access is required

## 12. Common Commands

Reinstall dependencies:

```powershell
pip install -r requirements.txt
```

Restart backend:

```powershell
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

Restart worker:

```powershell
powershell -ExecutionPolicy Bypass -File .\start_celery.ps1
```

Restart frontend:

```powershell
python -m http.server 3000 --bind 127.0.0.1 -d frontend
```

## 13. Important Notes

- This app currently expects port `8000` for backend and `3000` for frontend.
- The frontend is static HTML/JS, not a Node app.
- Celery worker is required for real audit processing.
- RAG / Fix-It chat depends on the configured embedding provider and a working vector store.
- If using OpenAI, make sure outbound HTTPS access to the OpenAI API is allowed from the server.
