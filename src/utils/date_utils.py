"""
Date and time utility functions.
"""

from datetime import date, datetime, timedelta
from typing import Optional, Tuple, List
from dateutil.relativedelta import relativedelta
import calendar


MONTHS = [
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december"
]


def parse_month_to_date_range(month_name: str, year: Optional[int] = None) -> Tuple[date, date]:
    """
    Convert month name to date range.
    
    Args:
        month_name: Name of the month (e.g., "May")
        year: Year (defaults to current or next year)
        
    Returns:
        Tuple of (start_date, end_date) for that month
    """
    month_name = month_name.lower()
    if month_name not in MONTHS:
        raise ValueError(f"Invalid month: {month_name}")
    
    month_num = MONTHS.index(month_name) + 1
    
    # Determine year
    if year is None:
        current = date.today()
        year = current.year
        # If requested month has passed, use next year
        if month_num < current.month:
            year += 1
    
    # Get first and last day of month
    first_day = date(year, month_num, 1)
    last_day_num = calendar.monthrange(year, month_num)[1]
    last_day = date(year, month_num, last_day_num)
    
    return first_day, last_day


def get_date_range(start: date, duration_days: int) -> Tuple[date, date]:
    """
    Get date range from start date and duration.
    
    Args:
        start: Start date
        duration_days: Duration in days
        
    Returns:
        Tuple of (start_date, end_date)
    """
    end = start + timedelta(days=duration_days)
    return start, end


def get_flexible_date_ranges(
    preferred_start: date,
    duration_days: int,
    flexibility_days: int = 3
) -> List[Tuple[date, date]]:
    """
    Get alternative date ranges within flexibility window.
    
    Args:
        preferred_start: Preferred start date
        duration_days: Trip duration
        flexibility_days: Days of flexibility (±)
        
    Returns:
        List of (start_date, end_date) tuples
    """
    ranges = []
    
    for offset in range(-flexibility_days, flexibility_days + 1):
        start = preferred_start + timedelta(days=offset)
        end = start + timedelta(days=duration_days)
        ranges.append((start, end))
    
    return ranges


def is_weekend(d: date) -> bool:
    """Check if date is on weekend."""
    return d.weekday() >= 5  # Saturday=5, Sunday=6


def get_weekday_name(d: date) -> str:
    """Get weekday name."""
    return calendar.day_name[d.weekday()]


def days_until(target: date) -> int:
    """Get number of days until target date."""
    return (target - date.today()).days


def format_duration(minutes: int) -> str:
    """
    Format duration in minutes to human-readable string.
    
    Args:
        minutes: Duration in minutes
        
    Returns:
        Formatted string (e.g., "2h 30m")
    """
    hours = minutes // 60
    mins = minutes % 60
    
    if hours > 0 and mins > 0:
        return f"{hours}h {mins}m"
    elif hours > 0:
        return f"{hours}h"
    else:
        return f"{mins}m"


def format_date_range(start: date, end: date) -> str:
    """
    Format date range to readable string.
    
    Args:
        start: Start date
        end: End date
        
    Returns:
        Formatted string (e.g., "May 1-5, 2026")
    """
    if start.year == end.year and start.month == end.month:
        return f"{start.strftime('%B')} {start.day}-{end.day}, {start.year}"
    elif start.year == end.year:
        return f"{start.strftime('%B %d')} - {end.strftime('%B %d')}, {start.year}"
    else:
        return f"{start.strftime('%B %d, %Y')} - {end.strftime('%B %d, %Y')}"
