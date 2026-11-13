"""Format-specific extract()/mask() modules, one per file type.

Every module in this package exposes the same shape (from the original task
brief): `extract(file) -> str` and format-specific mask/unmask helpers built
on top of `model.masking` and `model.predict`. Keeping this consistent is
what lets Person A's PDF/DOCX/PPTX formats and Person B's Excel/CSV/TXT
formats merge cleanly regardless of internal differences.
"""
