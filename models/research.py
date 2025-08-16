from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from core.database import Base

class ResearchTask(Base):
    __tablename__ = "research_tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String, unique=True, index=True)
    query = Column(Text, nullable=False)
    status = Column(String, default="pending")  # pending, processing, completed, failed
    priority = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    task_metadata = Column(JSON, default=dict)  # Changed from 'metadata' to 'task_metadata'
    
    # Relationships
    sources = relationship("ResearchSource", back_populates="task")
    results = relationship("ResearchResult", back_populates="task")
    
    def __repr__(self):
        return f"<ResearchTask(task_id='{self.task_id}', status='{self.status}')>"

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
    content = Column(Text)  # Store the actual content
    
    # Relationships
    task = relationship("ResearchTask", back_populates="sources")
    
    def __repr__(self):
        return f"<ResearchSource(url='{self.url}', type='{self.source_type}')>"

class ResearchResult(Base):
    __tablename__ = "research_results"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String, ForeignKey("research_tasks.task_id"))
    agent_type = Column(String)  # research, fact_check, content_gen, qa
    result_type = Column(String)  # summary, report, fact_check, content
    content = Column(Text)
    confidence_score = Column(Integer)
    result_metadata = Column(JSON, default=dict)  # Changed from 'metadata' to 'result_metadata'
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    task = relationship("ResearchTask", back_populates="results")
    
    def __repr__(self):
        return f"<ResearchResult(agent_type='{self.agent_type}', result_type='{self.result_type}')>"