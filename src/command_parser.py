"""Natural-language command parsing interfaces.

Parsing rules will be implemented in the command-parser stage.
"""


SUPPORTED_INTENTS = {
    "add_event",
    "delete_event",
    "query_schedule",
    "mark_completed",
}

SUPPORTED_TASK_TYPES = {
    "fixed_event",
    "deadline_task",
    "essential_task",
    "flexible_plan",
}
