from pathlib import Path
from typing import List
from app.rag.embeddings import MarkdownRunbookChunker, QdrantRunbookStore

RUNBOOKS_DIR = Path(__file__).resolve().parents[2] / "data" / "runbooks"


def mock_domain_embedder(text: str) -> List[float]:
    """Deterministic 4D domain embedder for fast, offline unit tests.
    
    Dimensions:
      [0]: Database / RDS / connections / Aurora / PostgreSQL affinity
      [1]: Kubernetes / Pod / OOMKilled / exit_code 137 / CrashLoop affinity
      [2]: Network / VPC / NAT Gateway / packet drop / SNAT port affinity
      [3]: Remediation / failover / restart action affinity
    """
    t = text.lower()
    db_score = sum(k in t for k in ["rds", "aurora", "postgres", "connection", "pgbouncer", "database"])
    k8s_score = sum(k in t for k in ["kubernetes", "pod", "oomkilled", "137", "crashloop", "container"])
    vpc_score = sum(k in t for k in ["vpc", "nat", "packet", "port", "snat", "subnet"])
    rem_score = sum(k in t for k in ["remediation", "failover", "restart", "approval"])

    vec = [float(db_score) + 0.01, float(k8s_score) + 0.01, float(vpc_score) + 0.01, float(rem_score) + 0.01]
    norm = sum(x * x for x in vec) ** 0.5
    return [x / norm for x in vec]


def test_markdown_chunker_extracts_headers_and_breadcrumbs():
    """Verify structural Markdown splitting preserves runbook ID, service, and section titles."""
    rds_file = RUNBOOKS_DIR / "rds_failover_runbook.md"
    chunks = MarkdownRunbookChunker.chunk_markdown(
        rds_file.read_text(encoding="utf-8"),
        source_file=rds_file.name,
    )

    assert len(chunks) == 4
    assert all(c.runbook_id == "RB-DB-001" for c in chunks)
    assert all(c.service == "rds" for c in chunks)

    section_titles = [c.section_title for c in chunks]
    assert section_titles == [
        "Trigger Conditions",
        "Blast Radius",
        "Automated Diagnostic Steps",
        "Remediation Policy",
    ]
    assert "Runbook: RDS Aurora PostgreSQL Failover" in chunks[0].content


def test_chunk_directory_parses_all_runbooks():
    """Verify all three domain runbooks (RDS, K8s, VPC) are parsed from data/runbooks."""
    all_chunks = MarkdownRunbookChunker.chunk_directory(RUNBOOKS_DIR)
    assert len(all_chunks) == 12  # 3 runbooks * 4 sections each

    services = {c.service for c in all_chunks}
    assert services == {"rds", "kubernetes", "vpc"}


def test_qdrant_indexing_and_semantic_search():
    """Verify Qdrant indexes chunks and ranks matching domain runbooks #1."""
    chunks = MarkdownRunbookChunker.chunk_directory(RUNBOOKS_DIR)
    store = QdrantRunbookStore(
        collection_name="test_runbooks",
        embed_fn=mock_domain_embedder,
        vector_size=4,
    )

    indexed_count = store.index_chunks(chunks)
    assert indexed_count == 12

    # 1. Database saturation query -> should retrieve RB-DB-001
    db_results = store.search("Aurora database connections exhausted on postgres primary", top_k=2)
    assert len(db_results) == 2
    assert db_results[0]["runbook_id"] == "RB-DB-001"
    assert db_results[0]["service"] == "rds"

    # 2. Kubernetes crash query -> should retrieve RB-K8S-002
    k8s_results = store.search("Kubernetes pod container terminated with OOMKilled exit code 137", top_k=2)
    assert k8s_results[0]["runbook_id"] == "RB-K8S-002"
    assert k8s_results[0]["service"] == "kubernetes"

    # 3. VPC NAT Gateway query -> should retrieve RB-VPC-003
    vpc_results = store.search("VPC NAT Gateway dropping packets due to SNAT port exhaustion", top_k=2)
    assert vpc_results[0]["runbook_id"] == "RB-VPC-003"
    assert vpc_results[0]["service"] == "vpc"


def test_qdrant_metadata_service_filtering():
    """Verify payload filtering strictly restricts vector search to the requested service domain."""
    chunks = MarkdownRunbookChunker.chunk_directory(RUNBOOKS_DIR)
    store = QdrantRunbookStore(
        collection_name="test_filtered_runbooks",
        embed_fn=mock_domain_embedder,
        vector_size=4,
    )
    store.index_chunks(chunks)

    # Even with a database-leaning query, filtering by 'kubernetes' must ONLY return kubernetes chunks
    filtered_results = store.search(
        "Database connection error and container restart",
        top_k=5,
        service_filter="kubernetes",
    )
    assert len(filtered_results) == 4  # Only 4 kubernetes chunks exist in total
    assert all(r["service"] == "kubernetes" for r in filtered_results)
    assert all(r["runbook_id"] == "RB-K8S-002" for r in filtered_results)

