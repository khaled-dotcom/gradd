import os
from dotenv import load_dotenv

load_dotenv()


def _bool_env(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).lower() in ("1", "true", "yes")


class Settings:
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_USER: str = os.getenv("DB_USER", "root")
    DB_PASS: str = os.getenv("DB_PASS", "")
    DB_NAME: str = os.getenv("DB_NAME", "rag_jobs")
    DB_SSL: bool = _bool_env("DB_SSL", "false")

    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_EMBED_MODEL: str = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")

    CHROMA_COLLECTION: str = os.getenv("CHROMA_COLLECTION", "jobs_collection")
    CHROMA_DIR: str = os.getenv("CHROMA_DIR", ".chroma")

    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

    # Kafka / Redis event stack (thesis demo — off on Azure production)
    EVENTS_ENABLED: bool = _bool_env("EVENTS_ENABLED", "false")
    KAFKA_BOOTSTRAP_SERVERS: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    ANALYTICS_DATA_PATH: str = os.getenv("ANALYTICS_DATA_PATH", "./data/lake")
    SPARK_REPORT_PATH: str = os.getenv("SPARK_REPORT_PATH", "./data/reports/latest.json")
    SPARK_MASTER: str = os.getenv("SPARK_MASTER", "local[*]")
    USE_SPARK: bool = _bool_env("USE_SPARK", "true")

    # Azure
    AZURE_STORAGE_CONNECTION_STRING: str = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
    AZURE_STORAGE_CONTAINER: str = os.getenv("AZURE_STORAGE_CONTAINER", "empowerwork")
    AZURE_SPARK_REPORT_BLOB: str = os.getenv("AZURE_SPARK_REPORT_BLOB", "reports/latest.json")
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "*")
    IDS_ENABLED: bool = _bool_env("IDS_ENABLED", "true")


settings = Settings()
