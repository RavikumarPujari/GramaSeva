from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

# Operational targets in hours by priority
DEFAULT_PRIORITY_TARGETS: Dict[str, int] = {
    "CRITICAL": 24,
    "HIGH": 48,
    "MEDIUM": 96,
    "LOW": 168,
}

# Category-specific operational target overrides (hours)
CATEGORY_TARGET_OVERRIDES: Dict[str, int] = {
    "water_leak": 24,
    "drainage_overflow": 36,
    "garbage_dump": 48,
    "road_damage": 72,
    "street_light": 48,
    "stray_animals": 72,
    "public_health": 24,
}

def get_sla_target_hours(category: str, priority: str) -> int:
    """Returns the operational target duration in hours based on category and priority."""
    # Priority 'CRITICAL' always takes highest urgency
    if priority == "CRITICAL":
        return 24
    
    # Check category-specific override
    if category in CATEGORY_TARGET_OVERRIDES:
        return CATEGORY_TARGET_OVERRIDES[category]
    
    # Fallback to general priority target
    return DEFAULT_PRIORITY_TARGETS.get(priority.upper(), 96)

def compute_sla_status(
    created_at: datetime,
    category: str,
    priority: str,
    current_status: str,
    resolved_at: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Computes SLA metrics for an issue.
    Label is explicitly 'Operational Target' per master specification rule.
    """
    # Ensure timezone awareness
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    
    now = datetime.now(timezone.utc)
    target_hours = get_sla_target_hours(category, priority)
    deadline_at = created_at + timedelta(hours=target_hours)

    is_terminal = current_status in ("RESOLVED", "REJECTED", "CANCELLED")

    if is_terminal and resolved_at:
        if resolved_at.tzinfo is None:
            resolved_at = resolved_at.replace(tzinfo=timezone.utc)
        comparison_time = resolved_at
    else:
        comparison_time = now

    hours_elapsed = round((comparison_time - created_at).total_seconds() / 3600.0, 1)
    hours_remaining = round((deadline_at - comparison_time).total_seconds() / 3600.0, 1)
    is_overdue = comparison_time > deadline_at and not (is_terminal and resolved_at and resolved_at <= deadline_at)
    overdue_by_hours = round(max(0.0, (comparison_time - deadline_at).total_seconds() / 3600.0), 1)

    return {
        "target_hours": target_hours,
        "deadline_at": deadline_at.isoformat(),
        "hours_elapsed": hours_elapsed,
        "hours_remaining": hours_remaining,
        "is_overdue": is_overdue,
        "overdue_by_hours": overdue_by_hours,
        "label": "Operational Target",  # Not statutory deadline unless verified
    }
