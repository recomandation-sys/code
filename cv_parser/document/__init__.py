"""Source-independent document model shared by every downstream stage.

Nothing outside `cv_parser/ingestion/` should need to know whether a given
`Word` came from PyMuPDF's native text layer or from OCR.
"""
