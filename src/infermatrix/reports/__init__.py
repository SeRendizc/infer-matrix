"""Report models, assemblers, renderers, and writers."""

from infermatrix.reports.assembler import (
    ReportAssemblyError,
    assemble_run_report,
)
from infermatrix.reports.errors import (
    ReportWriteError,
)
from infermatrix.reports.jsonl_writer import (
    write_jsonl_report,
)
from infermatrix.reports.markdown_renderer import (
    render_markdown_report,
)
from infermatrix.reports.markdown_writer import (
    write_markdown_report,
)
from infermatrix.reports.models import (
    ReportCheck,
    RunReport,
    build_run_report,
)

__all__ = [
    "ReportCheck",
    "RunReport",
    "build_run_report",
    "ReportAssemblyError",
    "assemble_run_report",
    "ReportWriteError",
    "render_markdown_report",
    "write_markdown_report",
    "write_jsonl_report",
]