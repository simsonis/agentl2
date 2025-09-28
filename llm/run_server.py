#!/usr/bin/env python3
"""
LLM Agent Server runner.
"""

import os
import sys
import uvicorn
from pathlib import Path

# Add src to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

if __name__ == "__main__":
    # Set environment variables if not set
    if not os.getenv("OPENAI_API_KEY"):
        print("Warning: OPENAI_API_KEY environment variable not set")

    uvicorn.run(
        "agentl2_llm.api.server:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )