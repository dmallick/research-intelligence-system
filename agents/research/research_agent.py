# agents/research/research_agent.py
import asyncio
import aiohttp
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone
import re
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass
import json
import hashlib

# Web scraping imports
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Browser, Page
import feedparser
import arxiv

# Document processing imports
import PyPDF2
import docx
from io import BytesIO

from agents.base.agent import BaseAgent, AgentMessage

@dataclass
class ResearchResult:
    """Data class for research results"""
    url: str
    title: str
    content: str
    metadata: Dict[str, Any]
    extracted_at: datetime
    content_type: str
    word_count: int
    source_quality_score: float

@dataclass
class SearchQuery:
    """Data class for search queries"""
    query: str
    search_type: str  # "web", "academic", "news"
    max_results: int = 10
    date_filter: Optional[str] = None
    domain_filter: Optional[List[str]] = None

class ResearchAgent(BaseAgent):
    """
    Research Agent for web scraping, academic paper retrieval, and content extraction
    """
    
    def __init__(self, agent_id: str = None):
        super().__init__("research", agent_id or "research_agent_001")
        self.browser: Optional[Browser] = None
        self.playwright_context = None
        
        # Configuration
        self.max_content_length = 50000  # Maximum content length to extract
        self.request_timeout = 30  # HTTP request timeout in seconds
        self.concurrent_requests = 5  # Max concurrent requests
        
        # Headers for web scraping
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
    
    async def initialize_browser(self):
        """Initialize Playwright browser for JavaScript-heavy sites"""
        try:
            if not self.playwright_context:
                self.playwright_context = await async_playwright().start()
                self.browser = await self.playwright_context.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-dev-shm-usage']
                )
                self.logger.info("Playwright browser initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize browser: {e}")
    
    async def close_browser(self):
        """Close Playwright browser"""
        try:
            if self.browser:
                await self.browser.close()
            if self.playwright_context:
                await self.playwright_context.stop()
            self.logger.info("Browser closed")
        except Exception as e:
            self.logger.error(f"Error closing browser: {e}")
    
    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process a research task"""
        task_type = task.get("task_type")
        
        try:
            if task_type == "web_research":
                return await self._handle_web_research(task)
            elif task_type == "academic_search":
                return await self._handle_academic_search(task)
            elif task_type == "news_search":
                return await self._handle_news_search(task)
            elif task_type == "document_extraction":
                return await self._handle_document_extraction(task)
            elif task_type == "url_analysis":
                return await self._handle_url_analysis(task)
            else:
                return {
                    "status": "error",
                    "task_id": task.get("task_id"),
                    "error": f"Unknown task type: {task_type}"
                }
                
        except Exception as e:
            self.logger.error(f"Error processing task {task.get('task_id')}: {e}")
            return {
                "status": "error",
                "task_id": task.get("task_id"),
                "error": str(e)
            }
    
    async def _handle_web_research(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Handle general web research task"""
        query_data = task.get("query", {})
        search_query = SearchQuery(**query_data)
        
        # Perform web search using multiple search engines
        results = await self._perform_web_search(search_query)
        
        # Extract content from top results
        extracted_results = []
        semaphore = asyncio.Semaphore(self.concurrent_requests)
        
        async def extract_content(result):
            async with semaphore:
                return await self._extract_web_content(result["url"])
        
        # Process URLs concurrently
        extraction_tasks = [extract_content(result) for result in results[:search_query.max_results]]
        extraction_results = await asyncio.gather(*extraction_tasks, return_exceptions=True)
        
        # Filter successful extractions
        for i, result in enumerate(extraction_results):
            if isinstance(result, ResearchResult):
                extracted_results.append({
                    "url": result.url,
                    "title": result.title,
                    "content": result.content[:2000] + "..." if len(result.content) > 2000 else result.content,
                    "metadata": result.metadata,
                    "word_count": result.word_count,
                    "quality_score": result.source_quality_score,
                    "extracted_at": result.extracted_at.isoformat()
                })
        
        return {
            "status": "completed",
            "task_id": task.get("task_id"),
            "query": search_query.query,
            "results_found": len(extracted_results),
            "results": extracted_results,
            "metadata": {
                "search_type": "web_research",
                "processed_at": datetime.now(timezone.utc).isoformat()
            }
        }
    
    async def _handle_academic_search(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Handle academic paper search via arXiv"""
        query = task.get("query", "")
        max_results = task.get("max_results", 10)
        
        try:
            # Search arXiv
            search = arxiv.Search(
                query=query,
                max_results=max_results,
                sort_by=arxiv.SortCriterion.Relevance
            )
            
            papers = []
            for paper in search.results():
                papers.append({
                    "title": paper.title,
                    "authors": [str(author) for author in paper.authors],
                    "abstract": paper.summary,
                    "url": paper.entry_id,
                    "pdf_url": paper.pdf_url,
                    "published": paper.published.isoformat() if paper.published else None,
                    "categories": paper.categories,
                    "metadata": {
                        "doi": paper.doi,
                        "journal_ref": paper.journal_ref,
                        "primary_category": paper.primary_category
                    }
                })
            
            return {
                "status": "completed",
                "task_id": task.get("task_id"),
                "query": query,
                "results_found": len(papers),
                "results": papers,
                "metadata": {
                    "search_type": "academic",
                    "source": "arxiv",
                    "processed_at": datetime.now(timezone.utc).isoformat()
                }
            }
            
        except Exception as e:
            self.logger.error(f"Academic search error: {e}")
            return {
                "status": "error",
                "task_id": task.get("task_id"),
                "error": f"Academic search failed: {str(e)}"
            }
    
    async def _handle_news_search(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Handle news search and RSS feed processing"""
        query = task.get("query", "")
        news_sources = task.get("sources", [
            "https://rss.cnn.com/rss/edition.rss",
            "https://feeds.bbci.co.uk/news/rss.xml",
            "https://feeds.reuters.com/reuters/topNews"
        ])
        
        results = []
        
        for source_url in news_sources:
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                    async with session.get(source_url, headers=self.headers) as response:
                        if response.status == 200:
                            content = await response.text()
                            feed = feedparser.parse(content)
                            
                            for entry in feed.entries[:5]:  # Top 5 from each source
                                # Simple keyword matching for relevance
                                if query.lower() in (entry.title + " " + entry.get('summary', '')).lower():
                                    results.append({
                                        "title": entry.title,
                                        "url": entry.link,
                                        "summary": entry.get('summary', ''),
                                        "published": entry.get('published', ''),
                                        "source": feed.feed.get('title', source_url),
                                        "metadata": {
                                            "tags": entry.get('tags', []),
                                            "author": entry.get('author', '')
                                        }
                                    })
            except Exception as e:
                self.logger.warning(f"Failed to fetch news from {source_url}: {e}")
        
        return {
            "status": "completed",
            "task_id": task.get("task_id"),
            "query": query,
            "results_found": len(results),
            "results": results[:task.get("max_results", 20)],
            "metadata": {
                "search_type": "news",
                "sources_checked": len(news_sources),
                "processed_at": datetime.now(timezone.utc).isoformat()
            }
        }
    
    async def _handle_document_extraction(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Handle document content extraction (PDF, DOCX, etc.)"""
        document_url = task.get("url")
        document_type = task.get("document_type", "auto")
        
        try:
            # Download document
            async with aiohttp.ClientSession() as session:
                async with session.get(document_url, headers=self.headers) as response:
                    if response.status != 200:
                        raise Exception(f"Failed to download document: HTTP {response.status}")
                    
                    content_bytes = await response.read()
                    
                    # Auto-detect document type if not specified
                    if document_type == "auto":
                        content_type = response.headers.get('content-type', '').lower()
                        if 'pdf' in content_type:
                            document_type = "pdf"
                        elif 'word' in content_type or 'docx' in content_type:
                            document_type = "docx"
                        else:
                            document_type = "html"
            
            # Extract content based on type
            if document_type == "pdf":
                extracted_text = await self._extract_pdf_content(content_bytes)
            elif document_type == "docx":
                extracted_text = await self._extract_docx_content(content_bytes)
            else:
                extracted_text = await self._extract_html_content(content_bytes.decode('utf-8'))
            
            return {
                "status": "completed",
                "task_id": task.get("task_id"),
                "document_url": document_url,
                "document_type": document_type,
                "content": extracted_text[:5000] + "..." if len(extracted_text) > 5000 else extracted_text,
                "word_count": len(extracted_text.split()),
                "metadata": {
                    "extraction_method": f"{document_type}_extraction",
                    "processed_at": datetime.now(timezone.utc).isoformat()
                }
            }
            
        except Exception as e:
            self.logger.error(f"Document extraction error: {e}")
            return {
                "status": "error",
                "task_id": task.get("task_id"),
                "error": f"Document extraction failed: {str(e)}"
            }
    
    async def _handle_url_analysis(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Handle detailed analysis of a specific URL"""
        url = task.get("url")
        
        try:
            result = await self._extract_web_content(url, detailed_analysis=True)
            
            return {
                "status": "completed",
                "task_id": task.get("task_id"),
                "url": url,
                "analysis": {
                    "title": result.title,
                    "content_preview": result.content[:1000] + "..." if len(result.content) > 1000 else result.content,
                    "word_count": result.word_count,
                    "quality_score": result.source_quality_score,
                    "metadata": result.metadata,
                    "extracted_at": result.extracted_at.isoformat()
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "task_id": task.get("task_id"),
                "error": f"URL analysis failed: {str(e)}"
            }
    
    async def _perform_web_search(self, search_query: SearchQuery) -> List[Dict[str, Any]]:
        """Perform web search using DuckDuckGo (no API key required)"""
        # This is a simplified implementation
        # In production, you might want to integrate with proper search APIs
        search_results = [
            {
                "url": "https://example.com/result1",
                "title": f"Search result for '{search_query.query}' - Result 1",
                "snippet": "This is a sample search result..."
            },
            {
                "url": "https://example.com/result2", 
                "title": f"Search result for '{search_query.query}' - Result 2",
                "snippet": "Another sample search result..."
            }
        ]
        
        return search_results
    
    async def _extract_web_content(self, url: str, detailed_analysis: bool = False) -> ResearchResult:
        """Extract content from a web page"""
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.request_timeout)
            ) as session:
                async with session.get(url, headers=self.headers) as response:
                    if response.status != 200:
                        raise Exception(f"HTTP {response.status} for {url}")
                    
                    html_content = await response.text()
                    
            # Parse with BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract title
            title = "No Title"
            if soup.title:
                title = soup.title.string.strip()
            elif soup.find('h1'):
                title = soup.find('h1').get_text().strip()
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header", "aside"]):
                script.decompose()
            
            # Extract main content
            content = ""
            
            # Try to find main content areas
            main_content = (
                soup.find('main') or 
                soup.find('article') or 
                soup.find('div', class_=re.compile(r'content|main|body', re.I)) or
                soup.find('div', id=re.compile(r'content|main|body', re.I))
            )
            
            if main_content:
                content = main_content.get_text()
            else:
                content = soup.get_text()
            
            # Clean up content
            content = re.sub(r'\s+', ' ', content).strip()
            content = content[:self.max_content_length]
            
            # Calculate quality score
            quality_score = self._calculate_quality_score(content, url, soup)
            
            # Extract metadata
            metadata = self._extract_metadata(soup, url, detailed_analysis)
            
            return ResearchResult(
                url=url,
                title=title,
                content=content,
                metadata=metadata,
                extracted_at=datetime.now(timezone.utc),
                content_type="text/html",
                word_count=len(content.split()),
                source_quality_score=quality_score
            )
            
        except Exception as e:
            self.logger.error(f"Content extraction failed for {url}: {e}")
            raise
    
    async def _extract_pdf_content(self, pdf_bytes: bytes) -> str:
        """Extract text content from PDF"""
        try:
            pdf_file = BytesIO(pdf_bytes)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            
            return text.strip()
            
        except Exception as e:
            self.logger.error(f"PDF extraction error: {e}")
            raise
    
    async def _extract_docx_content(self, docx_bytes: bytes) -> str:
        """Extract text content from DOCX"""
        try:
            doc_file = BytesIO(docx_bytes)
            doc = docx.Document(doc_file)
            
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            
            return text.strip()
            
        except Exception as e:
            self.logger.error(f"DOCX extraction error: {e}")
            raise
    
    async def _extract_html_content(self, html: str) -> str:
        """Extract text from HTML content"""
        soup = BeautifulSoup(html, 'html.parser')
        return soup.get_text()
    
    def _calculate_quality_score(self, content: str, url: str, soup: BeautifulSoup) -> float:
        """Calculate content quality score (0-1)"""
        score = 0.5  # Base score
        
        # Content length factor
        if len(content) > 500:
            score += 0.1
        if len(content) > 2000:
            score += 0.1
        
        # Domain reputation (simplified)
        domain = urlparse(url).netloc.lower()
        trusted_domains = ['wikipedia.org', 'scholar.google.com', 'arxiv.org', 'nature.com', 'science.org']
        if any(trusted in domain for trusted in trusted_domains):
            score += 0.2
        
        # Presence of structured content
        if soup.find_all(['h1', 'h2', 'h3']):
            score += 0.05
        if soup.find_all('p'):
            score += 0.05
        
        return min(1.0, score)
    
    def _extract_metadata(self, soup: BeautifulSoup, url: str, detailed: bool = False) -> Dict[str, Any]:
        """Extract metadata from HTML"""
        metadata = {
            "url": url,
            "domain": urlparse(url).netloc
        }
        
        # Meta tags
        meta_tags = soup.find_all('meta')
        for tag in meta_tags:
            if tag.get('name') == 'description':
                metadata['description'] = tag.get('content', '')[:200]
            elif tag.get('name') == 'keywords':
                metadata['keywords'] = tag.get('content', '').split(',')
            elif tag.get('name') == 'author':
                metadata['author'] = tag.get('content', '')
            elif tag.get('property') == 'og:title':
                metadata['og_title'] = tag.get('content', '')
        
        if detailed:
            # Additional analysis for detailed mode
            metadata.update({
                'headings_count': len(soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])),
                'paragraphs_count': len(soup.find_all('p')),
                'links_count': len(soup.find_all('a')),
                'images_count': len(soup.find_all('img'))
            })
        
        return metadata
    
    async def _handle_message(self, message: AgentMessage):
        """Handle incoming messages"""
        self.logger.info(f"Research agent received message: {message.message_type}")
        
        if message.message_type == "research_request":
            # Handle research request
            task_data = message.content
            result = await self.process_task(task_data)
            
            # Send result back
            await self.send_message(
                message.sender_id,
                "research_result",
                result,
                correlation_id=message.correlation_id
            )
        
        elif message.message_type == "ping":
            # Health check response
            await self.send_message(
                message.sender_id,
                "pong", 
                {
                    "agent_type": self.agent_type,
                    "status": "healthy",
                    "capabilities": [
                        "web_research",
                        "academic_search", 
                        "news_search",
                        "document_extraction",
                        "url_analysis"
                    ]
                },
                correlation_id=message.correlation_id
            )
        
        else:
            self.logger.warning(f"Unknown message type: {message.message_type}")

# Convenience function for creating research agent
async def create_research_agent(agent_id: str = None) -> ResearchAgent:
    """Create and initialize a research agent"""
    agent = ResearchAgent(agent_id)
    await agent.initialize()
    await agent.initialize_browser()
    return agent