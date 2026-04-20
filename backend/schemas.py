"""Action schema registry and irreversible action classification."""

ACTION_SCHEMAS: dict[str, list[str]] = {
    "email_external": ["recipient", "subject", "body"],
    "financial_transfer": ["recipient", "amount", "currency"],
    "schedule_meeting": ["title", "time", "attendees"],
    "delete_permanent": ["target_id", "target_type"],
    "reminder_self": ["message", "time"],
    "calendar_event": ["title", "time", "duration"],
}

IRREVERSIBLE_ACTIONS: set[str] = {"email_external", "financial_transfer", "delete_permanent"}
