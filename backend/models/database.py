from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./bugsniper.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    github_id = Column(Integer, unique=True, index=True)
    login = Column(String, unique=True, index=True)
    name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    access_token = Column(Text, nullable=True)  # Encrypted
    token_scope = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    repositories = relationship("Repository", back_populates="owner")
    jobs = relationship("Job", back_populates="user")

class Repository(Base):
    __tablename__ = "repositories"
    
    id = Column(Integer, primary_key=True, index=True)
    github_id = Column(Integer, unique=True, index=True)
    name = Column(String, index=True)
    full_name = Column(String, unique=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"))
    default_branch = Column(String, default="main")
    clone_url = Column(String)
    webhook_url = Column(String, nullable=True)
    webhook_secret = Column(String, nullable=True)
    webhook_id = Column(Integer, nullable=True)  # GitHub webhook ID
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    owner = relationship("User", back_populates="repositories")
    jobs = relationship("Job", back_populates="repository")

class Job(Base):
    __tablename__ = "jobs"
    
    id = Column(String, primary_key=True, index=True)
    repository_id = Column(Integer, ForeignKey("repositories.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    commit_sha = Column(String, index=True)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Commit details
    commit_message = Column(Text, nullable=True)
    commit_author = Column(String, nullable=True)
    commit_author_email = Column(String, nullable=True)
    commit_timestamp = Column(DateTime, nullable=True)
    commit_url = Column(String, nullable=True)
    
    # TestSprite results
    testsprite_passed = Column(Boolean, nullable=True)
    testsprite_total_tests = Column(Integer, nullable=True)
    testsprite_failed_tests = Column(Integer, nullable=True)
    testsprite_diagnostics = Column(Text, nullable=True)  # JSON
    testsprite_error_details = Column(Text, nullable=True)
    testsprite_execution_time = Column(Float, nullable=True)
    
    # Gemini analysis
    gemini_issue_summary = Column(Text, nullable=True)
    gemini_bugs_detected = Column(Text, nullable=True)  # JSON
    gemini_optimizations = Column(Text, nullable=True)  # JSON
    gemini_patch = Column(Text, nullable=True)
    gemini_deployable_status = Column(String, nullable=True)
    gemini_confidence_score = Column(Float, nullable=True)
    
    # GitHub operations
    branch_name = Column(String, nullable=True)
    pr_url = Column(String, nullable=True)
    pr_number = Column(Integer, nullable=True)
    
    repository = relationship("Repository", back_populates="jobs")
    user = relationship("User", back_populates="jobs")

def create_tables():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()