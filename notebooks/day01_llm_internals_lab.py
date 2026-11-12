"""
SentinelOps - Day 01 Hands-On Lab: LLM Internals & Token Mechanics
===================================================================

This lab is designed for Day 1 of the SentinelOps curriculum.
It builds foundational intuition without needing complex cloud setups or heavyweight GPU training:

1. Experiment 1: Tokenization Traps in SRE & Incident Logs
2. Experiment 2: Scaled Dot-Product Self-Attention in Pure NumPy
3. Experiment 3: KV Cache Memory & Agent Turn-Budget Calculator

Run this file with:
    python3 notebooks/day01_llm_internals_lab.py
"""

import math
from typing import List, Dict, Tuple

try:
    import numpy as np
except ImportError:
    np = None


# ==============================================================================
# EXPERIMENT 1: Tokenization Dynamics on Infrastructure & SRE Data
# ==============================================================================
def experiment_1_tokenization():
    print("\n" + "=" * 70)
    print("EXPERIMENT 1: Tokenization Behavior on Cloud Logs & DevOps Data")
    print("=" * 70)

    # Check if tiktoken or transformers is available
    tokenizer_name = None
    tokenize_func = None

    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")  # GPT-4 / ChatGPT tokenizer
        tokenizer_name = "tiktoken (cl100k_base)"
        tokenize_func = lambda text: [enc.decode([t]) for t in enc.encode(text)]
    except ImportError:
        try:
            from transformers import AutoTokenizer
            hf_tok = AutoTokenizer.from_pretrained("gpt2")
            tokenizer_name = "Hugging Face GPT-2"
            tokenize_func = lambda text: [hf_tok.decode([t]) for t in hf_tok.encode(text)]
        except Exception:
            tokenizer_name = "Built-in Rule-Based BPE Simulation (No external deps required)"
            # Simulated BPE-like splitter for offline demonstration
            import re
            def simulated_bpe(text):
                # Splits punctuation, numbers, and word sub-chunks
                tokens = re.findall(r"[A-Za-z]+|\d+|[:/_\-.,!?]|[\s]+", text)
                return tokens
            tokenize_func = simulated_bpe

    print(f"Active Tokenizer Engine: {tokenizer_name}\n")

    test_samples = [
        ("Plain English Query", "Database connection pool is saturated and rejecting requests."),
        ("PostgreSQL Error Code", "FATAL: 53300: remaining connection slots are reserved"),
        ("AWS Resource ARN", "arn:aws:rds:us-east-1:123456789012:db:prod-orders-cluster"),
        ("IPv4 Address & Port", "10.128.4.15:5432"),
        ("K8s Exit Signal", "pod/payment-worker terminated with exit_code:137 (OOMKilled)")
    ]

    print(f"{'Input Category':<25} | {'Chars':<6} | {'Tokens':<6} | {'Inflation':<10} | {'Tokens Sample'}")
    print("-" * 80)

    for category, text in test_samples:
        tokens = tokenize_func(text)
        char_count = len(text)
        token_count = len(tokens)
        ratio = f"{token_count / char_count:.2f} tok/char"
        sample_repr = str(tokens[:6]) + ("..." if len(tokens) > 6 else "")
        print(f"{category:<25} | {char_count:<6} | {token_count:<6} | {ratio:<10} | {sample_repr}")

    print("\n💡 Key Architectural Takeaway for SentinelOps:")
    print("Notice how structured identifiers (ARNs, IP addresses, error codes) split into")
    print("many tiny tokens compared to natural language. In multi-agent investigations, passing")
    print("raw, uncompressed log dumps quickly burns context window budget and degrades arithmetic reasoning.")


# ==============================================================================
# EXPERIMENT 2: Scaled Dot-Product Self-Attention from Scratch
# ==============================================================================
def experiment_2_self_attention():
    print('\n' + '=' * 70)
    print('EXPERIMENT 2: Scaled Dot-Product Attention (Pure Math)')
    print('=' * 70)
    print('Formula: Attention(Q, K, V) = softmax((Q * K^T) / sqrt(d_k)) * V\n')

    tokens = ["FATAL", "53300", "connection_limit", "rds_primary", "orders_db"]
    seq_len = len(tokens)
    d_k = 4

    if np is not None:
        np.random.seed(42)
        X = np.random.randn(seq_len, 8)
        W_q = np.random.randn(8, d_k) * 0.5
        W_k = np.random.randn(8, d_k) * 0.5
        W_v = np.random.randn(8, d_k) * 0.5
        Q, K, V = X @ W_q, X @ W_k, X @ W_v
        scores = (Q @ K.T) / math.sqrt(d_k)
        exp_scores = np.exp(scores - np.max(scores, axis=1, keepdims=True))
        attention_weights = exp_scores / np.sum(exp_scores, axis=1, keepdims=True)
    else:
        # Pure Python fallback matrix math (zero external dependencies)
        import random
        random.seed(42)
        # Create deterministic pseudo Q and K vectors
        Q = [[random.uniform(-1, 1) for _ in range(d_k)] for _ in range(seq_len)]
        K = [[random.uniform(-1, 1) for _ in range(d_k)] for _ in range(seq_len)]
        
        # Q @ K.T / sqrt(d_k)
        scores = []
        for i in range(seq_len):
            row = []
            for j in range(seq_len):
                dot = sum(Q[i][dim] * K[j][dim] for dim in range(d_k))
                row.append(dot / math.sqrt(d_k))
            scores.append(row)
            
        # Softmax along row
        attention_weights = []
        for row in scores:
            max_val = max(row)
            exp_row = [math.exp(val - max_val) for val in row]
            sum_exp = sum(exp_row)
            attention_weights.append([v / sum_exp for v in exp_row])

    print("Attention Weights Heatmap Matrix (Rows = Token attending to Columns):")
    header = "          " + "".join([f"{tok:>16}" for tok in tokens])
    print(header)
    print(" " * 10 + "-" * (16 * seq_len))

    for i, row_tok in enumerate(tokens):
        row_str = f"{row_tok:<10}"
        for j in range(seq_len):
            weight = attention_weights[i][j] if isinstance(attention_weights, list) else attention_weights[i, j]
            row_str += f"{weight:16.3f}"
        print(row_str)


# ==============================================================================
def experiment_3_kv_cache_calculator():
    print("\n" + "=" * 70)
    print("EXPERIMENT 3: KV Cache Memory & Multi-Turn Investigation Sizing")
    print("=" * 70)

    # Representative Model Specs: LLaMA-3-8B / Mistral-7B Class
    num_layers = 32
    num_kv_heads = 8         # Grouped-Query Attention (GQA)
    head_dim = 128
    precision_bytes = 2      # float16 or bfloat16 = 2 bytes per element

    print(f"Model Architecture Assumed:")
    print(f"  * Layers: {num_layers}")
    print(f"  * KV Heads (GQA): {num_kv_heads}")
    print(f"  * Head Dimension (d_k): {head_dim}")
    print(f"  * Precision: 16-bit ({precision_bytes} bytes/element)\n")

    # Formula for KV Cache memory per token:
    # 2 (Key + Value) * num_layers * num_kv_heads * head_dim * precision_bytes
    bytes_per_token = 2 * num_layers * num_kv_heads * head_dim * precision_bytes

    print(f"Formula: 2 * Layers * KV_Heads * Head_Dim * Precision")
    print(f"-> KV Cache per single context token: {bytes_per_token:,} bytes ({bytes_per_token / 1024:.2f} KB)\n")

    investigation_turns = [
        ("Turn 1: Ingest Initial Alert", 500),
        ("Turn 3: Runbook Retrieval Added", 2500),
        ("Turn 5: Database Specialist Logs Added", 6000),
        ("Turn 7: Network Specialist Traces Added", 12000),
        ("Turn 10: Full Multi-Agent Synthesis Context", 25000),
        ("Peak Incident Context Window", 64000),
    ]

    print(f"{'Investigation Phase':<45} | {'Tokens':<8} | {'KV Cache RAM (MB)':<18}")
    print("-" * 75)

    for phase, tokens in investigation_turns:
        mem_mb = (tokens * bytes_per_token) / (1024 * 1024)
        print(f"{phase:<45} | {tokens:<8} | {mem_mb:10.2f} MB")

    print("\n💡 Key Architectural Takeaway for SentinelOps:")
    print("In a production multi-agent system serving 50 concurrent incident investigations,")
    print("if each agent session reaches 25,000 tokens, the KV cache alone consumes ~6.25 GB of VRAM.")
    print("This is why production architectures prune old tool outputs, summarize turns,")
    print("and use scoped specialist agents rather than one giant unbounded prompt.")


# ==============================================================================
# MAIN ENTRYPOINT
# ==============================================================================
if __name__ == "__main__":
    print("\n" + "#" * 70)
    print("   SENTINELOPS — DAY 01: LLM INTERNALS & ATTENTION LAB")
    print("#" * 70)
    experiment_1_tokenization()
    experiment_2_self_attention()
    experiment_3_kv_cache_calculator()
    print("\n" + "=" * 70)
    print("✅ Day 01 Lab Execution Complete.")
    print("=" * 70 + "\n")
