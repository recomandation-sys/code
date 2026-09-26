"""Field extractors (Phase D+). Each module consumes the structural
`Document`/`Section` objects produced by `cv_parser.structure` and never
re-parses raw geometry itself — extraction here is about *reading* the
already-discovered structure, not discovering it again.
"""
