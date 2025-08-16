from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings as ChromaSettings
import openai
import numpy as np

from core.config import settings

class VectorStore(ABC):
    @abstractmethod
    async def add_documents(self, documents: List[Dict[str, Any]]) -> bool:
        pass
    
    @abstractmethod
    async def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        pass
    
    @abstractmethod
    async def delete_documents(self, document_ids: List[str]) -> bool:
        pass

class ChromaVectorStore(VectorStore):
    def __init__(self):
        self.client = chromadb.HttpClient(
            host=settings.CHROMA_HOST,
            port=settings.CHROMA_PORT,
            settings=ChromaSettings(allow_reset=True, anonymized_telemetry=False)
        )
        self.collection_name = "research_documents"
        self.collection = None
    
    async def initialize(self):
        """Initialize the collection"""
        try:
            self.collection = self.client.get_collection(name=self.collection_name)
        except:
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "Research documents and sources"}
            )
    
    def _get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using OpenAI"""
        openai.api_key = settings.OPENAI_API_KEY
        
        embeddings = []
        for text in texts:
            response = openai.Embedding.create(
                model="text-embedding-ada-002",
                input=text
            )
            embeddings.append(response['data'][0]['embedding'])
        
        return embeddings
    
    async def add_documents(self, documents: List[Dict[str, Any]]) -> bool:
        """Add documents to vector store"""
        try:
            if not self.collection:
                await self.initialize()
            
            ids = [doc['id'] for doc in documents]
            texts = [doc['content'] for doc in documents]
            metadatas = [doc.get('metadata', {}) for doc in documents]
            
            embeddings = self._get_embeddings(texts)
            
            self.collection.add(
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
            
            return True
            
        except Exception as e:
            logging.error(f"Error adding documents: {e}")
            return False
    
    async def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Search for similar documents"""
        try:
            if not self.collection:
                await self.initialize()
            
            query_embedding = self._get_embeddings([query])[0]
            
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=k
            )
            
            documents = []
            for i in range(len(results['ids'][0])):
                documents.append({
                    'id': results['ids'][0][i],
                    'content': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i]
                })
            
            return documents
            
        except Exception as e:
            logging.error(f"Error searching documents: {e}")
            return []

# Factory function
def get_vector_store() -> VectorStore:
    if settings.VECTOR_DB_TYPE == "chroma":
        return ChromaVectorStore()
    else:
        raise ValueError(f"Unsupported vector store type: {settings.VECTOR_DB_TYPE}")