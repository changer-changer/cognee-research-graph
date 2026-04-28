import os

# =============================================================================
# LLM Configuration (required for M2.3 academic extraction)
# =============================================================================
# Set LLM_API_KEY in your environment, e.g.:
#   export LLM_API_KEY="sk-..."
#   export LLM_BASE_URL="https://api.moonshot.cn/v1"
#   export LLM_MODEL="kimi-latest"
#
# Supported providers: OpenAI-compatible APIs (Kimi, OpenAI, etc.)
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.moonshot.cn/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "kimi-latest")

# =============================================================================
# GROBID Configuration
# =============================================================================
# GROBID must be running locally. Default port is 8070.
# To start: cd grobid && ./gradlew run
GROBID_URL = os.getenv("GROBID_URL", "http://localhost:8070")

# =============================================================================
# Cognee Embedding Configuration (required for vector indexing)
# =============================================================================
# Option A: Use fastembed (local, no API key needed)
#   export EMBEDDING_PROVIDER=fastembed
#   export EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
#   export EMBEDDING_DIMENSIONS=384
#
# Option B: Use OpenAI embeddings
#   export EMBEDDING_PROVIDER=openai
#   export EMBEDDING_MODEL=text-embedding-3-large
#   export EMBEDDING_API_KEY=$OPENAI_API_KEY
# =============================================================================

# =============================================================================
# Cognee Runtime Configuration
# =============================================================================
# Skip LLM connection test on startup (useful when only running ingestion)
#   export COGNEE_SKIP_CONNECTION_TEST=true
#
# Disable multi-user access control for local development
#   export ENABLE_BACKEND_ACCESS_CONTROL=false
# =============================================================================

# =============================================================================
# Project Paths
# =============================================================================
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
ALIASES_PATH = os.path.join(DATA_DIR, "aliases.json")
LEARNED_ALIASES_PATH = os.path.join(DATA_DIR, "learned_aliases.json")
UNMATCHED_CITATIONS_PATH = os.path.join(DATA_DIR, "unmatched_citations.json")
PAPERS_DIR = os.path.join(DATA_DIR, "papers")
