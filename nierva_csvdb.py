"""Compatibility imports for the question-set view."""

from views.question_sets_view import (
    format_editor_target,
    get_ai_prompt,
    get_csv_example,
    get_csv_template,
    get_schema,
    main,
    set_active_set,
    validate_csv,
)

__all__ = [
    "format_editor_target",
    "get_ai_prompt",
    "get_csv_example",
    "get_csv_template",
    "get_schema",
    "main",
    "set_active_set",
    "validate_csv",
]
