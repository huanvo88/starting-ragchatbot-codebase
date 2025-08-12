import os
import json
from dataclasses import dataclass
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file
load_dotenv()

# Load model configuration
def load_model_config():
    """Load model configuration from JSON file"""
    config_path = Path(__file__).parent / "model_config.json"
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # Fallback configuration if file doesn't exist
        return {
            "ollama": {"default_model": "qwen2.5:7b"},
            "anthropic": {"default_model": "claude-sonnet-4-20250514"}
        }

@dataclass
class Config:
    """Configuration settings for the RAG system"""
    def __post_init__(self):
        """Load model configuration after initialization"""
        self.model_config = load_model_config()
    
    # AI Provider settings - defaults to local Ollama
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "ollama")  # "anthropic" or "ollama"
    
    # Anthropic API settings
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    
    # Ollama settings
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    
    @property
    def ANTHROPIC_MODEL(self) -> str:
        """Get Anthropic model from config file"""
        return os.getenv("ANTHROPIC_MODEL", 
                        getattr(self, 'model_config', {}).get('anthropic', {}).get('default_model', 'claude-sonnet-4-20250514'))
    
    @property 
    def OLLAMA_MODEL(self) -> str:
        """Get Ollama model from config file"""
        return os.getenv("OLLAMA_MODEL",
                        getattr(self, 'model_config', {}).get('ollama', {}).get('default_model', 'qwen2.5:7b'))
    
    # Embedding model settings
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    
    # Document processing settings
    CHUNK_SIZE: int = 800       # Size of text chunks for vector storage
    CHUNK_OVERLAP: int = 100     # Characters to overlap between chunks
    MAX_RESULTS: int = 5         # Maximum search results to return
    MAX_HISTORY: int = 2         # Number of conversation messages to remember
    
    # Database paths
    CHROMA_PATH: str = "./chroma_db"  # ChromaDB storage location

config = Config()


