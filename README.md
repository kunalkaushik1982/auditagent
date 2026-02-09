# Delivery Audit Agent

A multi-agent AI-powered system for automating quality audits across enterprise project deliverables.

## Overview

The Delivery Audit Agent standardizes and automates quality checks for project deliverables in large enterprise environments. It uses AI-powered validation to replace manual, time-consuming audit processes with intelligent, consistent feedback.

## Key Features (Phase 1)

- **Three Specialized Agents**:
  - SoW Reviewer Agent
  - Project Plan Reviewer Agent
  - Architecture Compliance Agent

- **Intelligent Validation**: AI-powered analysis using LangChain/LangGraph and OpenAI GPT
- **Asynchronous Processing**: Queue multiple audits, run in parallel
- **Real-time Monitoring**: Dashboard showing audit status (pending, running, completed, failed)
- **Dual Output Format**: Inline annotations + detailed audit reports
- **Notification System**: In-app alerts when audits complete

## Technology Stack

### Backend
- **FastAPI** - Modern async Python web framework
- **LangChain/LangGraph** - AI orchestration and workflow management
- **OpenAI GPT** - Natural language understanding and reasoning
- **Celery + Redis** - Asynchronous task queue for parallel processing
- **SQLAlchemy** - Database ORM
- **SQLite** - Database (Phase 1, migrates to RDBMS later)

### Frontend
- **Vanilla JavaScript** - No framework dependencies
- **HTML5 & CSS3** - Modern responsive design
- **WebSocket/Polling** - Real-time status updates

### Document Processing
- **LangChain Loaders** - Word documents and text files (Phase 1)

## Project Structure

```
Audit-agent/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── agents/         # AI agent implementations
│   │   ├── api/            # API endpoints
│   │   ├── core/           # Core configuration
│   │   ├── models/         # Database models
│   │   ├── services/       # Business logic
│   │   └── tasks/          # Celery tasks
│   ├── uploads/            # Uploaded artifacts
│   └── reports/            # Generated reports
├── frontend/               # Vanilla JS/HTML/CSS frontend
│   ├── css/
│   ├── js/
│   └── index.html
├── .env.example            # Environment variables template
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## Setup Instructions

### Prerequisites
- Python 3.9+
- Redis/Memurai (for task queue)
- OpenAI API key

### Installation

1. **Clone the repository**
   ```bash
   cd C:\Users\work\Documents\Audit-agent
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Redis/Memurai** (Windows)
   - Download Memurai from https://www.memurai.com/
   - Install and run as Windows service

4. **Configure environment variables**
   ```bash
   copy .env.example .env
   # Edit .env file with your OpenAI API key and other settings
   ```

5. **Initialize the database**
   ```bash
   python -m backend.app.core.init_db
   ```

### Running the Application

**Terminal 1 - FastAPI Server:**
```bash
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Celery Worker:**
```bash
celery -A backend.app.tasks worker --loglevel=info --pool=solo
```

**Terminal 3 - Frontend (Optional - Simple HTTP Server):**
```bash
cd frontend
python -m http.server 3000
```

**Access:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- Celery Flower (if installed): http://localhost:5555

## Usage

1. **Login** with your credentials
2. **Select an agent type** (SoW Reviewer, Project Plan Reviewer, or Architecture Compliance)
3. **Upload artifact** (Word document) to audit
4. **Upload checklist** for validation criteria
5. **Submit audit request** - it will be queued
6. **Monitor progress** on the dashboard
7. **View results** when audit completes (inline annotations + detailed report)

## Development

### Running Tests
```bash
pytest
```

### Code Formatting
```bash
black backend/
flake8 backend/
```

## Future Phases

- **Phase 2**: Additional agents, severity classification, bulk submission, admin controls
- **Phase 3**: External system integrations, checklist library, advanced analytics
- **Phase 4**: Cloud deployment, RDBMS migration, scalability enhancements

## License

[To be determined]

## Contributors

[To be added]

## Support

For issues or questions, please contact [support email/channel to be added]
