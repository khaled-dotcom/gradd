# EmpowerWork — Job Assistance Platform

Inclusive job platform for people with disabilities: smart search, CV applications, AI chat, and Egypt software-job imports.

## Live (Azure)

| Service | URL |
|---------|-----|
| Frontend | https://ewsw55166st.z1.web.core.windows.net/ |
| API | https://ewsw55166api.azurewebsites.net |
| API health | https://ewsw55166api.azurewebsites.net/health |

## Project layout

```
MT-NEW-main/
├── backend/              # FastAPI API
├── frontend/             # React (Vite)
├── data-engineering/     # Scrape Wuzzuf · Forasna · LinkedIn → MySQL
│   ├── connectors/
│   ├── pipeline/         # extract → transform → load
│   └── dags/             # Airflow (every 8h)
├── scripts/              # Azure deploy & start
├── docs/                 # Documentation
├── api/ + app.py         # Azure App Service entry
└── requirements.txt
```

## Quick start (local)

```powershell
pip install -r requirements.txt
cd frontend && npm ci && npm run dev

# Backend (repo root)
python -m uvicorn app:app --reload --port 8000
```

Copy `.env.azure.example` → `.env` and set `DB_*`, `GROQ_API_KEY`.

## Azure

```powershell
.\scripts\azure-start.ps1
.\scripts\azure-deploy-frontend-storage.ps1
powershell -File scripts/build-azure-zip.ps1
az webapp deploy -g rg-empowerwork -n ewsw55166api --src-path deploy.zip --type zip
```

See [docs/azure/DEPLOYMENT.md](docs/azure/DEPLOYMENT.md).

## Jobs pipeline (software / Egypt)

```powershell
python data-engineering/pipeline/run.py
```

- Schedule: every **8 hours** via Airflow — `.\scripts\azure-airflow-start.ps1` then unpause DAG `empowerwork_software_jobs_pipeline`
- Admin manual import: **Admin → Jobs → Run import now** (admin login only)

Details: [data-engineering/docs/PIPELINE.md](data-engineering/docs/PIPELINE.md)

## Admin

- Login: `admin@test.com` (set via `python backend/scripts/create_admin_user.py`)
- Dashboard: `/admin`

## Docs

- [docs/RUN_COMMANDS.md](docs/RUN_COMMANDS.md) — commands
- [data-engineering/docs/DATA_MODEL.md](data-engineering/docs/DATA_MODEL.md) — warehouse schema
- [docs/features/ACCESSIBILITY_FEATURES.md](docs/features/ACCESSIBILITY_FEATURES.md) — accessibility

## Team

Rawan Mohamed Farouk · Khaled Ghalwash · Mohamed Gamal · Mohamed Hassen · Mazen Hossam · Nadeen Ehab
# GraduationProject
