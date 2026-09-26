"""Quality/review (Phase G): parse-quality scoring used both to pick the
best of several candidate parses (section 48's adaptive retry) and to
report the final `parse_quality`/`review_items` diagnostics (sections
47, 51). Nothing here re-derives fields — it only reads what earlier
phases already produced and reasons about how trustworthy the result is.
"""
