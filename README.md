# GulfScopeIQ

A GCC-focused public-source intelligence platform that collects, normalizes, correlates, and visualizes company, tender, job, document, and infrastructure intelligence from selected official/public sources.

## What GulfScopeIQ Does

The platform executes a consistent intelligence pipeline:

Collect -> Normalize -> Verify -> Correlate -> Visualize -> Understand

It offers the following distinct capabilities:
- **Company Intelligence**
- **Tender Intelligence**
- **Jobs Intelligence**
- **Document Intelligence**
- **Infrastructure Intelligence**
- **Unified Intelligence Profile**
- **Intelligence Graph**

## Architecture

- **Frontend:** React + Vite + Tailwind
- **Backend:** FastAPI + Python + Pydantic + httpx
- **Deployment:** Vercel multi-service deployment
- **Data Model:** Extensible ontology using `Evidence`, `IntelligenceEntity`, `IntelligenceRelationship`, and `IntelligenceReport`

No database required for the MVP. All operations are strictly stateless.

## Supported Coverage

Coverage reflects currently configured public sources and does not imply complete national coverage.

- **Companies:** Limited generic public-web/company intelligence
- **Infrastructure:** Live where a verified public company domain is available
- **Tenders:**
  - Qatar: configured
  - Kuwait: configured
  - Bahrain: configured
  - Saudi Arabia: foundation/not configured
  - Oman: foundation/not configured
  - United Arab Emirates: unavailable
- **Jobs:**
  - Saudi Arabia: Saudi Aramco, STC, SABIC
  - Oman: OQ
- **Documents:**
  - Saudi Arabia: SABIC
  - United Arab Emirates: Emirates NBD

## Reliability / Failure Isolation

- **Independent module execution**
- **Configured source failures do not crash whole investigation**
- **Status semantics:** strict usage of `collected`, `partial`, `error`, and `foundation`
- **Bounded requests/results:** limits in place to ensure stable responses
- **No active scanning:** entirely passive OSINT integration
- **No CAPTCHA/WAF bypass:** strictly compliant retrieval
- **Normal TLS verification:** standard secure requests

## Example Workflow

Search SABIC / Saudi Arabia -> company profile -> news -> jobs -> documents -> infrastructure -> correlation -> unified graph

## API Endpoints

- `GET /api/health`
- `GET /api/registry/gcc`
- `POST /api/company/investigate`
- `POST /api/tenders/search`
- `POST /api/jobs/search`
- `POST /api/documents/search`
- `POST /api/correlation/analyze`
- `POST /api/intelligence/profile`
- `POST /api/infrastructure/investigate`

## Local Development

### Backend Setup
```bash
cd backend
python -m venv venv
# Activate virtual environment
pip install -r requirements.txt
export PYTHONPATH=$PWD
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

## Testing

The backend ensures robustness via a comprehensive test suite (155 tests).
```bash
pytest backend/tests/
```

## Limitations / MVP Scope

- Selected public sources only
- No database/persistence
- No authentication
- No scheduled monitoring/alerts
- No browser automation
- No protected-source scraping
- Source availability can change
- Company intelligence is limited/generic rather than authoritative corporate-registry data
