# Pipeline — وظائف السوفتوير (3 مواقع / كل 8 ساعات)

## الهدف

جلب وظائف **برمجة وتطوير (Software/IT)** من مصر من:

| المصدر | الملف | ماذا يفعل |
|--------|------|-----------|
| **Wuzzuf** | `connectors/wuzzuf.py` | بحث بعدة كلمات (software, python, frontend…) |
| **Forasna** | `connectors/forasna.py` | قسم IT: `/jobs/egypt?category=it` |
| **LinkedIn** | `connectors/linkedin.py` | Guest API — مصر + كلمات سوفتوير |

التقديم للمستخدم **على موقع EmpowerWork فقط** (لا روابط تقديم خارجية).

---

## الجدولة — كل 8 ساعات

- `config/pipeline.yaml` → `schedule_cron: "0 */8 * * *"`
- Airflow DAG: `dags/empowerwork_jobs_pipeline.py` → `empowerwork_software_jobs_pipeline`
- التشغيل: 00:00، 08:00، 16:00 UTC

```powershell
.\scripts\azure-airflow-start.ps1
# أو: docker compose -f data-engineering/docker-compose.data.yml up -d
# ثم http://localhost:8085 — فعّل (unpause) DAG: empowerwork_software_jobs_pipeline
```

### Azure VM (تشغيل 24/7)

1. VM بـ Docker (Ubuntu أو Windows + Docker Desktop)
2. انسخ الريبو + `.env` (DB_* لـ Azure MySQL)
3. `.\scripts\azure-airflow-start.ps1`
4. فتح firewall MySQL لـ IP الـ VM
5. **تحديث يدوي:** Admin → Jobs → «Run import now» (محمي — أدمن فقط)

تشغيل يدوي:

```powershell
python data-engineering/pipeline/run.py
```

---

## المراحل (متقسمة بوضوح)

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────┐
│ 1. EXTRACT  │ ──► │ 2. TRANSFORM     │ ──► │ 3. LOAD     │
│ Bronze JSONL│     │ Silver → Gold    │     │ MySQL       │
└─────────────┘     └──────────────────┘     └─────────────┘
```

| Stage | Code | Input | Output |
|-------|------|-------|--------|
| **Extract** | `pipeline/stages/extract.py` | مواقع الوظائف | `bronze/source={name}/dt=.../*.jsonl` |
| **Transform** | `pipeline/stages/transform.py` + `scripts/medallion_pandas.py` | Bronze | `silver/`, `gold/` Parquet |
| **Load** | `pipeline/stages/load.py` | Gold | جداول `jobs`, `import_runs` |

### ماذا يحدث في Transform؟

1. تنظيف HTML وحقول موحدة (`spark_jobs/common.py` → `bronze_to_draft`)
2. فلتر **مصر** (`config/egypt_filters.yaml`)
3. فلتر **سوفتوير** (`config/software_filters.yaml`)
4. إزالة التكرار `(source, external_id)`
5. `is_accessible_focus` من كلمات الإدماج

---

## الإعدادات

| ملف | الغرض |
|-----|--------|
| `config/sources.yaml` | تفعيل المصادر، حد أقصى للوظائف، صفحات |
| `config/software_filters.yaml` | كلمات السوفتوير + استعلامات البحث |
| `config/egypt_filters.yaml` | مدن وبلد مصر |
| `config/pipeline.yaml` | الجدولة ومسار الـ lake |

---

## LinkedIn — تنبيه

يستخدم **Guest API** العام. قد يتوقف إذا غيّرت LinkedIn الموقع. راجع شروط LinkedIn قبل الاستخدام التجاري.

---

## هيكل المجلدات

```
data-engineering/
  connectors/          # سكراب كل موقع (الأهم)
  pipeline/
    run.py             # نقطة التشغيل
    stages/
      extract.py
      transform.py
      load.py
  spark_jobs/          # Transform (Spark اختياري)
  config/
  dags/                # Airflow كل 8 ساعات
  pipeline/            # run.py + stages (extract/transform/load)
  docs/
    PIPELINE.md        # هذا الملف
    DATA_MODEL.md
```
