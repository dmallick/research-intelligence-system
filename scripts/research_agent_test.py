#!/usr/bin/env python3
"""
Test script for Research Agent
Tests all research capabilities including web scraping, arXiv search, and document parsing
"""

import asyncio
import sys
import os
import tempfile
import json
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.base.agent import BaseAgent


from agents.research.research_agent import ResearchAgent, ResearchTaskTemplates
from core.message_queue import get_message_queue
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_research_agent_initialization():
    """Test research agent initialization"""
    print("=== Testing Research Agent Initialization ===")
    
    try:
        # Create research agent
        agent = ResearchAgent("test_research_agent")
        await agent.initialize()
        
        print("✅ Research agent initialized successfully")
        
        # Check status
        status = await agent.get_status()
        print(f"✅ Agent status retrieved: {status['capabilities']}")
        
        # Check statistics
        stats = status.get('statistics', {})
        print(f"✅ Agent statistics: {stats['total_requests']} total requests")
        
        return agent
        
    except Exception as e:
        print(f"❌ Research agent initialization failed: {e}")
        return None

async def test_web_scraping(agent: ResearchAgent):
    """Test web scraping functionality"""
    print("\n=== Testing Web Scraping ===")
    
    # Test URLs (using reliable, simple sites)
    test_urls = [
        "https://httpbin.org/html",  # Simple HTML for testing
        "https://jsonplaceholder.typicode.com/posts/1",  # JSON API
        "https://example.com",  # Basic HTML
    ]
    
    results = []
    
    for url in test_urls:
        try:
            print(f"📄 Scraping: {url}")
            
            # Create web scrape task
            task = ResearchTaskTemplates.web_scrape_task(url)
            task["task_id"] = f"scrape_{url.split('//')[-1].replace('/', '_')}"
            
            # Execute task
            result = await agent.execute_task(task)
            
            if result["status"] == "completed":
                content_length = len(result["result"].get("text_content", ""))
                print(f"✅ Scraped successfully - {content_length} characters")
                results.append(result)
            else:
                print(f"❌ Scraping failed: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"❌ Error scraping {url}: {e}")
    
    print(f"📊 Web scraping completed: {len(results)}/{len(test_urls)} successful")
    return results

async def test_arxiv_search(agent: ResearchAgent):
    """Test arXiv search functionality"""
    print("\n=== Testing arXiv Search ===")
    
    try:
        # Search for machine learning papers
        query = "machine learning"
        print(f"🔍 Searching arXiv for: {query}")
        
        task = ResearchTaskTemplates.arxiv_search_task(query, max_results=5)
        task["task_id"] = "arxiv_ml_search"
        
        result = await agent.execute_task(task)
        
        if result["status"] == "completed":
            papers = result["result"]
            print(f"✅ Found {len(papers)} papers")
            
            for i, paper in enumerate(papers[:3], 1):  # Show first 3
                print(f"  {i}. {paper.get('title', 'No title')[:100]}...")
                print(f"     Authors: {', '.join(paper.get('authors', [])[:3])}")
                print(f"     arXiv ID: {paper.get('arxiv_id', 'N/A')}")
                print()
            
            return result
        else:
            print(f"❌ arXiv search failed: {result.get('error', 'Unknown error')}")
            return None
            
    except Exception as e:
        print(f"❌ Error in arXiv search: {e}")
        return None

async def test_news_search(agent: ResearchAgent):
    """Test news search functionality (requires API key)"""
    print("\n=== Testing News Search ===")
    
    try:
        query = "artificial intelligence"
        print(f"📰 Searching news for: {query}")
        
        task = ResearchTaskTemplates.news_search_task(query, max_results=5)
        task["task_id"] = "news_ai_search"
        
        result = await agent.execute_task(task)
        
        if result["status"] == "completed":
            articles = result["result"]
            print(f"✅ Found {len(articles)} articles")
            
            for i, article in enumerate(articles[:3], 1):  # Show first 3
                print(f"  {i}. {article.get('title', 'No title')[:100]}...")
                print(f"     Source: {article.get('source', 'N/A')}")
                print(f"     Published: {article.get('published_at', 'N/A')}")
                print()
            
            return result
        else:
            error_msg = result.get('error', 'Unknown error')
            if "News API key not configured" in error_msg:
                print("⚠️  News API key not configured - skipping news search test")
                return {"status": "skipped", "reason": "No API key"}
            else:
                print(f"❌ News search failed: {error_msg}")
                return None
                
    except Exception as e:
        print(f"❌ Error in news search: {e}")
        return None

async def test_document_parsing(agent: ResearchAgent):
    """Test document parsing functionality"""
    print("\n=== Testing Document Parsing ===")
    
    results = []
    
    # Create temporary test files
    temp_dir = Path(tempfile.mkdtemp())
    
    try:
        # Test text file
        text_file = temp_dir / "test.txt"
        with open(text_file, 'w') as f:
            f.write("This is a test text file.\nIt has multiple lines.\nFor testing document parsing.")
        
        print(f"📄 Parsing text file: {text_file}")
        task = ResearchTaskTemplates.document_parse_task(str(text_file))
        task["task_id"] = "parse_text"
        
        result = await agent.execute_task(task)
        if result["status"] == "completed":
            content_length = len(result["result"]["content"])
            print(f"✅ Text file parsed successfully - {content_length} characters")
            results.append(result)
        else:
            print(f"❌ Text parsing failed: {result.get('error')}")
        
        # Test JSON file
        json_file = temp_dir / "test.json"
        test_data = {
            "title": "Test Document",
            "content": ["Item 1", "Item 2", "Item 3"],
            "metadata": {
                "created": "2024-01-01",
                "version": "1.0"
            }
        }
        
        with open(json_file, 'w') as f:
            json.dump(test_data, f, indent=2)
        
        print(f"📄 Parsing JSON file: {json_file}")
        task = ResearchTaskTemplates.document_parse_task(str(json_file))
        task["task_id"] = "parse_json"
        
        result = await agent.execute_task(task)
        if result["status"] == "completed":
            items_count = result["result"]["metadata"]["items_count"]
            print(f"✅ JSON file parsed successfully - {items_count} items")
            results.append(result)
        else:
            print(f"❌ JSON parsing failed: {result.get('error')}")
        
        # Test HTML file
        html_file = temp_dir / "test.html"
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Test HTML Document</title>
        </head>
        <body>
            <h1>Test Document</h1>
            <p>This is a test HTML document for parsing.</p>
            <ul>
                <li>Item 1</li>
                <li>Item 2</li>
                <li>Item 3</li>
            </ul>
        </body>
        </html>
        """
        
        with open(html_file, 'w') as f:
            f.write(html_content)
        
        print(f"📄 Parsing HTML file: {html_file}")
        task = ResearchTaskTemplates.document_parse_task(str(html_file))
        task["task_id"] = "parse_html"
        
        result = await agent.execute_task(task)
        if result["status"] == "completed":
            title = result["result"]["metadata"]["title"]
            print(f"✅ HTML file parsed successfully - Title: '{title}'")
            results.append(result)
        else:
            print(f"❌ HTML parsing failed: {result.get('error')}")
        
    except Exception as e:
        print(f"❌ Error in document parsing tests: {e}")
    
    finally:
        # Cleanup temporary files
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    print(f"📊 Document parsing completed: {len(results)} successful")
    return results

async def test_batch_url_extraction(agent: ResearchAgent):
    """Test batch URL extraction"""
    print("\n=== Testing Batch URL Extraction ===")
    
    try:
        urls = [
            "https://httpbin.org/html",
            "https://example.com",
            "https://httpbin.org/json"
        ]
        
        print(f"📦 Extracting content from {len(urls)} URLs...")
        
        task = ResearchTaskTemplates.batch_url_extract_task(urls)
        task["task_id"] = "batch_extract"
        
        result = await agent.execute_task(task)
        
        if result["status"] == "completed":
            results = result["result"]
            successful = len([r for r in results if r["status"] == "success"])
            print(f"✅ Batch extraction completed: {successful}/{len(urls)} successful")
            
            for i, url_result in enumerate(results, 1):
                status = "✅" if url_result["status"] == "success" else "❌"
                url = url_result["url"]
                print(f"  {i}. {status} {url}")
            
            return result
        else:
            print(f"❌ Batch extraction failed: {result.get('error')}")
            return None
            
    except Exception as e:
        print(f"❌ Error in batch URL extraction: {e}")
        return None

async def test_message_queue_integration(agent: ResearchAgent):
    """Test message queue integration"""
    print("\n=== Testing Message Queue Integration ===")
    
    try:
        # Test sending a research task via message queue
        print("📨 Testing message-based research task...")
        
        # Create a simple test agent to send messages
        from scripts.test_agent import TestAgent
        test_agent = TestAgent("test_requester")
        await test_agent.initialize()
        
        # Send a web scraping request
        await test_agent.send_message(
            agent.agent_id,
            "web_scrape",
            {
                "url": "https://httpbin.org/html",
                "options": {"use_playwright": False}
            },
            correlation_id="test_scrape_001"
        )
        
        print("✅ Research task message sent")
        
        # Wait for response
        await asyncio.sleep(3)
        
        # Check message history
        history = await test_agent.get_message_history()
        research_responses = [msg for msg in history if msg["message_type"] in ["scrape_result", "scrape_error"]]
        
        if research_responses:
            response = research_responses[-1]  # Get latest response
            if response["message_type"] == "scrape_result":
                print("✅ Received successful scrape result via message queue")
                return True
            else:
                print(f"❌ Received error response: {response.get('payload', {}).get('error')}")
                return False
        else:
            print("⚠️  No response received from research agent")
            return False
            
    except Exception as e:
        print(f"❌ Message queue integration test failed: {e}")
        return False

async def test_cache_functionality(agent: ResearchAgent):
    """Test caching functionality"""
    print("\n=== Testing Cache Functionality ===")
    
    try:
        # Clear cache first
        await agent.clear_cache()
        print("🧹 Cache cleared")
        
        # Get initial cache stats
        initial_stats = await agent.get_cache_stats()
        print(f"📊 Initial cache: {initial_stats['cache_files']} files")
        
        # Perform same scraping task twice
        url = "https://httpbin.org/html"
        task = ResearchTaskTemplates.web_scrape_task(url)
        task["task_id"] = "cache_test_1"
        
        # First request (should cache)
        print("🔄 First request (should cache)...")
        start_time = asyncio.get_event_loop().time()
        result1 = await agent.execute_task(task)
        first_duration = asyncio.get_event_loop().time() - start_time
        
        # Second request (should hit cache)
        print("⚡ Second request (should hit cache)...")
        task["task_id"] = "cache_test_2"
        start_time = asyncio.get_event_loop().time()
        result2 = await agent.execute_task(task)
        second_duration = asyncio.get_event_loop().time() - start_time
        
        # Check cache stats
        final_stats = await agent.get_cache_stats()
        print(f"📊 Final cache: {final_stats['cache_files']} files, {final_stats['cache_hits']} hits")
        
        # Verify both requests succeeded
        if result1["status"] == "completed" and result2["status"] == "completed":
            print(f"✅ Both requests completed")
            print(f"⏱️  First: {first_duration:.2f}s, Second: {second_duration:.2f}s")
            
            if second_duration < first_duration * 0.8:  # Should be significantly faster
                print("✅ Cache appears to be working (second request faster)")
                return True
            else:
                print("⚠️  Second request not significantly faster (cache may not be working)")
                return False
        else:
            print("❌ One or both requests failed")
            return False
            
    except Exception as e:
        print(f"❌ Cache functionality test failed: {e}")
        return False

async def run_comprehensive_tests():
    """Run all research agent tests"""
    print("🚀 Starting Comprehensive Research Agent Tests")
    print("Make sure Redis is running (docker-compose up)")
    print("=" * 60)
    
    # Test results tracking
    test_results = {}
    
    # Initialize agent
    agent = await test_research_agent_initialization()
    if not agent:
        print("❌ Cannot continue without agent initialization")
        return
    
    test_results["initialization"] = True
    
    try:
        # Test web scraping
        scrape_results = await test_web_scraping(agent)
        test_results["web_scraping"] = len(scrape_results) > 0
        
        # Test arXiv search
        arxiv_result = await test_arxiv_search(agent)
        test_results["arxiv_search"] = arxiv_result is not None
        
        # Test news search
        news_result = await test_news_search(agent)
        test_results["news_search"] = news_result is not None and news_result.get("status") != "skipped"
        
        # Test document parsing
        parse_results = await test_document_parsing(agent)
        test_results["document_parsing"] = len(parse_results) > 0
        
        # Test batch URL extraction
        batch_result = await test_batch_url_extraction(agent)
        test_results["batch_extraction"] = batch_result is not None
        
        # Test message queue integration
        mq_result = await test_message_queue_integration(agent)
        test_results["message_queue"] = mq_result
        
        # Test cache functionality
        cache_result = await test_cache_functionality(agent)
        test_results["cache"] = cache_result
        
        # Final agent status
        final_status = await agent.get_status()
        stats = final_status.get("statistics", {})
        
        print("\n" + "=" * 60)
        print("🏁 RESEARCH AGENT TEST SUMMARY")
        print("=" * 60)
        
        for test_name, result in test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name.replace('_', ' ').title():<25} {status}")
        
        print(f"\nAgent Statistics:")
        print(f"Total Requests: {stats.get('total_requests', 0)}")
        print(f"Successful: {stats.get('successful_requests', 0)}")
        print(f"Failed: {stats.get('failed_requests', 0)}")
        print(f"Cache Hits: {stats.get('cache_hits', 0)}")
        print(f"Documents Processed: {stats.get('documents_processed', 0)}")
        
        success_rate = sum(test_results.values()) / len(test_results) * 100
        print(f"\nOverall Success Rate: {success_rate:.1f}%")
        
        if success_rate >= 80:
            print("🎉 Research Agent is working well!")
        elif success_rate >= 60:
            print("⚠️  Research Agent has some issues but basic functionality works")
        else:
            print("❌ Research Agent has significant issues")
        
    finally:
        # Cleanup
        await agent.shutdown()

if __name__ == "__main__":
    asyncio.run(run_comprehensive_tests())