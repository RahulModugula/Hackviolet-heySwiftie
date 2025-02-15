"""Evaluation routes."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/eval", tags=["evaluation"])

_evaluator = None


def get_evaluator():
    global _evaluator
    if _evaluator is None:
        from app.core.evaluation import Evaluator
        _evaluator = Evaluator()
    return _evaluator


class EvalSampleRequest(BaseModel):
    query: str
    expected_docs: list[str]
    expected_answer: str = ""


@router.post("/sample")
async def add_sample(req: EvalSampleRequest):
    from app.core.evaluation import EvalSample
    from app.dependencies import rag_pipeline
    # run retrieval
    docs = rag_pipeline.retrieve(req.query)
    retrieved_ids = [d.text[:50] for d in docs]

    sample = EvalSample(
        query=req.query,
        expected_docs=req.expected_docs,
        expected_answer=req.expected_answer,
        retrieved_docs=retrieved_ids,
    )
    get_evaluator().add_sample(sample)
    return {"status": "ok", "retrieved": retrieved_ids}


@router.get("/metrics")
async def get_metrics():
    return get_evaluator().summary()
