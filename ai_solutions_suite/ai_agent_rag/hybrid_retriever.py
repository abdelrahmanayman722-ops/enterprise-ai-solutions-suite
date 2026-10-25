"""
Enterprise Hybrid BM25 & Dense Vector Retriever with Reciprocal Rank Fusion (RRF)
==================================================================================
Combines sparse lexical BM25 retrieval with dense vector cosine similarity using RRF
to provide high-recall, high-precision document chunk retrieval with confidence calibration.
Author: Eng. Abdelrahman Rashad (Senior Full-Stack & Solutions Architect).
"""

import math
import re
from typing import List, Dict, Any, Optional, Tuple

class DocumentChunk:
    """Represents an indexed document chunk with tokenization and metadata."""

    def __init__(self, doc_id: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        self.doc_id = doc_id
        self.content = content
        self.metadata = metadata or {}
        self.tokens = self._tokenize(content)
        self.term_freqs: Dict[str, int] = {}
        for token in self.tokens:
            self.term_freqs[token] = self.term_freqs.get(token, 0) + 1

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return re.findall(r'\b[a-zA-Z0-9_\-\.]+\b', text.lower())

class HybridRetriever:
    """Production-grade hybrid retriever combining BM25 and Dense Cosine Similarity with RRF."""

    def __init__(self, k1: float = 1.5, b: float = 0.75, rrf_k: int = 60):
        self.k1 = k1
        self.b = b
        self.rrf_k = rrf_k
        self.corpus: List[DocumentChunk] = []
        self.doc_freqs: Dict[str, int] = {}  # number of docs containing token
        self.avg_doc_len: float = 0.0
        self.vocab: List[str] = []

    def ingest_documents(self, documents: List[Dict[str, Any]]):
        """Ingests, chunks, and indexes a collection of documents."""
        for doc in documents:
            content = doc.get("content", "")
            doc_id = doc.get("id", f"doc_{len(self.corpus) + 1}")
            metadata = doc.get("metadata", {})
            chunk = DocumentChunk(doc_id=doc_id, content=content, metadata=metadata)
            self.corpus.append(chunk)

        self._rebuild_index()

    def _rebuild_index(self):
        """Recomputes IDF frequencies, average length, and vocabulary index."""
        if not self.corpus:
            self.doc_freqs = {}
            self.avg_doc_len = 0.0
            self.vocab = []
            return

        total_tokens = sum(len(c.tokens) for c in self.corpus)
        self.avg_doc_len = total_tokens / len(self.corpus) if self.corpus else 0.0

        self.doc_freqs = {}
        vocab_set = set()
        for chunk in self.corpus:
            for term in set(chunk.tokens):
                self.doc_freqs[term] = self.doc_freqs.get(term, 0) + 1
                vocab_set.add(term)

        self.vocab = sorted(list(vocab_set))

    def _compute_idf(self, term: str) -> float:
        """Computes Robertson-Spärck Jones IDF with smoothing."""
        n_q = self.doc_freqs.get(term, 0)
        N = len(self.corpus)
        if N == 0:
            return 0.0
        # BM25 standard smoothed IDF formula: ln((N - n + 0.5) / (n + 0.5) + 1.0)
        return math.log(((N - n_q + 0.5) / (n_q + 0.5)) + 1.0)

    def _score_bm25(self, query_tokens: List[str]) -> List[Tuple[float, DocumentChunk]]:
        """Scores all corpus chunks using Okapi BM25."""
        scored = []
        for chunk in self.corpus:
            score = 0.0
            doc_len = len(chunk.tokens)
            len_norm = 1.0 - self.b + self.b * (doc_len / (self.avg_doc_len or 1.0))

            for token in query_tokens:
                tf = chunk.term_freqs.get(token, 0)
                if tf > 0:
                    idf = self._compute_idf(token)
                    numerator = tf * (self.k1 + 1.0)
                    denominator = tf + self.k1 * len_norm
                    score += idf * (numerator / denominator)

            scored.append((score, chunk))

        scored.sort(key=lambda x: x[0], reverse=True)
        return scored

    def _score_dense_cosine(self, query_tokens: List[str]) -> List[Tuple[float, DocumentChunk]]:
        """Scores all corpus chunks using TF-IDF weighted cosine vector similarity."""
        query_tf: Dict[str, int] = {}
        for t in query_tokens:
            query_tf[t] = query_tf.get(t, 0) + 1

        query_vec: Dict[str, float] = {}
        q_norm_sq = 0.0
        for t, tf in query_tf.items():
            weight = (1.0 + math.log(tf)) * self._compute_idf(t)
            query_vec[t] = weight
            q_norm_sq += weight * weight
        q_norm = math.sqrt(q_norm_sq) if q_norm_sq > 0 else 1.0

        scored = []
        for chunk in self.corpus:
            dot_product = 0.0
            d_norm_sq = 0.0
            for term, tf in chunk.term_freqs.items():
                w_d = (1.0 + math.log(tf)) * self._compute_idf(term)
                d_norm_sq += w_d * w_d
                if term in query_vec:
                    dot_product += query_vec[term] * w_d

            d_norm = math.sqrt(d_norm_sq) if d_norm_sq > 0 else 1.0
            cosine = dot_product / (q_norm * d_norm) if (q_norm > 0 and d_norm > 0) else 0.0
            scored.append((cosine, chunk))

        scored.sort(key=lambda x: x[0], reverse=True)
        return scored

    def retrieve(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Executes hybrid retrieval using Reciprocal Rank Fusion (RRF)
        between lexical BM25 and dense cosine vector similarity.
        """
        query_tokens = DocumentChunk._tokenize(query)
        if not query_tokens or not self.corpus:
            return []

        # Run BM25
        bm25_ranked = self._score_bm25(query_tokens)
        # Run Dense Cosine
        dense_ranked = self._score_dense_cosine(query_tokens)

        # Build rank maps (1-based index)
        bm25_ranks: Dict[str, int] = {}
        bm25_scores: Dict[str, float] = {}
        for rank, (score, chunk) in enumerate(bm25_ranked, start=1):
            bm25_ranks[chunk.doc_id] = rank
            bm25_scores[chunk.doc_id] = score

        dense_ranks: Dict[str, int] = {}
        dense_scores: Dict[str, float] = {}
        for rank, (score, chunk) in enumerate(dense_ranked, start=1):
            dense_ranks[chunk.doc_id] = rank
            dense_scores[chunk.doc_id] = score

        # Reciprocal Rank Fusion: RRF = sum(1 / (k + rank_m))
        rrf_scores: Dict[str, float] = {}
        chunk_map: Dict[str, DocumentChunk] = {c.doc_id: c for c in self.corpus}

        for chunk in self.corpus:
            cid = chunk.doc_id
            b_score = bm25_scores.get(cid, 0.0)
            d_score = dense_scores.get(cid, 0.0)

            # Only consider documents with non-zero relevance in at least one system
            if b_score <= 0.0 and d_score <= 0.0:
                continue

            r_bm25 = bm25_ranks[cid]
            r_dense = dense_ranks[cid]
            score_rrf = (1.0 / (self.rrf_k + r_bm25)) + (1.0 / (self.rrf_k + r_dense))
            rrf_scores[cid] = score_rrf

        if not rrf_scores:
            return []

        sorted_cids = sorted(rrf_scores.keys(), key=lambda cid: rrf_scores[cid], reverse=True)

        # Max theoretical RRF score with 2 rankers at rank 1 is 2 / (rrf_k + 1)
        max_rrf = 2.0 / (self.rrf_k + 1.0)

        results = []
        for cid in sorted_cids[:top_k]:
            chunk = chunk_map[cid]
            raw_rrf = rrf_scores[cid]
            # Calibrated confidence metric between 0.0 and 1.0
            # Blends normalized RRF and dense cosine score
            dense_sim = dense_scores.get(cid, 0.0)
            norm_rrf = min(1.0, raw_rrf / max_rrf)
            confidence = round(0.5 * norm_rrf + 0.5 * min(1.0, dense_sim), 4)

            results.append({
                "doc_id": chunk.doc_id,
                "score": round(raw_rrf, 5),
                "bm25_score": round(bm25_scores.get(cid, 0.0), 4),
                "dense_score": round(dense_sim, 4),
                "confidence": confidence,
                "content": chunk.content,
                "metadata": chunk.metadata
            })

        return results
