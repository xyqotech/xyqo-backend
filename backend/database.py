"""
AUTOPILOT - Configuration base de données
SQLAlchemy avec PostgreSQL et sessions
"""

from sqlalchemy import create_engine, Column, Integer, String, Boolean, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
import os

from config import settings

# Configuration SQLAlchemy
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=settings.DEBUG
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class DemoSessionDB(Base):
    """Table des sessions de démonstration"""
    __tablename__ = "demo_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(16), unique=True, index=True, nullable=False)
    file_name = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False)
    file_hash = Column(String(64), index=True)
    extraction_success = Column(Boolean, default=False)
    jira_ticket_created = Column(Boolean, default=False)
    jira_ticket_key = Column(String(50))
    quality_score = Column(Float)
    latency_ms = Column(Integer)
    error_message = Column(Text)
    ip_address = Column(String(45))  # IPv6 compatible
    user_agent = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


def create_tables():
    """Créer les tables si elles n'existent pas"""
    Base.metadata.create_all(bind=engine)


def get_db_session() -> Session:
    """Dependency pour obtenir session DB"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Initialiser les tables au démarrage
if __name__ == "__main__":
    create_tables()
    print("Tables créées avec succès")
