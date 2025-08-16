from sqlalchemy import Column, Integer, String, DateTime, JSON
from datetime import datetime
from core.database import Base

class AgentState(Base):
    __tablename__ = "agent_states"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(String, unique=True, index=True)
    agent_type = Column(String)
    status = Column(String)  # idle, busy, error
    current_task = Column(String, nullable=True)
    last_heartbeat = Column(DateTime, default=datetime.utcnow)
    agent_metadata = Column(JSON, default=dict)  # Changed from 'metadata' to 'agent_metadata'
    
    def __repr__(self):
        return f"<AgentState(agent_id='{self.agent_id}', status='{self.status}')>"