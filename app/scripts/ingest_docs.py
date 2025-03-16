"""Script to ingest documents into the knowledge base."""

import asyncio
import sys
from pathlib import Path

async def main():
    from app.dependencies import knowledge_base

    # ingest README by default
    readme_path = Path("README.md")
    if readme_path.exists():
        chunks = await knowledge_base.ingest(str(readme_path))
        print(f"✓ Ingested README.md: {chunks} chunks")

    # ingest any files from docs/ directory if it exists
    docs_dir = Path("docs")
    if docs_dir.exists():
        for doc_file in docs_dir.glob("*.md"):
            chunks = await knowledge_base.ingest(str(doc_file))
            print(f"✓ Ingested {doc_file.name}: {chunks} chunks")

    print(f"\nKnowledge base stats: {knowledge_base.stats}")

if __name__ == "__main__":
    asyncio.run(main())
