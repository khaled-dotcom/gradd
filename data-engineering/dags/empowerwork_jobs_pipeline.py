"""
Airflow DAG: Egypt SOFTWARE jobs — Wuzzuf + Forasna + LinkedIn.

Schedule: every 8 hours (0 */8 * * *)
Unpause in Airflow UI: http://localhost:8085
"""
from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator

REPO = Path("/opt/airflow/repo")
DE = REPO / "data-engineering"


default_args = {
    "owner": "empowerwork",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=10),
}


def _setup_path():
    if str(DE) not in sys.path:
        sys.path.insert(0, str(DE))
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))


def stage_extract(**_context):
    _setup_path()
    from pipeline.stages.extract import run_extract

    run_extract(REPO, DE)


def stage_transform(**_context):
    _setup_path()
    from pipeline.stages.transform import run_transform

    run_transform(REPO, DE, use_spark=True)


def stage_load(**_context):
    _setup_path()
    from pipeline.stages.load import run_load

    run_load(REPO)


with DAG(
    dag_id="empowerwork_software_jobs_pipeline",
    default_args=default_args,
    description="Scrape Wuzzuf/Forasna/LinkedIn (software) → Gold → MySQL",
    schedule_interval="0 */8 * * *",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["empowerwork", "jobs", "software"],
) as dag:
    t_extract = PythonOperator(
        task_id="1_extract_bronze",
        python_callable=stage_extract,
        doc_md="**Stage 1:** Live scrape 3 boards → `data/lake/jobs/bronze/`",
    )
    t_transform = PythonOperator(
        task_id="2_transform_silver_gold",
        python_callable=stage_transform,
        doc_md="**Stage 2:** Filter Egypt + software IT, dedupe → Gold Parquet",
    )
    t_load = PythonOperator(
        task_id="3_load_mysql",
        python_callable=stage_load,
        doc_md="**Stage 3:** Upsert into MySQL for EmpowerWork website",
    )

    t_extract >> t_transform >> t_load
