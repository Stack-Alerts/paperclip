"""
Blast Radius — Touch Index query, report generation, and event-driven posting.

Entry points
------------
- blast_radius.query      : query Touch Index tables directly
- blast_radius.generator  : generate + post a Blast Radius Report for a Paperclip issue
- blast_radius.worker     : polling worker that watches for fix→in_review transitions
- blast_radius.api_server : simple HTTP server for GET /api/blast-radius
"""
