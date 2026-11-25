import re
from typing import List, Dict, Any, Optional
from rank_bm25 import BM25Okapi
from app.rag.embeddings import RunbookChunk, QdrantRunbookStore


class QueryRewriter:
    """Expands raw monitoring alerts and cryptic error codes with domain context."""

    EXPANSION_RULES: Dict[str, str] = {
        "137": "OOMKilled exit_code 137 container memory limit exceeded",
        "oom": "OOMKilled container_memory_working_set_bytes memory limit",
        "53300": "PostgreSQL FATAL remaining connection slots reserved DatabaseConnections",
        "pgbouncer": "database connection pooler idle sockets",
        "snat": "VPC NAT Gateway ErrorPortAllocation PacketsDropCount outbound port exhaustion",
        "port allocation": "ErrorPortAllocation NAT Gateway Elastic IP SNAT",
    }

    @classmethod
    def rewrite(cls, raw_query: str) -> str:
        """Return query enriched with matching SRE technical terms."""
        lowered = raw_query.lower()
        expansions: List[str] = []
        for trigger, addition in cls.EXPANSION_RULES.items():
            if trigger in lowered:
                expansions.append(addition)

        if not expansions:
            return raw_query
        return f"{raw_query} ({' '.join(expansions)})"


class BM25RunbookIndex:
    """Sparse lexical retriever using BM25Okapi with technical identifier preservation."""

    def __init__(self, chunks: Optional[List[RunbookChunk]] = None):
        self._chunks: List[RunbookChunk] = []
        self._bm25: Optional[BM25Okapi] = None
        if chunks:
            self.index_chunks(chunks)

    @staticmethod
    def tokenize(text: str) -> List[str]:
        """Extract alphanumeric tokens, preserving error numbers and underscores."""
        return re.findall(r"[a-z0-9_]+", text.lower())

    def index_chunks(self, chunks: List[RunbookChunk]) -> int:
        """Build BM25 inverted index over runbook chunks."""
        self._chunks = list(chunks)
        tokenized_corpus = [self.tokenize(c.content) for c in self._chunks]
        if tokenized_corpus:
            self._bm25 = BM25Okapi(tokenized_corpus)
        return len(self._chunks)

    def search(
        self,
        query: str,
        top_k: int = 5,
        service_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Perform sparse BM25 keyword search with optional service domain filtering."""
        if not self._bm25 or not self._chunks:
            return []

        query_tokens = self.tokenize(query)
        scores = self._bm25.get_scores(query_tokens)

        scored_items: List[tuple[float, RunbookChunk]] = []
        for score, chunk in zip(scores, self._chunks):
            if service_filter and chunk.service.lower() != service_filter.lower():
                continue
            scored_items.append((float(score), chunk))

        scored_items.sort(key=lambda item: item[0], reverse=True)

        results: List[Dict[str, Any]] = []
        for score, chunk in scored_items[:top_k]:
            payload = chunk.model_dump()
            payload["bm25_score"] = score
            results.append(payload)
        return results


class HybridRunbookRetriever:
    """Combines Dense Qdrant vector search and Sparse BM25 search via Reciprocal Rank Fusion."""

    def __init__(
        self,
        vector_store: QdrantRunbookStore,
        bm25_index: Optional[BM25RunbookIndex] = None,
        rrf_k: int = 60,
    ):
        self.vector_store = vector_store
        self.bm25_index = bm25_index or BM25RunbookIndex()
        self.rrf_k = rrf_k

    def index_chunks(self, chunks: List[RunbookChunk]) -> int:
        """Index chunks into both Qdrant (dense) and BM25 (sparse) stores."""
        self.vector_store.index_chunks(chunks)
        return self.bm25_index.index_chunks(chunks)

    @staticmethod
    def reciprocal_rank_fusion(
        ranked_lists: List[List[Dict[str, Any]]],
        k: int = 60,
    ) -> List[Dict[str, Any]]:
        """Fuse multiple ranked candidate lists using Reciprocal Rank Fusion (RRF)."""
        rrf_scores: Dict[str, float] = {}
        chunk_map: Dict[str, Dict[str, Any]] = {}

        for ranked_list in ranked_lists:
            for rank_idx, item in enumerate(ranked_list, start=1):
                cid = item["chunk_id"]
                rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (k + rank_idx))
                if cid not in chunk_map:
                    chunk_map[cid] = dict(item)

        fused_results: List[Dict[str, Any]] = []
        for cid, rrf_score in sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True):
            doc = chunk_map[cid]
            doc["rrf_score"] = rrf_score
            fused_results.append(doc)

        return fused_results

    def retrieve(
        self,
        query: str,
        top_k: int = 3,
        candidate_pool_size: int = 8,
        service_filter: Optional[str] = None,
        enable_query_rewrite: bool = True,
    ) -> List[Dict[str, Any]]:
        """Execute hybrid retrieval (Dense + BM25) and fuse via RRF."""
        effective_query = QueryRewriter.rewrite(query) if enable_query_rewrite else query

        dense_candidates = self.vector_store.search(
            query=effective_query,
            top_k=candidate_pool_size,
            service_filter=service_filter,
        )
        bm25_candidates = self.bm25_index.search(
            query=effective_query,
            top_k=candidate_pool_size,
            service_filter=service_filter,
        )

        fused = self.reciprocal_rank_fusion(
            [dense_candidates, bm25_candidates],
            k=self.rrf_k,
        )
        return fused[:top_k]