# Day 01: Transformer Architecture & LLM Internals

**Phase:** Week 1 — Advanced LLM Engineering & Knowledge Intelligence  
**Focus:** Foundations of Self-Attention, Tokenization, Embeddings, Context Window Dynamics, and the KV Cache

---

## 1. Executive Summary & Why This Matters

Senior AI engineers do not treat Large Language Models as black boxes. When designing autonomous agents or high-throughput RAG systems for SRE incident response, understanding model internals dictates every architecture decision: token budget calculation, streaming latency, context window degradation ("lost in the middle"), memory consumption during multi-turn agent loops (KV cache growth), and why temperature/sampling strategies trigger hallucinations.

Today, you will look beneath high-level SDKs (OpenAI/Anthropic/Bedrock) and study the core mathematical mechanics of autoregressive transformers using Hugging Face Transformers and PyTorch.

---

## 2. Learning Objectives

By the end of today, you will be able to:
1. Explain the scaled dot-product self-attention mechanism:
   $$\text{Attention}(Q, K, V) = \text{softmax}\left(\frac{QK^T}{\sqrt{d_k}}\right)V$$
2. Understand how Byte-Pair Encoding (BPE) and SentencePiece tokenizers tokenize code, numbers, and structured logs.
3. Quantify the memory footprint of the Key-Value (KV) cache during continuous generation.
4. Diagnose the root causes of hallucinations in LLMs (sampling randomness, attention dispersion, lack of calibration).
5. Extract attention weights from a Hugging Face model and visualize which input tokens drive specific outputs.

---

## 3. Technical Deep-Dive

### A. Scaled Dot-Product Self-Attention
Self-attention allows every token in an input sequence to dynamically weight its relationship to every other token.
- **Queries ($Q$):** What a token is looking for.
- **Keys ($K$):** What a token advertises about itself.
- **Values ($V$):** The contextual information passed forward.
- The scaling factor $\sqrt{d_k}$ prevents dot products from growing excessively large in high dimensions, which would push softmax gradients into vanishing regions.

### B. The KV Cache & Autoregressive Inference
During generation, each new token requires attention over all previous tokens. Without caching:
- Recomputing $K$ and $V$ for all past tokens scales with time complexity $O(N^2)$ per generated token.
- With the **KV Cache**, past keys and values are stored in GPU/RAM, reducing next-token generation complexity to $O(N)$ memory reads:
  $$\text{KV Cache Memory} = 2 \times 2 \times \text{Layers} \times \text{Heads} \times d_k \times \text{SeqLen} \times \text{Precision Bytes}$$

### C. Tokenization Traps in SRE & Incident Analysis
Standard LLM tokenizers (tiktoken, LLaMA tokenizer) are trained on web text. When parsing AWS ARNs, stack traces, IP addresses, or JSON payloads:
- An IP address like `192.168.1.1` may be split into 5-7 distinct tokens (`192`, `.`, `168`, `.`, `1`, `.`, `1`), inflating latency and degrading arithmetic reasoning.

---

## 4. Curated Learning Resources

### High-Impact YouTube Lectures
1. **Andrej Karpathy — "Let's build GPT: from scratch, in code, spelled out"**
   - URL: https://www.youtube.com/watch?v=kCc8FmEb1nY
   - *Why watch:* The gold standard 2-hour lecture walking through every matrix multiplication, multi-head attention block, and residual connection in PyTorch.
2. **3Blue1Brown — "Visualizing Attention and Transformers"**
   - URL: https://www.youtube.com/watch?v=eMlx5fFNoYc
   - *Why watch:* The most intuitive geometric and visual explanation of Query, Key, and Value vector transformations.
3. **Umar Jamil — "Attention Is All You Need — Paper Explanation"**
   - URL: https://www.youtube.com/watch?v=bCz4OMemCcA
   - *Why watch:* Line-by-line breakdown of the original Vaswani et al. transformer architecture and positional encoding.

### Official Documentation & Papers
- **Vaswani et al. (2017):** *Attention Is All You Need* (https://arxiv.org/abs/1706.03762)
- **Hugging Face Transformers Docs:** *LLM Inference & KV Cache Optimization* (https://huggingface.co/docs/transformers/main/en/kv_cache)

---

## 5. Hands-on Guided Exercise: Inspecting Tokenization & Attention

Run this Python script to inspect how a tokenizer chunks cloud error logs and how attention maps relate tokens:

```python
import numpy as np

def simulated_self_attention(sequence: list[str]):
    """Demonstrate self-attention calculation with synthetic Q, K, V vectors."""
    np.random.seed(42)
    seq_len = len(sequence)
    d_k = 4
    
    # Generate random representations
    X = np.random.randn(seq_len, d_k)
    W_q = np.random.randn(d_k, d_k)
    W_k = np.random.randn(d_k, d_k)
    W_v = np.random.randn(d_k, d_k)
    
    Q = X @ W_q
    K = X @ W_k
    V = X @ W_v
    
    # Scaled dot-product: (Q * K.T) / sqrt(d_k)
    scores = (Q @ K.T) / np.sqrt(d_k)
    attention_weights = np.exp(scores) / np.sum(np.exp(scores), axis=1, keepdims=True)
    context = attention_weights @ V
    
    print(f"Sequence Tokens: {sequence}")
    print(f"Attention Matrix Shape: {attention_weights.shape}")
    print("Self-Attention Weights for First Token:")
    for token, weight in zip(sequence, attention_weights[0]):
        print(f"  -> '{token}': {weight:.4f}")
    return context

if __name__ == "__main__":
    tokens = ["FATAL", "53300", "too_many_connections", "database", "orders"]
    simulated_self_attention(tokens)
```

---

## 6. SentinelOps Core Implementation Assignment

**File to create:** `sentinelops/app/rag/token_inspector.py`
Build a utility class that:
1. Calculates exact token usage for incident payloads.
2. Identifies fragmented tokens in system logs (e.g., detecting if error codes are split).
3. Estimates KV cache memory overhead for multi-turn incident investigations.

---

## 7. Verification & Testing

Create `tests/unit/test_token_inspector.py`:
```python
def test_kv_cache_memory_calculation():
    # Verify formula for 32 layers, 32 heads, dim 128, float16 (2 bytes)
    layers, heads, dim, seq_len, bytes_per_elem = 32, 32, 128, 2048, 2
    expected_bytes = 2 * 2 * layers * heads * dim * seq_len * bytes_per_elem
    assert expected_bytes == 2 * 2 * 32 * 32 * 128 * 2048 * 2
```

---

## 8. Exit Criteria Checklist

- [ ] Can write down the scaled dot-product attention equation from memory and explain why $\sqrt{d_k}$ is used.
- [ ] Can calculate KV cache RAM requirements given context window size and layer depth.
- [ ] Verified how error logs are tokenized without relying on magic assumptions.
- [ ] Documented findings in SentinelOps notes.

---

## 9. Senior AI Engineer Interview Prep

**Q1: Why does inference latency increase linearly or quadratically as context length expands, and how does PagedAttention / vLLM solve it?**  
*Model Answer:* In autoregressive generation, each new token must compute attention scores against all previous tokens in the sequence ($O(N)$ attention compute per step). Without caching, recomputing keys/values is $O(N^2)$. While KV caching brings computation per token to $O(N)$, standard PyTorch allocations require contiguous memory for the cache. Because sequence lengths are unpredictable, systems pre-allocate max context memory, leading to up to 60-80% memory fragmentation. PagedAttention divides the KV cache into fixed-size physical memory pages (like virtual memory in operating systems), eliminating internal fragmentation and enabling near 100% GPU memory utilization.

**Q2: What is the "Lost in the Middle" phenomenon, and how does it impact RAG systems with long context windows?**  
*Model Answer:* Empirical research (Liu et al., 2023) demonstrates that transformer attention mechanisms disproportionately attend to information placed at the very beginning and very end of the input prompt. When extensive context (e.g. 20 retrieved runbooks) is packed into a 128k context window, relevant facts placed in the middle 60% suffer up to a 50% drop in retrieval accuracy. In SentinelOps, we counter this by limiting retrieved chunks to top-3 to top-5 reranked passages and placing crucial incident symptoms adjacent to the generation instructions.
