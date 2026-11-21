import re
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from pydantic import BaseModel, Field
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)



class RunbookChunk(BaseModel):
    """Structured representation of a single runbook section chunk."""
    chunk_id: str
    runbook_id: str = Field(description="Extracted ID, e.g. RB-DB-001")
    runbook_title: str
    service: str = Field(description="Normalized service domain: rds, kubernetes, vpc")
    section_title: str
    content: str = Field(description="Breadcrumb-enriched text used for embedding")
    source_file: str


class MarkdownRunbookChunker:
    """Header-aware Markdown chunker that preserves document breadcrumbs."""

    SERVICE_MAP = {
        "DB": "rds",
        "K8S": "kubernetes",
        "VPC": "vpc",
    }

    @classmethod
    def _extract_header_info(cls, markdown_text: str)->tuple[str, str, str]:
        """Extract runbook title, runbook_id (e.g., RB-DB-001), and normalized service."""
        header_match = re.search(r"^#\s+(.+?)\s*\((RB-([A-Z0-9]+)-\d+)\)", markdown_text, re.MULTILINE)
        if header_match:
            title = header_match.group(1).strip()
            runbook_id = header_match.group(2).strip()
            domain_code = header_match.group(3).strip()
            service = cls.SERVICE_MAP.get(domain_code, domain_code.lower())
            return title, runbook_id, service
        return "Untitled Runbook", "RB-GEN-000", "general"

    @classmethod
    def chunk_markdown(cls, markdown_text: str, source_file: str = "unknown.md") -> List[RunbookChunk]:
        """Split a Markdown runbook by '## ' headers while attaching parent context."""
        title, runbook_id, service = cls._extract_header_info(markdown_text)

        # Split on level-2 headers (## Section Name)
        sections = re.split(r"^##\s+", markdown_text, flags=re.MULTILINE)
        chunks: List[RunbookChunk] = []

        # sections[0] is before the first '## ', subsequent items are 'Section Title\nBody...'
        for idx, section_raw in enumerate(sections[1:], start=1):
            lines = section_raw.strip().splitlines()
            if not lines:
                continue
            section_title = lines[0].strip()
            section_body = "\n".join(lines[1:]).strip()
            if not section_body:
                continue
            enriched_content = (
                f"Runbook: {title} ({runbook_id})\n"
                f"Service: {service} | Section: {section_title}\n"
                f"{section_body}"
            )
            chunk_id = str(
                uuid.uuid5(uuid.NAMESPACE_DNS, f"{runbook_id}-{idx}-{section_title}")
            )
            chunks.append(
                RunbookChunk(
                    chunk_id=chunk_id,
                    runbook_id=runbook_id,
                    runbook_title=title,
                    service=service,
                    section_title=section_title,
                    content=enriched_content,
                    source_file=source_file,
                )
            )
        return chunks

    @classmethod
    def chunk_directory(cls, directory_path: Path) -> List[RunbookChunk]:
        """Parse and chunk all Markdown (.md) files in a directory."""
        all_chunks: List[RunbookChunk] = []
        for me_file in sorted(directory_path.glob("*.md")):
            text = me_file.read_text(encoding="utf-8")
            all_chunks.extend(cls.chunk_markdown(text, source_file=str(me_file.name)))
        return all_chunks


class QdrantRunbookStore:
    """Vector database wrapper for indexing and querying incident runbooks in Qdrant."""

    def __init__(
        self,
        collection_name: str = "sentinel_runbooks",
        qdrant_client: Optional[QdrantClient] = None,
        embed_fn: Optional[Callable[[str], List[float]]] = None,
        vector_size: int = 384,
    ):
        self.collection_name = collection_name
        self.client = qdrant_client or QdrantClient(":memory:")
        self.vector_size = vector_size
        self._embed_fn = embed_fn
        self._st_model = None
        self._ensure_collection()

    def _ensure_collection(self)->None:
        """Create the Qdrant collection if it does not already exist."""
        existing = [c.name for c in self.client.get_collections().collections]
        if self.collection_name not in existing:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size, distance=Distance.COSINE
                ),
            )

    def embed_text(
        self,
        text: str,
    )-> List[float]:
        """Generate dense embedding vector for text using injected function or SentenceTransformer."""
        if self._embed_fn is not None:
            return self._embed_fn(text)

        if self._st_model is None:
            from sentence_transformers import SentenceTransformer
            self._st_model = SentenceTransformer("all-MiniLM-L6-v2")

        vector = self._st_model.encode(text, normalize_embeddings=True)
        return vector.tolist()

    def index_chunks(self, chunks: List[RunbookChunk]) -> int:
        """Embed and upsert runbook chunks into Qdrant."""
        points: List[PointStruct] = []
        for chunk in chunks:
            vector = self.embed_text(chunk.content)
            points.append(
                PointStruct(
                    id=chunk.chunk_id,
                    vector=vector,
                    payload=chunk.model_dump(),
                )
            )
        if points:
            self.client.upsert(collection_name=self.collection_name, points=points)
        return len(points)

    def search(
            self,
            query: str,
            top_k: int = 3,
            service_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Perform dense semantic search with optional metadata payload filtering."""
        query_vector = self.embed_text(query)

        qdrant_filter = None
        if service_filter:
            qdrant_filter = Filter(
                must=[
                    FieldCondition(
                        key="service",
                        match=MatchValue(value=service_filter.lower()),
                    )
                ]
            )
        response = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            query_filter=qdrant_filter,
            limit=top_k,
        )

        results: List[Dict[str, Any]] = []
        for point in response.points:
            payload = dict(point.payload or {})
            payload["score"] = point.score
            results.append(payload)
        return results


        




        



    