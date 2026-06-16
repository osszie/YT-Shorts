"""LLM provider backends.

The project is model-agnostic (STRATEGY.md §8 "any model"): a small Provider
interface with concrete backends (Gemini, local Ollama, ...). `pipeline/llm.py`
selects one via LLM_PROVIDER and wraps it with pacing + retry/backoff, so every
stage keeps calling the same `llm.generate_*` API regardless of backend.
"""
