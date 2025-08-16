#!/usr/bin/env python3
"""
Test script for Research Agent
Run this to test the research agent functionality
"""

import asyncio
import sys
import os
import json

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.research.research_agent import ResearchAgent
from core.message_queue import get_message_queue
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)

async def test_research_agent_initialization():
    """Test research agent initialization"""
    print("=== Testing Research Agent Initialization ===")
    
    try:
        agent = ResearchAgent("research_test_001")
        await agent.initialize()
        await agent.initialize_browser()
        print("✅ Research agent initialized successfully")
        
        # Test health check
        await agent.send_message(
            "research_test_001",  # Send to self for testing
            "ping",
            {"test": "health_check"}
        )
        
        await asyncio.sleep(1)
        
        return agent
        
    except Exception as e:
        print(f"❌ Research agent initialization failed: {e}")
        return None

async def test_web_research_task(agent: ResearchAgent):
    """Test web research functionality"""
    print("\n=== Testing Web Research Task ===")
    
    try:
        task = {
            "task_id": "web_research_001",
            "task_type": "web_research",
            "query": {
                "query": "artificial intelligence recent developments",
                "search_type": "web",
                "max_results": 3
            }
        }
        
        print(f"Processing web research task: {task['query']['query']}")
        result = await agent.process_task(task)
        
        if result["status"] == "completed":
            print(f"✅ Web research completed")
            print(f"   Results found: {result['results_found']}")
            for i, res in enumerate(result['results'][:2]):  # Show first 2
                print(f"   Result {i+1}: {res['title'][:60]}...")
        else:
            print(f"❌ Web research failed: {result.get('error', 'Unknown error')}")
        
        return result["status"] == "completed"
        
    except Exception as e:
        print(f"❌ Web research test failed: {e}")
        return False

async def test_academic_search(agent: ResearchAgent):
    """Test academic paper search"""
    print("\n=== Testing Academic Search ===")
    
    try:
        task = {
            "task_id": "academic_001",
            "task_type": "academic_search",
            "query": "machine learning transformers",
            "max_results": 5
        }
        
        print(f"Searching for academic papers: {task['query']}")
        result = await agent.process_task(task)
        
        if result["status"] == "completed":
            print(f"✅ Academic search completed")
            print(f"   Papers found: {result['results_found']}")
            for i, paper in enumerate(result['results'][:2]):  # Show first 2
                print(f"   Paper {i+1}: {paper['title'][:60]}...")
                print(f"            Authors: {', '.join(paper['authors'][:3])}")
        else:
            print(f"❌ Academic search failed: {result.get('error', 'Unknown error')}")
        
        return result["status"] == "completed"
        
    except Exception as e:
        print(f"❌ Academic search test failed: {e}")
        return False

async def test_news_search(agent: ResearchAgent):
    """Test news search functionality"""
    print("\n=== Testing News Search ===")
    
    try:
        task = {
            "task_id": "news_001",
            "task_type": "news_search",
            "query": "technology news",
            "max_results": 10,
            "sources": [
                "https://rss.cnn.com/rss/edition.rss",
                "https://feeds.bbci.co.uk/news/technology/rss.xml"
            ]
        }
        
        print(f"Searching news for: {task['query']}")
        result = await agent.process_task(task)
        
        if result["status"] == "completed":
            print(f"✅ News search completed")
            print(f"   Articles found: {result['results_found']}")
            print(f"   Sources checked: {result['metadata']['sources_checked']}")
            for i, article in enumerate(result['results'][:2]):  # Show first 2
                print(f"   Article {i+1}: {article['title'][:60]}...")
        else:
            print(f"❌ News search failed: {result.get('error', 'Unknown error')}")
        
        return result["status"] == "completed"
        
    except Exception as e:
        print(f"❌ News search test failed: {e}")
        return False

async def test_url_analysis(agent: ResearchAgent):
    """Test URL analysis functionality"""
    print("\n=== Testing URL Analysis ===")
    
    try:
        # Test with a reliable URL
        task = {
            "task_id": "url_analysis_001",
            "task_type": "url_analysis",
            "url": "https://httpbin.org/html"  # Reliable test URL
        }
        
        print(f"Analyzing URL: {task['url']}")
        result = await agent.process_task(task)
        
        if result["status"] == "completed":
            print(f"✅ URL analysis completed")
            analysis = result["analysis"]
            print(f"   Title: {analysis['title']}")
            print(f"   Word count: {analysis['word_count']}")
            print(f"   Quality score: {analysis['quality_score']:.2f}")
        else:
            print(f"❌ URL analysis failed: {result.get('error', 'Unknown error')}")
        
        return result["status"] == "completed"
        
    except Exception as e:
        print(f"❌ URL analysis test failed: {e}")
        return False

async def test_message_communication(agent: ResearchAgent):
    """Test message-based research requests"""
    print("\n=== Testing Message Communication ===")
    
    try:
        # Simulate a research request via message
        from agents.base.agent import AgentMessage
        from datetime import datetime
        import uuid
        
        message = AgentMessage(
            id=str(uuid.uuid4()),
            sender_id="test_orchestrator",
            receiver_id=agent.agent_id,
            message_type="research_request",
            content={
                "task_id": "msg_research_001",
                "task_type": "academic_search",
                "query": "natural language processing",
                "max_results": 3
            },
            timestamp=datetime.utcnow(),
            correlation_id="test_correlation_msg"
        )
        
        # Send message and wait for response
        await agent._handle_message(message)
        
        # Wait for processing
        await asyncio.sleep(2)
        
        print("✅ Message communication test completed")
        return True
        
    except Exception as e:
        print(f"❌ Message communication test failed: {e}")
        return False

async def test_concurrent_requests(agent: ResearchAgent):
    """Test concurrent request handling"""
    print("\n=== Testing Concurrent Requests ===")
    
    try:
        tasks = [
            {
                "task_id": f"concurrent_{i}",
                "task_type": "academic_search",
                "query": f"test query {i}",
                "max_results": 2
            }
            for i in range(3)
        ]
        
        print("Processing 3 concurrent research tasks...")
        results = await asyncio.gather(
            *[agent.process_task(task) for task in tasks],
            return_exceptions=True
        )
        
        completed = sum(1 for r in results if isinstance(r, dict) and r.get("status") == "completed")
        print(f"✅ Completed {completed}/3 concurrent tasks")
        
        return completed >= 2  # At least 2 should succeed
        
    except Exception as e:
        print(f"❌ Concurrent requests test failed: {e}")
        return False

async def test_error_handling(agent: ResearchAgent):
    """Test error handling with invalid tasks"""
    print("\n=== Testing Error Handling ===")
    
    try:
        # Test invalid task type
        invalid_task = {
            "task_id": "invalid_001",
            "task_type": "invalid_task_type",
            "query": "test"
        }
        
        result = await agent.process_task(invalid_task)
        
        if result["status"] == "error" and "Unknown task type" in result["error"]:
            print("✅ Error handling for invalid task type works")
            return True
        else:
            print(f"❌ Expected error handling failed: {result}")
            return False
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False

async def cleanup_agent(agent: ResearchAgent):
    """Cleanup agent resources"""
    try:
        await agent.close_browser()
        print("✅ Agent resources cleaned up")
    except Exception as e:
        print(f"⚠️ Cleanup warning: {e}")

async def main():
    """Main test function"""
    print("🚀 Starting Research Agent Tests")
    print("Make sure you have installed the required packages:")
    print("pip install aiohttp beautifulsoup4 playwright arxiv feedparser PyPDF2 python-docx")
    print("playwright install chromium")
    print()
    
    # Initialize agent
    agent = await test_research_agent_initialization()
    if not agent:
        print("❌ Cannot proceed without working agent")
        return
    
    # Run tests
    test_results = {}
    
    try:
        # Core functionality tests
        test_results["web_research"] = await test_web_research_task(agent)
        test_results["academic_search"] = await test_academic_search(agent)
        test_results["news_search"] = await test_news_search(agent)
        test_results["url_analysis"] = await test_url_analysis(agent)
        
        # Advanced tests  
        test_results["message_communication"] = await test_message_communication(agent)
        test_results["concurrent_requests"] = await test_concurrent_requests(agent)
        test_results["error_handling"] = await test_error_handling(agent)
        
    finally:
        # Always cleanup
        await cleanup_agent(agent)
    
    # Test summary
    print("\n" + "="*60)
    print("🎯 RESEARCH AGENT TEST SUMMARY")
    print("="*60)
    
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        test_display = test_name.replace("_", " ").title()
        print(f"{test_display:<25}: {status}")
    
    total_tests = len(test_results)
    passed_tests = sum(test_results.values())
    
    print("-" * 60)
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    print(f"Success Rate: {passed_tests/total_tests*100:.1f}%")
    
    if passed_tests == total_tests:
        print("\n🎉 All tests passed! Research Agent is working perfectly.")
    elif passed_tests >= total_tests * 0.7:
        print("\n⚠️ Most tests passed. Research Agent is mostly functional.")
    else:
        print("\n❌ Many tests failed. Check the Research Agent implementation.")
    
    print("\n📝 Next Steps:")
    print("1. Install missing dependencies if tests failed")
    print("2. Test integration with vector store (ChromaDB)")
    print("3. Add the research agent to your API endpoints")
    print("4. Test end-to-end research workflow")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")