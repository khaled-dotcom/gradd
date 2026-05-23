# EmpowerWork — Data Engineering

**Airflow** (كل **8 ساعات**) + **Spark/Pandas** + سكراب **Wuzzuf + Forasna + LinkedIn** — وظائف **Software/IT** في مصر.

## تشغيل سريع

```powershell
python data-engineering/pipeline/run.py
```

## التوثيق

- [docs/PIPELINE.md](docs/PIPELINE.md) — شرح المراحل والجدولة والمصادر
- [docs/DATA_MODEL.md](docs/DATA_MODEL.md) — نموذج البيانات

## Layout

| Path | Role |
|------|------|
| `connectors/` | **Scrape** — Wuzzuf, Forasna, LinkedIn |
| `pipeline/stages/` | extract → transform → load |
| `spark_jobs/` | Bronze → Silver → Gold |
| `config/` | sources, software_filters, egypt_filters |
| `dags/` | Airflow `0 */8 * * *` |

## Airflow

```powershell
docker compose -f data-engineering/docker-compose.data.yml up -d
```

UI: http://localhost:8085 — DAG: `empowerwork_software_jobs_pipeline`
