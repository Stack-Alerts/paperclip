# Technology Stack
**Document**: 41_TECHNOLOGY_STACK.md
**Status**: 🟢 Complete
**Priority**: P0 - Critical

## Technology Selections

### UI Framework
**Choice**: PyQt6 or PySide6
**Rationale**: 
- Mature, stable
- Cross-platform
- Rich widget library
- Good performance

### Backend
**Language**: Python 3.10+
**Framework**: NautilusTrader
**Data**: Pandas, NumPy

### Data Storage
**Config**: JSON files
**Historical**: Parquet/CSV via LakeAPI
**Live**: WebSocket streams

### Testing
**Unit**: pytest
**Integration**: pytest + fixtures
**UI**: pytest-qt

### Code Quality
**Linting**: ruff
**Formatting**: black
**Type Checking**: mypy

### Deployment
**Packaging**: Poetry
**Distribution**: Standalone executable
**Updates**: Auto-update system

**Version**: 1.0
