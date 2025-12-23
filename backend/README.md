# PASS Backend (Flask + Postgres)

## Quick start (MVP demo)
1) Start Postgres (from project root):
   ```bash
   docker compose up -d db
   ```

2) Create Python venv + install deps:
   ```bash
   cd backend
   python -m venv .venv
   # Windows: .venv\Scripts\activate
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3) Configure env:
   - Copy `.env.example` to `.env` and keep defaults.

4) Seed demo data:
   ```bash
   python scripts/seed_demo.py
   ```

5) Run server:
   ```bash
   python run.py
   ```

Backend runs at: http://localhost:5000/api/health

## Optional: Train LightGBM model
Put your dataset at `backend/data/dropout.csv` with a `target` column (0/1), then:
```bash
python scripts/train_lightgbm.py
```

Then (from Advisor UI) trigger risk scoring:
```http
POST /api/advisor/predict-risk
```
