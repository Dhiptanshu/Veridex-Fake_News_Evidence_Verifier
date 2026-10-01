"""Importing this package registers every stage implementation."""
from app.stages import explanation, keywords, ner, preprocess, retrieval, verification  # noqa: F401
from app.stages.base import Stage, StageContext, get_stage, list_stages, register

__all__ = ["Stage", "StageContext", "get_stage", "list_stages", "register"]
