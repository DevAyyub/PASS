# PASS — Proactive Academic Support System (MVP)

This repo is a **from-scratch starter kit** (React + Flask + Postgres) for your Information Systems project.

## 1) Start the database
```bash
docker compose up -d db
```

## 2) Run the backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python scripts/seed_demo.py
python run.py
```

Backend health: http://localhost:5000/api/health

## 3) Run the frontend
```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Frontend: http://localhost:5173

## Demo accounts
- Advisor: advisor@pass.local / advisor123
- Student: student1@pass.local / student123

## What works in this MVP
- Role-based login (student/advisor)
- Advisor: risk-ranked list, student detail, simple XAI panel, intervention logger, trigger risk scoring
- Student: progress dashboard (no risk shown), diagnostic study plan from blueprint+responses+resources
