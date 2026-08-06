"""
/// <summary>
/// Smart CSV file type detector (ArioNex Smart CSV Type Detector)
/// </summary>
/// <remarks>
/// This module reads the first few rows of a CSV file to determine whether it contains
/// question-and-answer (QnA) patterns or structured financial/accounting data.
///
/// Detection logic:
///   - If any column contains the word "question", "answer", or a Persian QnA keyword (e.g. "Sual", "Pasokh") → QnA
///   - Otherwise → Structured (financial/accounting)
///
/// This helper was extracted from the upload endpoint so it can be tested independently and reused.
/// </remarks>
"""

import logging
from typing import Literal

logger = logging.getLogger("arionex.csv_detector")

# Returnable CSV type
CsvType = Literal["qna", "structured"]


def detect_csv_type(file_path: str) -> CsvType:
    """
    /// <summary>
    /// Smart CSV type detection based on column headers (QnA vs. structured data)
    /// </summary>
    /// <param name="file_path">Full path of the CSV file uploaded to the server</param>
    /// <returns>"qna" if the file follows a Q&A pattern, "structured" otherwise</returns>
    /// <remarks>
    /// For performance, only the first 5 rows are read (nrows=5).
    /// Matching of both Persian and English column headers is supported.
    /// On any error while reading the CSV, "structured" is returned as a safe default.
    /// </remarks>
    """
    try:
        import pandas as pd

        # Read only the header for high performance
        df = pd.read_csv(file_path, nrows=5)
        cols_lower = [str(c).lower().strip() for c in df.columns]

        # Check QnA keywords in column names (Persian + English)
        is_qna = any(
            "question" in c
            or "answer" in c
            or c in ("سوال", "پرسش", "جواب", "پاسخ")
            for c in cols_lower
        )

        csv_type: CsvType = "qna" if is_qna else "structured"
        logger.info(f"CSV type detected for '{file_path}': '{csv_type}' (columns: {cols_lower[:5]})")
        return csv_type

    except Exception as e:
        logger.error(f"CSV type detection failed for '{file_path}': {str(e)}. Defaulting to 'structured'.")
        return "structured"
