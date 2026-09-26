"""Layout discovery: regions, columns, reading order (sections 15-16).

Everything here operates purely on block/line geometry that is already
page-relative — no visual model, no fixed coordinates, no assumed column
count. `reading_order.assign_reading_order` is the public entry point.
"""
