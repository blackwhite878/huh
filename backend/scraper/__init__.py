"""
Mudah.my scraper subpackage.

Modules:
- types_quota: per-state property-type quota & MY regions
- storage: long-term CSV + temp JSON store
- mudah_scraper: lean httpx + BS4 with Playwright fallback
- seeder: ensures longterm dataset coverage (skip-if-already)
- ranking_agent: LLM-weighted math scoring → top10
- pipeline: high-level entry called by search_pipeline
"""
