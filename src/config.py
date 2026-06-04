import polars as pl
import re

pl.Config(
     tbl_formatting='UTF8_BORDERS_ONLY',
     tbl_cell_numeric_alignment='RIGHT',
     set_tbl_column_data_type_inline=False,
     set_tbl_hide_dtype_separator=True,
     set_tbl_rows=6,
     set_tbl_width_chars=250,
     thousands_separator=',',
     decimal_separator='.',
     float_precision=2,
     fmt_str_lengths=5,
     set_tbl_cols=12,
     set_trim_decimal_zeros=True,
)


def latex_table_to_md(latex_str: str) -> str:
    """
    Naively converts a simple LaTeX tabular environment to a Markdown table.
    """
    # Extract rows
    rows = re.findall(r"(.*?)\\\\\s*?(?:\\hline)?", latex_str)
    
    md_rows = []
    for row in rows:
        # Remove \hline, \centering, \begin/end tags if captured
        if "begin{tabular}" in row or "end{tabular}" in row:
            continue
        
        # Split by & and strip whitespace/latex formatting
        cells = [cell.strip() for cell in row.split("&")]
        md_rows.append("| " + " | ".join(cells) + " |")

    if not md_rows:
        return ""

    # Create the header separator (assuming first row is header)
    num_cols = len(md_rows[0].split("|")) - 2
    separator = "| " + " | ".join(["---"] * num_cols) + " |"
    
    md_rows.insert(1, separator)
    
    return "\n".join(md_rows)

# Usage inside your script:
# latex_source = "..."
# md_table = latex_table_to_md(latex_source)
# fd.write(md_table)
