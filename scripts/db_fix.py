#!/usr/bin/env python3
"""
Simple fix for duplicate agent ID issue
This script provides easy solutions without complex database operations
"""

import asyncio
import sys
import os
import time

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def option1_restart_containers():
    """Option 1: Restart Docker containers to clear database"""
    print("🔄 Option 1: Restart Docker Containers")
    print("=" * 50)
    print("This will:")
    print("• Stop all containers")
    print("• Clear all database data") 
    print("• Restart containers fresh")
    print()
    
    confirm = input("⚠️  This will DELETE ALL DATA. Continue? (yes/no): ").lower().strip()
    
    if confirm == "yes":
        print("🛑 Stopping containers...")
        os.system("docker-compose down -v")
        
        print("🚀 Starting containers...")
        os.system("docker-compose up -d")
        
        print("⏱️ Waiting for services to start...")
        time.sleep(10)
        
        print("✅ Containers restarted. Database is now clean!")
        return True
    else:
        print("❌ Operation cancelled")
        return False

async def option2_test_with_unique_id():
    """Option 2: Test with completely unique agent ID"""
    print("🆔 Option 2: Test with Unique ID")
    print("=" * 50)
    
    # Import here to avoid dependency issues
    try:
        from agents.research.research_agent import ResearchAgent
        
        # Create truly unique ID
        unique_id = f"research_test_{int(time.time() * 1000)}"
        print(f"Creating agent with unique ID: {unique_id}")
        
        agent = ResearchAgent(unique_id)
        await agent.initialize()
        
        print("✅ Agent created successfully!")
        print("🧪 Running quick test...")
        
        # Quick test
        task = {
            "task_id": "quick_test",
            "task_type": "academic_search",
            "query": "test query",
            "max_results": 1
        }
        
        result = await agent.process_task(task)
        print(f"✅ Test result: {result['status']}")
        
        # Cleanup
        if hasattr(agent, 'close_browser'):
            await agent.close_browser()
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

async def option3_check_docker_status():
    """Option 3: Check if Docker services are running"""
    print("🐳 Option 3: Check Docker Status")
    print("=" * 50)
    
    print("Checking Docker containers...")
    os.system("docker-compose ps")
    
    print("\nChecking Docker logs...")
    print("PostgreSQL logs:")
    os.system("docker-compose logs postgres | tail -10")
    
    print("\nRedis logs:")
    os.system("docker-compose logs redis | tail -10")
    
    print("\nIf services aren't running, try: docker-compose up -d")

async def option4_manual_sql_fix():
    """Option 4: Manual SQL fix commands"""
    print("🛠️ Option 4: Manual SQL Fix")
    print("=" * 50)
    print("You can manually connect to the database and run these commands:")
    print()
    print("1. Connect to PostgreSQL:")
    print("   docker exec -it <postgres_container_name> psql -U postgres -d research_intelligence")
    print()
    print("2. Delete test agents:")
    print("   DELETE FROM agent_states WHERE agent_id LIKE 'research_test_%';")
    print()
    print("3. Or delete all agents:")
    print("   DELETE FROM agent_states;")
    print()
    print("4. Check remaining agents:")
    print("   SELECT * FROM agent_states;")
    print()
    print("To find container name, run: docker-compose ps")

async def main():
    """Main menu"""
    print("🔧 Quick Fix for Agent ID Conflict")
    print("=" * 50)
    print()
    print("Choose a fix option:")
    print("1. Restart Docker containers (clears all data)")
    print("2. Test with completely unique ID")
    print("3. Check Docker service status")
    print("4. Show manual SQL fix commands")
    print("5. Exit")
    print()
    
    try:
        choice = input("Select option (1-5): ").strip()
        
        if choice == "1":
            success = await option1_restart_containers()
            if success:
                print("\n🧪 Now you can run the test:")
                print("python scripts/test_research_agent.py")
        
        elif choice == "2":
            await option2_test_with_unique_id()
        
        elif choice == "3":
            await option3_check_docker_status()
        
        elif choice == "4":
            await option4_manual_sql_fix()
        
        elif choice == "5":
            print("👋 Goodbye!")
        
        else:
            print("❌ Invalid option")
    
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    print("🚀 Starting Simple Fix Script...")
    asyncio.run(main())