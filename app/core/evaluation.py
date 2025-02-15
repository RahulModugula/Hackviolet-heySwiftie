"""Evaluation framework - retrieval quality and response metrics."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class RetrievalMetrics:
    mrr: float  # Mean Reciprocal Rank
    recall_at_k: dict[int, float]  # recall@1, @3, @5
    precision_at_k: dict[int, float]
    ndcg: float


@dataclass
class ResponseMetrics:
    relevance: float  # 0-1, how relevant is the response
    coherence: float  # 0-1
    factual_consistency: float  # 0-1, does response align with retrieved context


@dataclass
class EvalSample:
    query: str
    expected_docs: list[str]  # ground truth document IDs
    expected_answer: str = ""
    retrieved_docs: list[str] = field(default_factory=list)
    response: str = ""


class Evaluator:
    """Evaluate RAG pipeline quality."""

    def __init__(self):
        self._samples: list[EvalSample] = []

    def add_sample(self, sample: EvalSample):
        self._samples.append(sample)

    def compute_retrieval_metrics(self, k_values: list[int] | None = None) -> RetrievalMetrics:
        k_values = k_values or [1, 3, 5]
        if not self._samples:
            return RetrievalMetrics(mrr=0, recall_at_k={}, precision_at_k={}, ndcg=0)

        reciprocal_ranks = []
        recall_scores = {k: [] for k in k_values}
        precision_scores = {k: [] for k in k_values}
        ndcg_scores = []

        for sample in self._samples:
            expected = set(sample.expected_docs)
            retrieved = sample.retrieved_docs

            # MRR
            rr = 0.0
            for i, doc in enumerate(retrieved):
                if doc in expected:
                    rr = 1.0 / (i + 1)
                    break
            reciprocal_ranks.append(rr)

            # Recall@k and Precision@k
            for k in k_values:
                top_k = set(retrieved[:k])
                hits = len(top_k & expected)
                recall_scores[k].append(hits / len(expected) if expected else 0)
                precision_scores[k].append(hits / k)

            # NDCG
            ndcg_scores.append(self._compute_ndcg(retrieved, expected))

        return RetrievalMetrics(
            mrr=float(np.mean(reciprocal_ranks)),
            recall_at_k={k: float(np.mean(v)) for k, v in recall_scores.items()},
            precision_at_k={k: float(np.mean(v)) for k, v in precision_scores.items()},
            ndcg=float(np.mean(ndcg_scores)),
        )

    def _compute_ndcg(self, retrieved: list[str], expected: set[str], k: int = 10) -> float:
        """Normalized Discounted Cumulative Gain."""
        dcg = 0.0
        for i, doc in enumerate(retrieved[:k]):
            rel = 1.0 if doc in expected else 0.0
            dcg += rel / np.log2(i + 2)

        # ideal DCG
        ideal_rels = sorted([1.0] * min(len(expected), k) + [0.0] * max(0, k - len(expected)), reverse=True)
        idcg = sum(r / np.log2(i + 2) for i, r in enumerate(ideal_rels))

        return dcg / idcg if idcg > 0 else 0.0

    def compute_response_metrics(self) -> ResponseMetrics:
        """Compute response quality metrics using simple heuristics."""
        if not self._samples:
            return ResponseMetrics(relevance=0, coherence=0, factual_consistency=0)

        relevance_scores = []
        coherence_scores = []
        consistency_scores = []

        for sample in self._samples:
            if not sample.response or not sample.expected_answer:
                continue

            # word overlap as rough relevance proxy
            resp_words = set(sample.response.lower().split())
            exp_words = set(sample.expected_answer.lower().split())
            overlap = len(resp_words & exp_words) / max(len(exp_words), 1)
            relevance_scores.append(min(overlap * 2, 1.0))

            # coherence: response length relative to query (not too short, not too long)
            ratio = len(sample.response) / max(len(sample.query), 1)
            coherence = min(ratio / 10, 1.0) if ratio > 0.5 else ratio
            coherence_scores.append(coherence)

            # factual consistency: check if retrieved context terms appear in response
            context_terms = set()
            for doc in sample.retrieved_docs[:3]:
                context_terms.update(doc.lower().split())
            if context_terms:
                match = len(resp_words & context_terms) / max(len(context_terms), 1)
                consistency_scores.append(min(match * 5, 1.0))

        return ResponseMetrics(
            relevance=float(np.mean(relevance_scores)) if relevance_scores else 0,
            coherence=float(np.mean(coherence_scores)) if coherence_scores else 0,
            factual_consistency=float(np.mean(consistency_scores)) if consistency_scores else 0,
        )

    def summary(self) -> dict:
        retrieval = self.compute_retrieval_metrics()
        response = self.compute_response_metrics()
        return {
            "n_samples": len(self._samples),
            "retrieval": {
                "mrr": round(retrieval.mrr, 4),
                "recall@3": round(retrieval.recall_at_k.get(3, 0), 4),
                "recall@5": round(retrieval.recall_at_k.get(5, 0), 4),
                "ndcg": round(retrieval.ndcg, 4),
            },
            "response": {
                "relevance": round(response.relevance, 4),
                "coherence": round(response.coherence, 4),
                "factual_consistency": round(response.factual_consistency, 4),
            },
        }
