"""Pharmacogenomic knowledge base from official sources."""

from barekat_genomics.knowledge.models import VariantKnowledge
from barekat_genomics.knowledge.registry import KnowledgeRegistry, get_knowledge_registry

__all__ = ["VariantKnowledge", "KnowledgeRegistry", "get_knowledge_registry"]
