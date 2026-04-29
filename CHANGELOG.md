# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- Staged LLM extraction pipeline (1a → 1b → 2)
- Hierarchical method extraction with `contains` relations
- Problem taxonomy with `is_subtask_of` relations
- Entity resolution with acronym matching and Jaccard deduplication
- Recursive taxonomy builder with LLM summarization
- Support for multiple LLM providers (Anthropic/Kimi, OpenAI)

## [2026-04-29]

### Added
- Professional README with badges and architecture diagram
- MIT License
- CONTRIBUTING.md with development setup
- examples/basic_usage.py minimal working example
- GitHub issue templates (bug report, feature request)
- Distribution build script (`build_distribution.sh`)
- GitHub repository published

### Fixed
- Proxy environment variable clearing in Cognee `__init__.py`
- Entity deduplication preventing acronym/fullname duplicates
- Empty node name prevention in database
- Relation name resolution after entity normalization

### Known Issues
- Training objectives (DPO Loss, Hybrid Prefix) not fully extracted
- Multi-paper taxonomy intermediate layers need validation
