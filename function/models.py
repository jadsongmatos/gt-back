# function/models.py
from sqlalchemy import (
    Column, Integer, String, Enum, JSON, DateTime, func
)
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class FileProcess(Base):
    __tablename__ = 'file_process'
    id = Column(Integer, primary_key=True)
    file_path = Column(String, nullable=False)
    status = Column(
        Enum('PENDING','PROCESSING','SUCCESS','FAILURE', name='status_enum'),
        nullable=False, default='PENDING'
    )
    current_step = Column(Integer, nullable=False, default=0)
    result = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False,
                        server_default=func.now(), onupdate=func.now())
