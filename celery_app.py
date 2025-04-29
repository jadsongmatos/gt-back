import os
import logging
from celery import Celery
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from contextlib import contextmanager

# 1. Configuração de URLs de broker e backend Celery (via SQLite)
broker_url = os.getenv("CELERY_BROKER_URL", "sqla+sqlite:///celery_broker.sqlite3")
result_url = os.getenv("CELERY_RESULT_URL", "db+sqlite:///celery_results.sqlite3")

# 2. Inicializar Celery
celery = Celery(
    "openfaas_tasks",
    broker=broker_url,
    backend=result_url,
    include=["function.tasks"],
)

celery.conf.update(
     task_serializer="msgpack",
     result_serializer="msgpack",
     accept_content=["msgpack"],
     task_acks_late=True,
     worker_prefetch_multiplier=1,
    broker_transport_options={
        "max_retries": 3,
        #"visibility_timeout": 3600,  # 1 hora
    },
)

# SQLAlchemy Engine para SQLite com otimizações:
engine = create_engine(
    "sqlite:///celery_results.sqlite3",
    # timeout em segundos para aguardar locks antes de falhar
    connect_args={
        "check_same_thread": False,
        "timeout": 30
    },
    poolclass=NullPool,
    isolation_level="SERIALIZABLE",
    execution_options={"compiled_cache": {}},
    future=True,
)

# Configurar SQLite para durabilidade e desempenho
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA synchronous=EXTRA;")
    cursor.execute("PRAGMA foreign_keys=ON;")
    cursor.execute("PRAGMA busy_timeout=30000;")
    #cursor.execute("PRAGMA temp_store=MEMORY;")
    cursor.close()

# Session Factory
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)

# Context Manager para sessões seguras
@contextmanager
def get_session():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        
from function.models import Base
Base.metadata.create_all(engine)