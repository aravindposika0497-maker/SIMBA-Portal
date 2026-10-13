"""Server-side masking backstop for sample previews.

This is a safety net, not a governance control. Sample tables should be
Unity Catalog views that already mask or omit sensitive columns.
"""


def _is_sensitive(column, patterns):
    name = column.lower()
    return any(pattern in name for pattern in patterns)


def _mask_value(value):
    if value is None:
        return None
    text = str(value)
    if len(text) <= 2:
        return "***"
    return f"{text[:2]}***"


def mask_rows(rows, patterns):
    if not rows:
        return [], []
    sensitive = [c for c in rows[0].keys() if _is_sensitive(c, patterns)]
    masked = []
    for row in rows:
        out = dict(row)
        for column in sensitive:
            out[column] = _mask_value(out[column])
        masked.append(out)
    return masked, sensitive
