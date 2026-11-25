from typing import List, Dict, Any, Optional, Callable
from app.rag.retrieval import HybridRunbookRetriever


class CrossEncoderReranker:
    """Stage-2 Cross-Encoder reranker scoring full (query, document) token interactions."""

    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        score_fn: Optional[Callable[[str, str], float]] = None,
    ):
        self.model_name = model_name
        self._score_fn = score_fn
        self._cross_encoder = None

    def score_pair(self, query: str, document_text: str) -> float:
        """Compute cross-attention relevance score for a single (query, document) pair."""
        if self._score_fn is not None:
            return float(self._score_fn(query, document_text))

        if self._cross_encoder is None:
            from sentence_transformers import CrossEncoder
            self._cross_encoder = CrossEncoder(self.model_name)

        scores = self._cross_encoder.predict([(query, document_text)])
        return float(scores[0])

    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: int = 3,
    ) -> List[Dict[str, Any]]:
        """Rescore Stage-1 candidate chunks and return top_k sorted by Cross-Encoder score."""
        if not candidates:
            return []

        rescored: List[Dict[str, Any]] = []
        for candidate in candidates:
            item = dict(candidate)
            item["rerank_score"] = self.score_pair(query, item["content"])
            rescored.append(item)

        rescored.sort(key=lambda x: x["rerank_score"], reverse=True)
        return rescored[:top_k]


class TwoStageRAGPipeline:
    """End-to-end 2-stage retrieval pipeline: Hybrid RRF (Stage 1) -> Cross-Encoder (Stage 2)."""

    def __init__(
        self,
        hybrid_retriever: HybridRunbookRetriever,
        reranker: CrossEncoderReranker,
    ):
        self.hybrid_retriever = hybrid_retriever
        self.reranker = reranker

    def retrieve_and_rerank(
        self,
        query: str,
        top_k: int = 3,
        stage1_candidates: int = 6,
        service_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch top candidates via Hybrid BM25+Qdrant RRF, then rerank via Cross-Encoder."""
        candidates = self.hybrid_retriever.retrieve(
            query=query,
            top_k=stage1_candidates,
            candidate_pool_size=stage1_candidates,
            service_filter=service_filter,
        )
        return self.reranker.rerank(query=query, candidates=candidates, top_k=top_k)