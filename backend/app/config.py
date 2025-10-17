"""Configuration management for the Math Agent application."""
import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings."""
    
    # API Keys
    github_token: str = Field(..., env="GITHUB_TOKEN")
    tavily_api_key: str = Field(..., env="TAVILY_API_KEY")
    
    # Supabase Configuration
    supabase_url: str = Field(..., env="SUPABASE_URL")
    supabase_key: str = Field(..., env="SUPABASE_KEY")
    supabase_service_key: Optional[str] = Field(None, env="SUPABASE_SERVICE_KEY")
    
    # LangSmith Configuration (Optional)
    langchain_tracing_v2: bool = Field(False, env="LANGCHAIN_TRACING_V2")
    langchain_endpoint: Optional[str] = Field(None, env="LANGCHAIN_ENDPOINT")
    langchain_api_key: Optional[str] = Field(None, env="LANGCHAIN_API_KEY")
    langchain_project: str = Field("math-agent", env="LANGCHAIN_PROJECT")
    
    # Application Settings
    environment: str = Field("development", env="ENVIRONMENT")
    debug: bool = Field(True, env="DEBUG")
    log_level: str = Field("INFO", env="LOG_LEVEL")
    
    # MCP Configuration
    mcp_server_port: int = Field(3000, env="MCP_SERVER_PORT")
    
    # Model Configuration - GitHub Models
    github_api_base: str = "https://models.github.ai/inference"
    llm_model: str = "gpt-4o"  # GitHub Models available model
    embedding_model: str = "text-embedding-3-small"
    temperature: float = 0.1
    max_tokens: int = 2000
    
    # Vector Store Configuration
    collection_name: str = "math_knowledge_base"
    similarity_threshold: float = 0.7
    top_k_results: int = 5
    
    # Guardrails Configuration
    max_question_length: int = 500
    allowed_topics: list = ["mathematics", "math", "algebra", "geometry", 
                           "calculus", "trigonometry", "statistics", 
                           "probability", "arithmetic", "number theory"]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
