# Day 05: Advanced RAG Architecture — Hybrid Search & Reranking

**Phase:** Week 1 — Advanced LLM Engineering & Knowledge Intelligence  
**Focus:** Sparse BM25 + Dense Vector Search, Reciprocal Rank Fusion (RRF), Query Rewriting, and Cross-Encoder Reranking

---

## 1. Executive Summary & Why This Matters

Pure dense vector search (what we built on Day 4) has a well-known blind spot in infrastructure operations: **exact lexical identifiers**. When an SRE alert fires containing an exact error code like `exit_code: 137`, `ErrorPortAllocation`, or `FATAL: 53300`, a dense Bi-Encoder often averages those rare tokens into a generic "system error" vector. Conversely, pure keyword search (BM25) fails when an operator describes a symptom conceptually (*"containers keep dying from memory pressure"*) without using the exact token `OOMKilled`.

Production RAG engines solve this with a **Two-Stage Hybrid Retrieval & Reranking Pipeline**:
1. **Stage 1 (Candidate Generation — High Recall):** Run **Sparse BM25** (exact keyword/identifier match) and **Dense Qdrant Vector Search** (semantic match) in parallel, fusing their rankings via **Reciprocal Rank Fusion (RRF)**.
2. **Stage 2 (Cross-Encoder Reranking — High Precision):** Pass the top $N$ fused candidates through a **Cross-Encoder** that computes full token-by-token cross-attention between the query and each document chunk to produce the final top $K$ results.

---

## 2. Learning Objectives

By the end of today, you will understand and be able to:
1. **Implement Sparse BM25 Retrieval:** Use `rank_bm25.BM25Okapi` with technical token preservation (keeping error codes, underscores, and numbers intact).
2. **Master Reciprocal Rank Fusion (RRF):**
   $$\text{RRF\_Score}(d \in D) = \sum_{m \in \{\text{BM25}, \text{Dense}\}} \frac{1}{k + \text{rank}_m(d)} \quad (\text{typically } k = 60)$$
   Explain why rank-based fusion outperforms raw score normalization.
3. **Architect Cross-Encoder Reranking:** Understand the architectural difference between a **Bi-Encoder** (encodes query and document separately) and a **Cross-Encoder** (encodes `[CLS] Query [SEP] Document [SEP]` jointly with full self-attention).
4. **Implement Query Rewriting / Expansion:** Enrich cryptic monitoring alerts with domain synonyms before retrieval.

---

## 3. Technical Deep-Dive

### A. Bi-Encoder vs. Cross-Encoder Architecture

```
=== Stage 1: Bi-Encoder (Qdrant Vector Search) ===
[ Query ]    ──► [ Encoder ] ──► Vector U (384-d) ┐
                                                  ├──► Cosine(U, V) ──► Fast O(1) dot product!
[ Document ] ──► [ Encoder ] ──► Vector V (384-d) ┘    (Pre-computed at index time)
⚠️ Limitation: Query tokens and Document tokens NEVER attend to each other directly.
   All meaning is compressed into a single 384-float bottleneck.


=== Stage 2: Cross-Encoder (Reranker) ===
[ CLS + Query Tokens + SEP + Document Tokens + SEP ]
                        │
                        ▼
        [ Full Transformer Self-Attention ]
   (Every query token attends to every document token!)
                        │
                        ▼
           [ Relevance Score (0.0 to 1.0) ]
✅ Strength: Highest possible accuracy.
⚠️ Cost: Cannot pre-compute vectors! Must run N transformer forward passes at query time.
   Solution: Only run Cross-Encoder on the top 10–25 candidates from Stage 1.
```

### B. Why Reciprocal Rank Fusion (RRF) Beats Linear Score Combination
- **BM25 scores** are unbounded positive floats ($[0, \infty)$) that depend heavily on query length and corpus term rarity (IDF).
- **Cosine similarity scores** are bounded ($[-1, 1]$), often clustering tightly between $0.45$ and $0.85$.
- Adding $0.75 \text{ (Cosine)} + 18.4 \text{ (BM25)}$ allows BM25 outliers to completely swamp the semantic signal.
- **RRF** converts raw scores into **ordinal ranks** ($1, 2, 3, \dots$). A document ranked #1 in BM25 and #2 in Dense Search gets $\frac{1}{60+1} + \frac{1}{60+2} = 0.03252$, smoothly rewarding consensus across both retrieval paradigms without fragile min-max calibration.

---

## 4. Curated Learning Resources

### High-Impact YouTube Lectures
1. **James Briggs — "Hybrid Search & Reciprocal Rank Fusion (RRF) Explained"**
   - **URL:** https://www.youtube.com/watch?v=k_n_3u_qjU8
   - **Channel:** James Briggs
   - *Why watch:* Clear mathematical walkthrough and Python implementation of combining sparse BM25 with dense vector search.
2. **Nils Reimers (Creator of Sentence-Transformers) — "Dense Retrieval and Cross-Encoder Reranking"**
   - **URL:** https://www.youtube.com/watch?v=Fw3rP4b_6G4
   - **Channel:** Hugging Face / Nils Reimers
   - *Why watch:* The creator of `sentence-transformers` explains the information bottleneck of Bi-Encoders and why two-stage retrieval with Cross-Encoders is the gold standard.
3. **Qdrant Official — "Hybrid Search with Sparse and Dense Vectors"**
   - **URL:** https://www.youtube.com/watch?v=f7MR0v6K3W0
   - **Channel:** Qdrant
   - *Why watch:* Production patterns for fusing lexical and semantic search in real-world RAG pipelines.

### Official Documentation
- **Sentence-Transformers Cross-Encoder Docs:** https://www.sbert.net/docs/cross_encoder/usage/usage.html
- **Qdrant Hybrid Queries & RRF Guide:** https://qdrant.tech/documentation/concepts/hybrid-queries/
- **Original RRF Paper (Cormack et al., SIGIR):** *"Reciprocal Rank Fusion Outperforms Condorcet and Individual Rank Learning Methods"*

---

## 5. Hands-on Guided Exercise (Conceptual Prototype)

Here is how BM25 + Dense RRF fusion works in pure Python:

```python
import re
from rank_bm25 import BM25Okapi
from typing import List, Dict

def tokenize_technical(text: str) -> List[str]:
    """Preserve alphanumeric tokens, error codes, and underscores."""
    return re.findall(r"[a-z0-9_]+", text.lower())

def demo_bm25_and_rrf():
    corpus = [
        {"id": "chunk_1", "text": "PostgreSQL FATAL 53300 remaining connection slots reserved"},
        {"id": "chunk_2", "text": "Kubernetes pod OOMKilled container terminated exit_code 137"},
        {"id": "chunk_3", "text": "AWS VPC NAT Gateway ErrorPortAllocation packet drop"},
    ]
    tokenized_corpus = [tokenize_technical(doc["text"]) for doc in corpus]
    bm25 = BM25Okapi(tokenized_corpus)

    query = "container crashed with exit_code 137"
    scores = bm25.get_scores(tokenize_technical(query))
    bm25_ranked = [doc["id"] for _, doc in sorted(zip(scores, corpus), key=lambda x: x[0], reverse=True)]

    # Suppose dense retrieval ranked them:
    dense_ranked = ["chunk_2", "chunk_1", "chunk_3"]

    # Reciprocal Rank Fusion (k=60)
    k = 60
    rrf_scores: Dict[str, float] = {}
    for rank_list in [bm25_ranked, dense_ranked]:
        for rank_idx, doc_id in enumerate(rank_list, start=1):
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (1.0 / (k + rank_idx))

    print("BM25 Ranking:", bm25_ranked)
    print("RRF Fused Scores:", sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True))

if __name__ == "__main__":
    demo_bm25_and_rrf()
```

---

## 6. SentinelOps Core Implementation Plan (What We Will Code)

When we begin the coding phase, we will implement this step-by-step:
- **Step 1:** Build `app/rag/retrieval.py` implementing:
  - `BM25RunbookIndex`: Technical tokenizer + `BM25Okapi` sparse index with optional `service_filter`.
  - `QueryRewriter`: Expands raw telemetry alerts and error codes with technical synonyms.
  - `HybridRunbookRetriever`: Executes Dense Qdrant search + Sparse BM25 search and merges them via **Reciprocal Rank Fusion (RRF, $k=60$)**.
- **Step 2:** Build `app/rag/reranking.py` implementing `CrossEncoderReranker` (supporting both Hugging Face `CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")` and an injectable scoring function for deterministic unit tests).
- **Step 3:** Write automated unit tests in `tests/unit/test_hybrid_rag_and_reranking.py` verifying that exact error codes (`exit_code: 137`, `ErrorPortAllocation`), RRF consensus ranking, and Cross-Encoder rescoring work end-to-end.

---

## 7. Exit Criteria Checklist

- [ ] Understand why BM25 is essential alongside dense vectors for exact error codes and identifiers.
- [ ] Can write the Reciprocal Rank Fusion formula $\sum \frac{1}{k + \text{rank}_m(d)}$ from memory and explain why $k=60$ dampens outlier ranks.
- [ ] Understand why Cross-Encoders are used only for Stage-2 reranking rather than Stage-1 full-corpus search.
- [ ] Ready to implement `app/rag/retrieval.py` and `app/rag/reranking.py` step-by-step.

---

## 8. Senior AI Engineer Interview Prep

**Q1: Why not just use a Cross-Encoder to search the entire database of 100,000 runbook chunks directly since it is more accurate than a Bi-Encoder?**  
*Model Answer:*  
A Cross-Encoder cannot pre-compute document embeddings because it requires passing the concatenated `[CLS] Query [SEP] Document [SEP]` pair through all transformer layers at query time to compute cross-attention. Searching 100,000 chunks with a Cross-Encoder would require **100,000 transformer forward passes per user query**, taking minutes of GPU time (~30–60 seconds even on an A100). A Bi-Encoder pre-computes document vectors offline, reducing query-time search over 100,000 chunks to a 2-millisecond HNSW lookup, after which the Cross-Encoder only runs 10 to 20 forward passes on the top candidates (~30–50ms total).

**Q2: What role does the constant $k=60$ play in Reciprocal Rank Fusion $\frac{1}{k + \text{rank}}$?**  
*Model Answer:*  
Without $k$ (i.e. $k=0$), rank #1 receives a weight of $1.0$, rank #2 receives $0.5$, and rank #10 receives $0.1$. That means a single retriever placing an irrelevant outlier document at rank #1 ($1.0$) would outweigh two other retrievers that both placed a truly relevant document at rank #3 ($0.33 + 0.33 = 0.66$). Adding $k=60$ flattens the steep hyperbolic drop-off among top ranks, ensuring that **multi-retriever consensus** (appearing near the top in *both* BM25 and Dense Vector search) dominates over a single retriever's #1 spike.

