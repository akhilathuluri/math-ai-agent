"""Supabase Vector Store for mathematical knowledge base."""
import os
from typing import List, Dict, Any, Optional
from supabase import create_client, Client
from openai import OpenAI
import numpy as np
from app.config import settings


class SupabaseVectorStore:
    """Manages vector storage and retrieval using Supabase with pgvector."""
    
    def __init__(self):
        """Initialize Supabase client and GitHub Models client for embeddings."""
        self.supabase: Client = create_client(
            settings.supabase_url,
            settings.supabase_key
        )
        # Use GitHub Models endpoint
        self.openai_client = OpenAI(
            api_key=settings.github_token,
            base_url=settings.github_api_base
        )
        self.collection_name = settings.collection_name
        
    async def initialize_schema(self):
        """Initialize the database schema with pgvector extension."""
        # Note: This SQL should be run directly in Supabase SQL editor
        sql = """
        -- Enable pgvector extension
        CREATE EXTENSION IF NOT EXISTS vector;
        
        -- Create knowledge base table
        CREATE TABLE IF NOT EXISTS math_knowledge_base (
            id BIGSERIAL PRIMARY KEY,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            solution_steps JSONB,
            topic VARCHAR(100),
            difficulty VARCHAR(20),
            source VARCHAR(100),
            metadata JSONB,
            embedding vector(1536),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        -- Create index for vector similarity search
        CREATE INDEX IF NOT EXISTS math_kb_embedding_idx 
        ON math_knowledge_base 
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100);
        
        -- Create feedback table for human-in-the-loop
        CREATE TABLE IF NOT EXISTS feedback (
            id BIGSERIAL PRIMARY KEY,
            question_id BIGINT REFERENCES math_knowledge_base(id),
            user_question TEXT NOT NULL,
            generated_answer TEXT NOT NULL,
            user_feedback TEXT,
            rating INTEGER CHECK (rating >= 1 AND rating <= 5),
            corrections JSONB,
            is_correct BOOLEAN,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        -- Create sessions table to track agent interactions
        CREATE TABLE IF NOT EXISTS agent_sessions (
            id BIGSERIAL PRIMARY KEY,
            session_id UUID DEFAULT gen_random_uuid(),
            question TEXT NOT NULL,
            routing_decision VARCHAR(50),
            knowledge_base_match BOOLEAN,
            web_search_performed BOOLEAN,
            final_answer TEXT,
            confidence_score FLOAT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """
        print("Schema SQL generated. Please run this in Supabase SQL editor.")
        return sql
    
    def get_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using GitHub Models (OpenAI compatible)."""
        response = self.openai_client.embeddings.create(
            model=f"openai/{settings.embedding_model}",  # GitHub Models format
            input=text
        )
        return response.data[0].embedding
    
    async def add_documents(
        self,
        documents: List[Dict[str, Any]]
    ) -> List[int]:
        """
        Add documents to the knowledge base.
        
        Args:
            documents: List of dicts with keys: question, answer, solution_steps, 
                      topic, difficulty, source, metadata
        
        Returns:
            List of inserted document IDs
        """
        inserted_ids = []
        
        for doc in documents:
            # Generate embedding for the question
            embedding = self.get_embedding(doc['question'])
            
            # Prepare data for insertion
            data = {
                'question': doc['question'],
                'answer': doc['answer'],
                'solution_steps': doc.get('solution_steps', {}),
                'topic': doc.get('topic', 'general'),
                'difficulty': doc.get('difficulty', 'medium'),
                'source': doc.get('source', 'unknown'),
                'metadata': doc.get('metadata', {}),
                'embedding': embedding
            }
            
            # Insert into Supabase
            result = self.supabase.table(self.collection_name).insert(data).execute()
            if result.data:
                inserted_ids.append(result.data[0]['id'])
        
        return inserted_ids
    
    async def similarity_search(
        self,
        query: str,
        k: int = None,
        threshold: float = None
    ) -> List[Dict[str, Any]]:
        """
        Perform similarity search for a query.
        
        Args:
            query: The question to search for
            k: Number of results to return
            threshold: Minimum similarity threshold
        
        Returns:
            List of matching documents with similarity scores
        """
        if k is None:
            k = settings.top_k_results
        if threshold is None:
            threshold = settings.similarity_threshold
        
        # Generate embedding for query
        query_embedding = self.get_embedding(query)
        
        # Perform similarity search using RPC function
        # Note: You need to create this function in Supabase
        result = self.supabase.rpc(
            'match_math_documents',
            {
                'query_embedding': query_embedding,
                'match_threshold': threshold,
                'match_count': k
            }
        ).execute()
        
        return result.data if result.data else []
    
    async def get_by_id(self, doc_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve a document by ID."""
        result = self.supabase.table(self.collection_name)\
            .select("*")\
            .eq('id', doc_id)\
            .execute()
        
        return result.data[0] if result.data else None
    
    async def update_document(self, doc_id: int, updates: Dict[str, Any]) -> bool:
        """Update a document in the knowledge base."""
        result = self.supabase.table(self.collection_name)\
            .update(updates)\
            .eq('id', doc_id)\
            .execute()
        
        return bool(result.data)
    
    async def delete_document(self, doc_id: int) -> bool:
        """Delete a document from the knowledge base."""
        result = self.supabase.table(self.collection_name)\
            .delete()\
            .eq('id', doc_id)\
            .execute()
        
        return bool(result.data)
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the knowledge base."""
        # Total count
        total_result = self.supabase.table(self.collection_name)\
            .select("*", count='exact')\
            .execute()
        
        # Count by topic
        topic_result = self.supabase.table(self.collection_name)\
            .select("topic")\
            .execute()
        
        topics = {}
        for row in topic_result.data:
            topic = row.get('topic', 'unknown')
            topics[topic] = topics.get(topic, 0) + 1
        
        return {
            'total_documents': total_result.count,
            'topics': topics
        }


# Create RPC function SQL for Supabase
MATCH_DOCUMENTS_RPC = """
CREATE OR REPLACE FUNCTION match_math_documents(
    query_embedding vector(1536),
    match_threshold float,
    match_count int
)
RETURNS TABLE (
    id bigint,
    question text,
    answer text,
    solution_steps jsonb,
    topic varchar,
    difficulty varchar,
    source varchar,
    metadata jsonb,
    similarity float
)
LANGUAGE sql STABLE
AS $$
    SELECT
        id,
        question,
        answer,
        solution_steps,
        topic,
        difficulty,
        source,
        metadata,
        1 - (embedding <=> query_embedding) as similarity
    FROM math_knowledge_base
    WHERE 1 - (embedding <=> query_embedding) > match_threshold
    ORDER BY embedding <=> query_embedding
    LIMIT match_count;
$$;
"""
