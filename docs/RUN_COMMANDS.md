# Run Commands

## Local development

```powershell
# From repo root
pip install -r requirements.txt
copy .env.azure.example .env
# Edit .env: DB_*, GROQ_API_KEY

# Terminal 1 — API
python -m uvicorn app:app --reload --port 8000

# Terminal 2 — Frontend
cd frontend
npm ci
npm run dev
```

Frontend: http://localhost:5173  
API docs: http://localhost:8000/docs

## Database (first time)

```powershell
python backend/scripts/migrations/migrate_jobs_data_warehouse.py
python backend/scripts/seeds/seed_disabilities.py
python backend/scripts/seeds/seed_assistive_tools.py
python backend/scripts/create_admin_user.py admin@test.com Admin123456! Admin
```

## Azure

```powershell
.\scripts\azure-start.ps1
powershell -File scripts/build-azure-zip.ps1
az webapp deploy -g rg-empowerwork -n ewsw55166api --src-path deploy.zip --type zip
powershell -File scripts/azure-deploy-frontend-storage.ps1
```

## Jobs pipeline

```powershell
python data-engineering/pipeline/run.py
```

Airflow (every 8 hours):

```powershell
.\scripts\azure-airflow-start.ps1
# http://localhost:8085 — unpause DAG: empowerwork_software_jobs_pipeline
```

Admin manual import: log in as admin → **Admin → Jobs → Run import now**
