from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class ResearchTask(Base):
    __tablename__ = "research_tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String, unique=True, index=True)
    query = Column(Text, nullable=False)
    status = Column(String, default="pending")  # pending, processing, completed, failed
    priority = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    metadata = Column(JSON, default=dict)
    
    # Relationships
    sources = relationship("ResearchSource", back_populates="task")
    results = relationship("ResearchResult", back_populates="task")

class ResearchSource(Base):
    __tablename__ = "research_sources"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String, ForeignKey("research_tasks.task_id"))
    url = Column(String, nullable=False)
    source_type = Column(String)  # web, academic, news, document
    title = Column(String)
    credibility_score = Column(Integer, default=0)
    retrieved_at = Column(DateTime, default=datetime.utcnow)
    content_hash = Column(String)
    
    # Relationships
    task = relationship("ResearchTask", back_populates="sources")

class ResearchResult(Base):
    __tablename__ = "research_results"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String, ForeignKey("research_tasks.task_id"))
    agent_type = Column(String)  # research, fact_check, content_gen, qa
    result_type = Column(String)  # summary, report, fact_check, content
    content = Column(Text)
    confidence_score = Column(Integer)
    metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    task = relationship("ResearchTask", back_populates="results")

class AgentState(Base):
    __tablename__ = "agent_states"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(String, unique=True, index=True)
    agent_type = Column(String)
    status = Column(String)  # idle, busy, error
    current_task = Column(String, nullable=True)
    last_heartbeat = Column(DateTime, default=datetime.utcnow)
    metadata = Column(JSON, default=dict)