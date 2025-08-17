#!/usr/bin/env python3
"""
Database cleanup script for development/testing
This script helps clean up test data and resolve agent ID conflicts
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_db
from core.models import AgentState, ResearchTask
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from core.config import settings
from sqlalchemy.ext.asyncio import create_async_engine
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create engine for direct database operations
engine = create_async_engine(settings.DATABASE_URL, echo=False)

async def clean_test_agents():
    """Remove test agents from database"""
    print("🧹 Cleaning test agents...")
    
    try:
        async with AsyncSession(engine) as session:
            # Delete agents with test IDs
            result = await session.execute(
                delete(AgentState).where(
                    AgentState.agent_id.like('research_test_%')
                )
            )
            
            deleted_count = result.rowcount
            await session.commit()
            
            print(f"✅ Deleted {deleted_count} test agents")
            return True
            
    except Exception as e:
        print(f"❌ Failed to clean test agents: {e}")
        return False

async def clean_old_agents(older_than_hours: int = 24):
    """Remove agents older than specified hours"""
    print(f"🧹 Cleaning agents older than {older_than_hours} hours...")
    
    try:
        async with AsyncSession(engine) as session:
            cutoff_time = datetime.utcnow() - timedelta(hours=older_than_hours)
            
            result = await session.execute(
                delete(AgentState).where(
                    AgentState.last_heartbeat < cutoff_time
                )
            )
            
            deleted_count = result.rowcount
            await session.commit()
            
            print(f"✅ Deleted {deleted_count} old agents")
            return True
            
    except Exception as e:
        print(f"❌ Failed to clean old agents: {e}")
        return False

async def clean_test_tasks():
    """Remove test research tasks"""
    print("🧹 Cleaning test research tasks...")
    
    try:
        async with AsyncSession(engine) as session:
            # Delete tasks with test IDs
            result = await session.execute(
                delete(ResearchTask).where(
                    ResearchTask.title.like('%test%')
                )
            )
            
            deleted_count = result.rowcount
            await session.commit()
            
            print(f"✅ Deleted {deleted_count} test tasks")
            return True
            
    except Exception as e:
        print(f"❌ Failed to clean test tasks: {e}")
        return False

async def list_current_agents():
    """List all current agents in database"""
    print("📋 Current agents in database:")
    
    try:
        async with AsyncSession(engine) as session:
            result = await session.execute(
                select(AgentState.agent_id, AgentState.agent_type, AgentState.status, AgentState.last_heartbeat)
            )
            
            agents = result.all()
            
            if not agents:
                print("   No agents found")
                return
            
            for agent in agents:
                last_seen = agent.last_heartbeat.strftime("%Y-%m-%d %H:%M:%S") if agent.last_heartbeat else "Never"
                print(f"   • {agent.agent_id} ({agent.agent_type}) - {agent.status} - Last seen: {last_seen}")
            
            print(f"   Total: {len(agents)} agents")
            
    except Exception as e:
        print(f"❌ Failed to list agents: {e}")

async def reset_agent_status(agent_id: str = None):
    """Reset agent status to idle"""
    if agent_id:
        print(f"🔄 Resetting status for agent: {agent_id}")
    else:
        print("🔄 Resetting status for all agents...")
    
    try:
        async with AsyncSession(engine) as session:
            if agent_id:
                # Reset specific agent
                result = await session.execute(
                    select(AgentState).where(AgentState.agent_id == agent_id)
                )
                agent = result.scalar_one_or_none()
                
                if agent:
                    agent.status = "idle"
                    agent.current_task = None
                    agent.last_heartbeat = datetime.utcnow()
                    print(f"✅ Reset agent {agent_id}")
                else:
                    print(f"❌ Agent {agent_id} not found")
            else:
                # Reset all agents
                result = await session.execute(select(AgentState))
                agents = result.scalars().all()
                
                for agent in agents:
                    agent.status = "idle"
                    agent.current_task = None
                    agent.last_heartbeat = datetime.utcnow()
                
                print(f"✅ Reset {len(agents)} agents")
            
            await session.commit()
            return True
            
    except Exception as e:
        print(f"❌ Failed to reset agent status: {e}")
        return False

async def clean_duplicate_agents():
    """Remove duplicate agents (keep latest)"""
    print("🧹 Cleaning duplicate agents...")
    
    try:
        async with AsyncSession(engine) as session:
            # Find duplicates
            result = await session.execute("""
                SELECT agent_id, COUNT(*) as count
                FROM agent_states 
                GROUP BY agent_id 
                HAVING COUNT(*) > 1
            """)
            
            duplicates = result.all()
            
            if not duplicates:
                print("   No duplicate agents found")
                return True
            
            for dup in duplicates:
                agent_id = dup.agent_id
                print(f"   Removing duplicates for: {agent_id}")
                
                # Keep the latest entry, delete others
                subresult = await session.execute(
                    select(AgentState)
                    .where(AgentState.agent_id == agent_id)
                    .order_by(AgentState.last_heartbeat.desc())
                )
                
                agents = subresult.scalars().all()
                
                # Delete all but the first (latest)
                for agent in agents[1:]:
                    await session.delete(agent)
            
            await session.commit()
            print(f"✅ Cleaned {len(duplicates)} duplicate agent groups")
            return True
            
    except Exception as e:
        print(f"❌ Failed to clean duplicates: {e}")
        return False

async def main():
    """Main cleanup function"""
    print("🚀 Database Cleanup Script")
    print("=" * 50)
    
    # Show current state
    await list_current_agents()
    
    print("\nAvailable cleanup options:")
    print("1. Clean test agents (research_test_*)")
    print("2. Clean old agents (>24 hours)")
    print("3. Clean test tasks")
    print("4. Reset all agent statuses")
    print("5. Clean duplicate agents")
    print("6. Full cleanup (all of the above)")
    print("7. List agents and exit")
    
    try:
        choice = input("\nSelect option (1-7): ").strip()
        
        if choice == "1":
            await clean_test_agents()
        elif choice == "2":
            await clean_old_agents()
        elif choice == "3":
            await clean_test_tasks()
        elif choice == "4":
            await reset_agent_status()
        elif choice == "5":
            await clean_duplicate_agents()
        elif choice == "6":
            print("🚀 Performing full cleanup...")
            await clean_test_agents()
            await clean_old_agents()
            await clean_test_tasks()
            await clean_duplicate_agents()
            await reset_agent_status()
            print("✅ Full cleanup completed")
        elif choice == "7":
            print("👋 Listing agents only, no cleanup performed")
        else:
            print("❌ Invalid option selected")
            return
        
        # Show final state
        print("\n📋 Final state:")
        await list_current_agents()
        
    except KeyboardInterrupt:
        print("\n⚠️ Cleanup interrupted by user")
    except Exception as e:
        print(f"\n❌ Cleanup failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())