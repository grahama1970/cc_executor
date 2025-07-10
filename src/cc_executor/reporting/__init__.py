"""
Reporting module for CC Executor.

Provides anti-hallucination verification and execution reporting.
Every cc_execute call generates verifiable artifacts that can be checked.

IMPORTANT: For reliable reporting, always use json_mode=True in cc_execute calls.
"""

from .hallucination_check import (
    check_hallucination,
    generate_hallucination_report,
    quick_check
)
from .quick_verify import verify_cc_execute_calls
from .examples_test_reporter import (
    ExamplesTestReporter,
    test_and_report_examples
)
from .json_report_generator import (
    JSONReportGenerator,
    generate_json_report
)

__all__ = [
    'check_hallucination',
    'generate_hallucination_report', 
    'quick_check',
    'verify_cc_execute_calls',
    'ExamplesTestReporter',
    'test_and_report_examples',
    'JSONReportGenerator',
    'generate_json_report'
]