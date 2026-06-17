"""PDF report generation for the e2e endpoint test run (test_output.pdf)."""

from __future__ import annotations

import json

from fpdf import FPDF

from e2e.recorder import Recorder, StepResult

_GREEN = (39, 174, 96)
_RED = (231, 76, 60)
_DARK = (44, 62, 80)
_GREY = (127, 140, 141)
_LIGHT_ROW = (245, 247, 249)
_HEADER_BG = (52, 73, 94)
_WHITE = (255, 255, 255)


def _txt(value) -> str:
    """Coerce a value to latin-1-safe text for the PDF core fonts."""
    return str(value).encode("latin-1", "replace").decode("latin-1")


class _ReportPDF(FPDF):
    """A4 portrait report with a repeating header band and page footer."""

    def __init__(self) -> None:
        """Configure page geometry and auto page breaks."""
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_auto_page_break(auto=True, margin=15)
        self.title_text = "Restaurant App - E2E Endpoint Test Report"

    def header(self) -> None:
        """Draw the slim title band on every page."""
        self.set_fill_color(*_HEADER_BG)
        self.rect(0, 0, 210, 12, "F")
        self.set_y(3)
        self.set_font("helvetica", "B", 9)
        self.set_text_color(*_WHITE)
        self.cell(0, 6, _txt(self.title_text), align="C")
        self.set_y(16)
        self.set_text_color(*_DARK)

    def footer(self) -> None:
        """Draw the page number footer."""
        self.set_y(-12)
        self.set_font("helvetica", "I", 8)
        self.set_text_color(*_GREY)
        self.cell(0, 6, f"Page {self.page_no()}/{{nb}}", align="C")


def _summary_page(pdf: _ReportPDF, recorder: Recorder, meta: dict) -> None:
    """Render the cover block: run metadata and overall pass/fail counts."""
    pdf.add_page()
    pdf.set_font("helvetica", "B", 18)
    pdf.cell(0, 12, "End-to-End API Test Report", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("helvetica", "", 9)
    pdf.set_text_color(*_GREY)
    for label, key in [
        ("Run started", "started_at"),
        ("Run finished", "finished_at"),
        ("API base URL", "base_url"),
        ("AWS account", "account"),
        ("AWS region", "region"),
    ]:
        pdf.set_font("helvetica", "B", 9)
        pdf.cell(32, 5.5, f"{label}:")
        pdf.set_font("helvetica", "", 9)
        pdf.cell(0, 5.5, _txt(meta.get(key, "-")), new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(*_DARK)
    pdf.ln(4)

    total = len(recorder.results)
    passed = recorder.passed_count
    failed = recorder.failed_count

    boxes = [
        ("TOTAL STEPS", str(total), _DARK),
        ("PASSED", str(passed), _GREEN),
        ("FAILED", str(failed), _RED if failed else _GREY),
    ]
    x = pdf.l_margin
    for label, value, color in boxes:
        pdf.set_xy(x, pdf.get_y())
        pdf.set_draw_color(*color)
        pdf.set_line_width(0.5)
        pdf.rect(x, pdf.get_y(), 58, 22)
        pdf.set_xy(x, pdf.get_y() + 3)
        pdf.set_font("helvetica", "B", 20)
        pdf.set_text_color(*color)
        pdf.cell(58, 10, value, align="C")
        pdf.set_xy(x, pdf.get_y() + 10)
        pdf.set_font("helvetica", "", 8)
        pdf.set_text_color(*_GREY)
        pdf.cell(58, 6, label, align="C")
        x += 62
    pdf.set_text_color(*_DARK)
    pdf.ln(30)


def _summary_table(pdf: _ReportPDF, results: list[StepResult]) -> None:
    """Render the one-line-per-endpoint overview table."""
    pdf.set_font("helvetica", "B", 13)
    pdf.cell(0, 9, "Endpoint Summary", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)

    widths = [14, 13, 66, 17, 13, 17, 17, 33]
    headers = ["Step", "Method", "Path", "Expected", "Got", "HTTP", "DB", "Result"]

    def _header_row() -> None:
        pdf.set_font("helvetica", "B", 7.5)
        pdf.set_fill_color(*_HEADER_BG)
        pdf.set_text_color(*_WHITE)
        for width, head in zip(widths, headers):
            pdf.cell(width, 6, head, border=1, fill=True, align="C")
        pdf.ln()
        pdf.set_text_color(*_DARK)

    _header_row()
    for index, result in enumerate(results):
        if pdf.get_y() > 270:
            pdf.add_page()
            _header_row()
        fill = index % 2 == 1
        pdf.set_fill_color(*_LIGHT_ROW)
        pdf.set_font("helvetica", "", 7)

        path = result.path if len(result.path) <= 52 else result.path[:49] + "..."
        if result.status_code is not None:
            got = str(result.status_code)
        elif result.reason.startswith("skipped"):
            got = "SKIP"
        else:
            got = "ERR"
        http_mark = (
            "SKIP" if got == "SKIP" else ("OK" if result.http_passed else "FAIL")
        )
        if not result.db_checks:
            db_mark = "-"
        else:
            db_mark = "OK" if result.db_passed else "FAIL"
        overall = "PASS" if result.passed else "FAIL"

        cells = [
            (result.step, "C", _DARK),
            (result.method, "C", _DARK),
            (path, "L", _DARK),
            (result.expected, "C", _DARK),
            (got, "C", _DARK),
            (http_mark, "C", _GREEN if result.http_passed else _RED),
            (
                db_mark,
                "C",
                _GREY if db_mark == "-" else (_GREEN if result.db_passed else _RED),
            ),
            (overall, "C", _GREEN if result.passed else _RED),
        ]
        for (text, align, color), width in zip(cells, widths):
            pdf.set_text_color(*color)
            pdf.cell(width, 5.5, _txt(text), border=1, fill=fill, align=align)
        pdf.ln()
    pdf.set_text_color(*_DARK)


def _detail_block(pdf: _ReportPDF, result: StepResult) -> None:
    """Render the full request/response/DB detail card for one step."""
    if pdf.get_y() > 235:
        pdf.add_page()

    color = _GREEN if result.passed else _RED
    pdf.set_fill_color(*color)
    pdf.rect(pdf.l_margin, pdf.get_y(), 2, 7, "F")
    pdf.set_x(pdf.l_margin + 4)
    pdf.set_font("helvetica", "B", 10)
    pdf.cell(150, 7, _txt(f"{result.step}  -  {result.name}"))
    pdf.set_text_color(*color)
    pdf.cell(
        0,
        7,
        "PASS" if result.passed else "FAIL",
        align="R",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.set_text_color(*_DARK)

    pdf.set_font("helvetica", "", 8)
    pdf.cell(
        0,
        5,
        _txt(
            f"{result.method} {result.path}    (as: {result.auth_user},"
            f" {result.duration_ms:.0f} ms)"
        ),
        new_x="LMARGIN",
        new_y="NEXT",
    )

    if result.request_query:
        pdf.set_font("helvetica", "B", 8)
        pdf.cell(22, 5, "Query:")
        pdf.set_font("courier", "", 7.5)
        pdf.multi_cell(
            0, 4, _txt(json.dumps(result.request_query)), new_x="LMARGIN", new_y="NEXT"
        )
    if result.request_body:
        pdf.set_font("helvetica", "B", 8)
        pdf.cell(0, 5, "Request body:", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("courier", "", 7.5)
        pdf.set_x(pdf.l_margin + 4)
        pdf.multi_cell(
            0,
            3.6,
            _txt(json.dumps(result.request_body, indent=2)),
            new_x="LMARGIN",
            new_y="NEXT",
        )

    if result.status_code is not None:
        status_text = str(result.status_code)
    elif result.reason.startswith("skipped"):
        status_text = "not executed (skipped)"
    else:
        status_text = "request error"
    pdf.set_font("helvetica", "B", 8)
    pdf.cell(22, 5, "Response:")
    pdf.set_font("helvetica", "", 8)
    pdf.set_text_color(*(_GREEN if result.http_passed else _RED))
    pdf.cell(
        0,
        5,
        _txt(f"HTTP {status_text}  (expected {result.expected})"),
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.set_text_color(*_DARK)
    if result.reason:
        pdf.set_font("helvetica", "I", 8)
        pdf.set_text_color(*_RED)
        pdf.set_x(pdf.l_margin + 4)
        pdf.multi_cell(
            0, 4, _txt(f"reason: {result.reason}"), new_x="LMARGIN", new_y="NEXT"
        )
        pdf.set_text_color(*_DARK)

    body = result.response_body
    if body:
        if len(body) > 1600:
            body = body[:1600] + "\n... (truncated)"
        pdf.set_font("courier", "", 7)
        pdf.set_x(pdf.l_margin + 4)
        pdf.multi_cell(0, 3.4, _txt(body), new_x="LMARGIN", new_y="NEXT")

    if result.db_checks:
        pdf.set_font("helvetica", "B", 8)
        pdf.cell(0, 5, "Database verification:", new_x="LMARGIN", new_y="NEXT")
        for check in result.db_checks:
            mark_color = _GREEN if check.passed else _RED
            pdf.set_x(pdf.l_margin + 4)
            pdf.set_font("helvetica", "B", 8)
            pdf.set_text_color(*mark_color)
            pdf.cell(8, 4.4, "[OK]" if check.passed else "[X]")
            pdf.set_text_color(*_DARK)
            pdf.set_font("helvetica", "", 8)
            pdf.multi_cell(
                0,
                4.4,
                _txt(f"{check.table}: {check.expectation}"),
                new_x="LMARGIN",
                new_y="NEXT",
            )
            if check.before or check.after:
                pdf.set_font("courier", "", 7)
                pdf.set_text_color(*_GREY)
                if check.before:
                    pdf.set_x(pdf.l_margin + 12)
                    pdf.multi_cell(
                        0,
                        3.6,
                        _txt(f"before: {check.before}"),
                        new_x="LMARGIN",
                        new_y="NEXT",
                    )
                if check.after:
                    pdf.set_x(pdf.l_margin + 12)
                    pdf.multi_cell(
                        0,
                        3.6,
                        _txt(f"after : {check.after}"),
                        new_x="LMARGIN",
                        new_y="NEXT",
                    )
                pdf.set_text_color(*_DARK)
    elif result.method in ("GET",):
        pdf.set_font("helvetica", "I", 8)
        pdf.set_text_color(*_GREY)
        pdf.cell(
            0,
            5,
            "Database verification: read-only endpoint - no change expected.",
            new_x="LMARGIN",
            new_y="NEXT",
        )
        pdf.set_text_color(*_DARK)

    pdf.ln(3)
    pdf.set_draw_color(220, 224, 228)
    pdf.set_line_width(0.2)
    pdf.line(pdf.l_margin, pdf.get_y(), 210 - pdf.r_margin, pdf.get_y())
    pdf.ln(3)


def generate_pdf(recorder: Recorder, meta: dict, output_path: str) -> None:
    """Write the full PDF report (summary + per-endpoint details) to disk.

    Args:
        recorder: The Recorder holding every StepResult of the run.
        meta: Run metadata — base_url, account, region, started_at, finished_at.
        output_path: Destination path of the PDF file.

    """
    pdf = _ReportPDF()
    pdf.alias_nb_pages()

    _summary_page(pdf, recorder, meta)
    _summary_table(pdf, recorder.results)

    pdf.add_page()
    pdf.set_font("helvetica", "B", 13)
    pdf.cell(0, 9, "Endpoint Details", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    for result in recorder.results:
        _detail_block(pdf, result)

    pdf.output(output_path)
