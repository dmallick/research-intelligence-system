from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from core.database import Base

class ContentTemplate(Base):
    __tablename__ = "content_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    template_type = Column(String)  # report, summary, presentation, social_post
    template_content = Column(Text)
    variables = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<ContentTemplate(name='{self.name}', type='{self.template_type}')>"

class GeneratedContent(Base):
    __tablename__ = "generated_content"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String, ForeignKey("research_tasks.task_id"))
    content_type = Column(String)  # report, summary, presentation, social_post
    title = Column(String)
    content = Column(Text)
    template_id = Column(Integer, ForeignKey("content_templates.id"), nullable=True)
    content_metadata = Column(JSON, default=dict)  # Changed from 'metadata' to 'content_metadata'
    quality_score = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    template = relationship("ContentTemplate")
    
    def __repr__(self):
        return f"<GeneratedContent(title='{self.title}', type='{self.content_type}')>"