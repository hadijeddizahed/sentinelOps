from pathlib import Path
from typing import List
from app.rag.embeddings import MarkdownRunbookChunker, QdrantRunbookStore
from app.rag.retrieval import QueryRewriter, BM25RunbookIndex, HybridRunbookRetriever
from app.rag.reranking import CrossEncoderReranker, TwoStageRAGPipeline

RUNBOOKS_DIR = Path(__file__).resolve().parents[2] / "data" / "runbooks"


def mock_domain_embedder(text: str) -> List[float]:
    """Deterministic 4D domain embedder for offline unit tests."""
    t = text.lower()
    db_score = sum(k in t for k in ["rds", "aurora", "postgres", "connection", "pgbouncer", "database"])
    k8s_score = sum(k in t for k in ["kubernetes", "pod", "oomkilled", "137", "crashloop", "container"])
    vpc_score = sum(k in t for k in ["vpc", "nat", "packet", "port", "snat", "subnet"])
    rem_score = sum(k in t for k in ["remediation", "failover", "restart", "approval"])

    vec = [float(db_score) + 0.01, float(k8s_score) + 0.01, float(vpc_score) + 0.01, float(rem_score) + 0.01]
    norm = sum(x * x for x in vec) ** 0.5
    return [x / norm for x in vec]


def mock_cross_encoder_scorer(query: str, doc_text: str) -> float:
    """Simulated Cross-Encoder interaction scorer that rewards exact token overlap + section intent."""
    q_tokens = set(BM25RunbookIndex.tokenize(query))
    d_tokens = set(BM25RunbookIndex.tokenize(doc_text))
    overlap = len(q_tokens & d_tokens)
    bonus = 5.0 if ("remediation" in query.lower() and "section: remediation policy" in doc_text.lower()) else 0.0
    return float(overlap) + bonus


def test_query_rewriter_expands_cryptic_error_codes():
    """Verify QueryRewriter expands error numbers like 137 and 53300 with domain context."""
    rewritten_k8s = QueryRewriter.rewrite("Pod payment-worker died with 137")
    assert "OOMKilled" in rewritten_k8s
    assert "memory limit" in rewritten_k8s

    rewritten_db = QueryRewriter.rewrite("Postgres error 53300 on primary")
    assert "remaining connection slots" in rewritten_db


def test_bm25_exact_identifier_retrieval():
    """Verify BM25 sparse search finds exact technical error identifiers like ErrorPortAllocation."""
    chunks = MarkdownRunbookChunker.chunk_directory(RUNBOOKS_DIR)
    bm25 = BM25RunbookIndex(chunks)

    results = bm25.search("ErrorPortAllocation PacketsDropCount", top_k=2)
    assert len(results) == 2
    assert results[0]["runbook_id"] == "RB-VPC-003"
    assert results[0]["section_title"] == "Trigger Conditions"
    assert results[0]["bm25_score"] > 0.0


def test_reciprocal_rank_fusion_rewards_consensus():
    """Verify RRF(k=60) ranks a consensus document (#2 in both lists) above a single-list #1 outlier."""
    dense_list = [
        {"chunk_id": "outlier_dense", "title": "Outlier Dense #1"},
        {"chunk_id": "consensus_doc", "title": "Consensus #2 in both"},
    ]
    bm25_list = [
        {"chunk_id": "outlier_bm25", "title": "Outlier BM25 #1"},
        {"chunk_id": "consensus_doc", "title": "Consensus #2 in both"},
    ]

    fused = HybridRunbookRetriever.reciprocal_rank_fusion([dense_list, bm25_list], k=60)
    assert fused[0]["chunk_id"] == "consensus_doc"
    # Consensus score = 1/62 + 1/62 = 0.032258 > single #1 score (1/61 = 0.016393)
    assert fused[0]["rrf_score"] > fused[1]["rrf_score"]


def test_two_stage_hybrid_and_cross_encoder_pipeline():
    """Verify end-to-end Stage 1 (Hybrid RRF) + Stage 2 (Cross-Encoder Reranker) pipeline."""
    chunks = MarkdownRunbookChunker.chunk_directory(RUNBOOKS_DIR)
    vector_store = QdrantRunbookStore(
        collection_name="test_hybrid_runbooks",
        embed_fn=mock_domain_embedder,
        vector_size=4,
    )
    hybrid_retriever = HybridRunbookRetriever(vector_store=vector_store)
    hybrid_retriever.index_chunks(chunks)

    reranker = CrossEncoderReranker(score_fn=mock_cross_encoder_scorer)
    pipeline = TwoStageRAGPipeline(hybrid_retriever=hybrid_retriever, reranker=reranker)

    results = pipeline.retrieve_and_rerank(
        query="What is the remediation policy for exit_code 137 pod crashloop?",
        top_k=2,
        stage1_candidates=6,
    )

    assert len(results) == 2
    assert results[0]["runbook_id"] == "RB-K8S-002"
    assert results[0]["section_title"] == "Remediation Policy"
    assert "rerank_score" in results[0]
    assert "rrf_score" in results[0]

