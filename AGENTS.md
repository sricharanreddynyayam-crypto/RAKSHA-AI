# AI Agent Guide for RakshaAI

## Purpose
This file gives AI coding agents the immediate context needed to work productively in this repository.

## Repository structure
- `backend/app/main.py`: FastAPI backend entrypoint and API route definitions.
- `backend/app/services/risk_engine.py`: Core risk scoring logic and data model definitions.
- `backend/tests/test_risk_engine.py`: unit tests for the risk engine.
- `backend/requirements.txt`: Python dependencies.

## Live server / backend behavior
- The backend is a FastAPI app exposing:
  - `GET /` for a basic running message
  - `GET /health` for health checks
  - `POST /risk/check` for risk scoring
  - `GET /simulate` for a random safety scenario
  - `GET /demo/timeline` for a demo timeline payload
- The risk scoring flow is built around `RiskRequest` → `RiskInput` → `compute_risk_score()`.
- The scoring rules include low battery, SOS triggers, no movement, and sudden stop.
- Response shape includes `risk_score`, `risk_band`, `factors`, `explanation`, and `alert`.

## Important notes for agents
- The working backend root is `backend/`; do not assume the repository root is the package root.
- The test file currently imports symbols that do not exist in `backend/app/services/risk_engine.py`.
  - `RiskFactors` and `calculate_risk_score` are likely stale names.
  - Prioritize aligning tests with the current `RiskResult` and `compute_risk_score` implementation.
- Use the current FastAPI code as the source of truth for API contract and risk logic.

## How to run
From the repository root:
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## How to test
From the repository root:
```bash
cd backend
pytest -v tests/test_risk_engine.py
```

## When making changes
- Keep API route behavior consistent with the existing endpoints.
- If you update the risk model, update the `/simulate` and `/demo/timeline` responses if needed.
- Prefer small, explicit changes due to the repository's simple service layout.
