"""
ITM — Intelligent Trade Manager
================================
Foundation module for the BTC Trade Engine execution layer.

The ITM owns all live order submission, fill tracking, position management,
and risk gate enforcement. It delegates execution to NautilusTrader; the
domain layer here is intentionally framework-agnostic so it can be unit-tested
without a running Nautilus node.

Package layout
--------------
itm/
  domain/        — pure domain model (entities, events, state machines, config)
                   (Section A — complete)
  data/          — data management & synchronization layer (Section B)
                   Binance WebSocket stream, real-time bar construction,
                   gap detection + backfill, freshness gating, NT data adapter
  adapters/      — NautilusTrader type mappers and event converters (Section C+)
  engine/        — execution engine orchestration (Section G+)
"""

__version__ = "0.2.0"  # Section B added
