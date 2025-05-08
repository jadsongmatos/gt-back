# function/models.py
import enum
from sqlalchemy import (
    Column, Integer, String, Enum as SqlEnum, JSON, DateTime, func
)
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class StatusEnum(enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    ERROR = "ERROR"  # adicionado porque é usado no código

class FileProcess(Base):
    __tablename__ = 'file_process'

    id = Column(Integer, primary_key=True)
    file_path = Column(String, nullable=False)
    status = Column(
        SqlEnum(StatusEnum, name='status_enum'),
        nullable=False,
        default=StatusEnum.PENDING
    )
    current_step = Column(Integer, nullable=False, default=0)
    result = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
