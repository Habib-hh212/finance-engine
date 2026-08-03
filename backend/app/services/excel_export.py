"""Turns report rows into a downloadable .xlsx response -- shared by every
"Download Excel" button across the reports so each one isn't hand-rolling
its own ExcelWriter plumbing.
"""
import io

import pandas as pd
from fastapi import Response

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def sheets_to_xlsx_response(sheets: dict[str, list[dict]], filename: str) -> Response:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for sheet_name, rows in sheets.items():
            pd.DataFrame(rows).to_excel(writer, sheet_name=sheet_name[:31], index=False)
    buffer.seek(0)
    return Response(
        content=buffer.getvalue(),
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
