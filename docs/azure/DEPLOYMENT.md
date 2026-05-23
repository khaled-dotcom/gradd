# نشر EmpowerWork على Azure (حساب طالب)

دليل نشر **المشروع الكامل**: React + FastAPI + MySQL + Blob.  
طبقة **Kafka/Spark** تبقى للعرض المحلي (الرسالة) — على Azure: `EVENTS_ENABLED=false`.

---

## 1) ماذا يُنشر؟

| جزء | خدمة Azure |
|-----|------------|
| Frontend (`frontend/`) | **Static Web Apps** (مجاني) |
| Backend (Docker) | **App Service** Linux B1 |
| MySQL | **Azure Database for MySQL** أو **Aiven** (مجاني) |
| CV / صور / تقرير Spark | **Storage Account** (Blob) |

**لا يُنشر:** `sign_language/` (نسخة مكررة)، Kafka/Redis/workers على Azure.

---

## 2) المتطلبات

- حساب [Azure for Students](https://azure.microsoft.com/free/students/) ($100 رصيد)
- [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli)
- Docker Desktop
- GitHub repo للمشروع
- مفاتيح: `GROQ_API_KEY`، `OPENAI_API_KEY` (لـ Chroma/RAG)

---

## 3) إنشاء الموارد (Portal أو CLI)

### 3.1 مجموعة موارد

```powershell
az login
az group create --name rg-empowerwork --location westeurope
```

### 3.2 MySQL (أو استخدم Aiven المجاني)

```powershell
az mysql flexible-server create `
  --resource-group rg-empowerwork `
  --name empowerwork-mysql `
  --location westeurope `
  --sku-name Standard_B1ms `
  --tier Burstable `
  --storage-size 32 `
  --version 8.0.21 `
  --admin-user ewadmin `
  --admin-password "YourStrong#Passw0rd" `
  --public-access 0.0.0.0
```

إنشاء قاعدة:

```powershell
az mysql flexible-server db create `
  --resource-group rg-empowerwork `
  --server-name empowerwork-mysql `
  --database-name rag_jobs
```

**مهم:** اسم المستخدم في `.env`:

```env
DB_USER=ewadmin@empowerwork-mysql
DB_HOST=empowerwork-mysql.mysql.database.azure.com
DB_SSL=true
```

### 3.3 Storage Account (Blob)

```powershell
az storage account create -g rg-empowerwork -n empowerworkstore --sku Standard_LRS
az storage container create --account-name empowerworkstore --name empowerwork --public-access blob
```

انسخ **Connection string** من Portal → Access keys.

### 3.4 App Service (Docker)

```powershell
az appservice plan create -g rg-empowerwork -n plan-empowerwork --is-linux --sku B1
az webapp create -g rg-empowerwork -p plan-empowerwork -n empowerwork-api --deployment-container-image-name-placeholder
az webapp config container set -g rg-empowerwork -n empowerwork-api `
  --docker-custom-image-name <your-acr>.azurecr.io/empowerwork-api:latest `
  --docker-registry-server-url https://<your-acr>.azurecr.io
```

**بدون ACR (أبسط للطالب):** من Portal → App Service → Deployment Center → Container Registry أو رفع Docker يدوياً بعد:

```powershell
cd C:\path\to\MT-NEW-main
docker build -t empowerwork-api .
# اربط ACR أو استخدم az acr build
```

### 3.5 Frontend (Storage static website — works in swedencentral)

Student subscriptions often cannot create Static Web Apps in `westeurope`. Use blob static hosting instead:

```powershell
.\scripts\azure-deploy-frontend-storage.ps1
```

URL: `https://<storageaccount>.z1.web.core.windows.net/`

**Alternative:** Static Web Apps in an allowed region (Portal → GitHub → `frontend` / `dist`).

---

## 4) متغيرات App Service

من [`.env.azure.example`](../../.env.azure.example) — Application settings:

| Setting | مثال |
|---------|------|
| `DB_HOST` | `xxx.mysql.database.azure.com` |
| `DB_USER` | `user@server` |
| `DB_PASS` | كلمة المرور |
| `DB_NAME` | `rag_jobs` |
| `DB_SSL` | `true` |
| `GROQ_API_KEY` | مفتاح Groq |
| `GROQ_MODEL` | `llama-3.1-8b-instant` |
| `OPENAI_API_KEY` | للـ embeddings |
| `EVENTS_ENABLED` | `false` |
| `AZURE_STORAGE_CONNECTION_STRING` | من Storage |
| `AZURE_STORAGE_CONTAINER` | `empowerwork` |
| `CORS_ORIGINS` | `https://<swa>.azurestaticapps.net` |
| `CHROMA_DIR` | `/home/site/wwwroot/.chroma` |
| `WEBSITES_ENABLE_APP_SERVICE_STORAGE` | `true` |
| `IDS_ENABLED` | `false` |

---

## 5) Frontend — متغيرات البناء

في Static Web Apps → Configuration → Application settings (أو `frontend/.env` عند البناء):

```env
VITE_API_URL=https://empowerwork-api.azurewebsites.net
VITE_EVENTS_ENABLED=false
```

---

## 6) تهيئة قاعدة البيانات

على جهازك، انسخ `.env.azure.example` → `.env` واملأ بيانات MySQL السحابية:

```powershell
.\scripts\azure-seed-db.ps1
```

ثم (اختياري) Chroma:

```powershell
python backend/scripts/reindex_chroma.py
```

---

## 7) Spark + Admin (هجين)

1. محلياً: `docker compose -f docker-compose.events.yml run --rm spark-analytics`
2. ارفع التقرير:

```powershell
# ضع AZURE_STORAGE_CONNECTION_STRING في .env
.\scripts\upload-spark-report.ps1
```

3. Admin Dashboard → بطاقة Spark تقرأ من Blob.

---

## 8) Kafka للرسالة (محلي)

```powershell
docker compose -f docker-compose.events.yml up -d
$env:EVENTS_ENABLED="true"
python scripts/run_workers.py
```

اعرض Kafka UI: http://localhost:8080 ولقطات مع رابط Azure الحي.

---

## 9) Checklist اختبار

- [ ] `https://<api>.azurewebsites.net/health`
- [ ] `https://<swa>.azurestaticapps.net` — تسجيل، وظائف، شات
- [ ] رفع صورة profile + CV
- [ ] Admin + Spark report (بعد الرفع)
- [ ] Sign Language iframe (Streamlit خارجي — يعمل إن الرابط حي)

---

## 10) GitHub Actions (اختياري)

- Backend: [`.github/workflows/azure-backend.yml`](../../.github/workflows/azure-backend.yml) — يحتاج `AZURE_CREDENTIALS` + ACR
- Frontend: [`.github/workflows/azure-frontend.yml`](../../.github/workflows/azure-frontend.yml) — `AZURE_STATIC_WEB_APPS_API_TOKEN`

---

## 11) توفير الرصيد

- استخدم **Aiven MySQL مجاني** بدل Azure MySQL (~$12/شهر)
- أوقف App Service عند عدم العرض: `az webapp stop`
- Static Web Apps يبقى مجاني
