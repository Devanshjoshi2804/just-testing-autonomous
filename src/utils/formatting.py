"""
Formatting Utility Functions
Format numbers, bytes, durations, timestamps with precision
"""
from typing import Union, Optional
from datetime import datetime, timedelta


def format_bytes(
    bytes_value: Union[int, float],
    precision: int = 2,
    binary: bool = True,
) -> str:
    """
    Format bytes to human-readable format

    Args:
        bytes_value: Number of bytes
        precision: Decimal precision
        binary: Use binary units (1024) vs decimal (1000)

    Returns:
        Formatted string (e.g., "1.50 MB")

    Examples:
        >>> format_bytes(1536)
        "1.50 KB"
        >>> format_bytes(1536000)
        "1.46 MB"
    """
    if bytes_value < 0:
        return f"-{format_bytes(-bytes_value, precision, binary)}"

    if bytes_value == 0:
        return "0 B"

    divisor = 1024 if binary else 1000
    units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB'] if binary else ['B', 'kB', 'MB', 'GB', 'TB', 'PB']

    size = float(bytes_value)
    unit_index = 0

    while size >= divisor and unit_index < len(units) - 1:
        size /= divisor
        unit_index += 1

    return f"{size:.{precision}f} {units[unit_index]}"


def format_duration(
    seconds: Union[int, float],
    precision: str = "auto",
    include_milliseconds: bool = False,
) -> str:
    """
    Format duration in seconds to human-readable format

    Args:
        seconds: Duration in seconds
        precision: "auto", "seconds", "minutes", "hours"
        include_milliseconds: Include milliseconds

    Returns:
        Formatted string (e.g., "1h 23m 45s")

    Examples:
        >>> format_duration(90)
        "1m 30s"
        >>> format_duration(3665)
        "1h 1m 5s"
        >>> format_duration(0.123, include_milliseconds=True)
        "123ms"
    """
    if seconds < 0:
        return f"-{format_duration(-seconds, precision, include_milliseconds)}"

    if seconds == 0:
        return "0s"

    # Handle milliseconds
    if include_milliseconds and seconds < 1:
        ms = int(seconds * 1000)
        return f"{ms}ms"

    parts = []

    # Days
    if seconds >= 86400:
        days = int(seconds // 86400)
        parts.append(f"{days}d")
        seconds %= 86400

    # Hours
    if seconds >= 3600:
        hours = int(seconds // 3600)
        parts.append(f"{hours}h")
        seconds %= 3600

    # Minutes
    if seconds >= 60:
        minutes = int(seconds // 60)
        parts.append(f"{minutes}m")
        seconds %= 60

    # Seconds
    if seconds > 0 or not parts:
        if include_milliseconds:
            parts.append(f"{seconds:.3f}s")
        else:
            parts.append(f"{int(seconds)}s")

    # Apply precision
    if precision == "hours":
        parts = parts[:1]
    elif precision == "minutes":
        parts = parts[:2]
    elif precision == "seconds":
        parts = parts[:3]
    # else "auto" - keep all parts

    return " ".join(parts)


def format_timestamp(
    timestamp: Union[datetime, str, float],
    format_type: str = "iso",
    timezone: Optional[str] = None,
) -> str:
    """
    Format timestamp to string

    Args:
        timestamp: Datetime object, ISO string, or Unix timestamp
        format_type: "iso", "human", "short", "custom"
        timezone: Target timezone (e.g., "UTC", "US/Eastern")

    Returns:
        Formatted timestamp string

    Examples:
        >>> dt = datetime(2025, 1, 15, 10, 30, 45)
        >>> format_timestamp(dt, "iso")
        "2025-01-15T10:30:45"
        >>> format_timestamp(dt, "human")
        "Jan 15, 2025 10:30 AM"
    """
    # Convert to datetime
    if isinstance(timestamp, str):
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    elif isinstance(timestamp, (int, float)):
        dt = datetime.fromtimestamp(timestamp)
    elif isinstance(timestamp, datetime):
        dt = timestamp
    else:
        raise ValueError(f"Invalid timestamp type: {type(timestamp)}")

    # Apply timezone if specified
    if timezone:
        import pytz
        tz = pytz.timezone(timezone)
        dt = dt.astimezone(tz)

    # Format based on type
    if format_type == "iso":
        return dt.isoformat()
    elif format_type == "human":
        return dt.strftime("%b %d, %Y %I:%M %p")
    elif format_type == "short":
        return dt.strftime("%Y-%m-%d %H:%M")
    elif format_type == "date":
        return dt.strftime("%Y-%m-%d")
    elif format_type == "time":
        return dt.strftime("%H:%M:%S")
    else:
        return dt.isoformat()


def format_percentage(
    value: float,
    total: Optional[float] = None,
    precision: int = 1,
    include_symbol: bool = True,
) -> str:
    """
    Format percentage

    Args:
        value: Value (0-1 if total is None, else actual value)
        total: Total value (if value is not already 0-1)
        precision: Decimal precision
        include_symbol: Include % symbol

    Returns:
        Formatted percentage string

    Examples:
        >>> format_percentage(0.755)
        "75.5%"
        >>> format_percentage(15, total=20)
        "75.0%"
    """
    if total is not None:
        if total == 0:
            percentage = 0
        else:
            percentage = (value / total) * 100
    else:
        percentage = value * 100

    symbol = "%" if include_symbol else ""
    return f"{percentage:.{precision}f}{symbol}"


def format_number(
    number: Union[int, float],
    precision: Optional[int] = None,
    use_separators: bool = True,
    separator: str = ",",
) -> str:
    """
    Format number with thousand separators

    Args:
        number: Number to format
        precision: Decimal precision (None for integers)
        use_separators: Use thousand separators
        separator: Separator character

    Returns:
        Formatted number string

    Examples:
        >>> format_number(1234567)
        "1,234,567"
        >>> format_number(1234.5678, precision=2)
        "1,234.57"
    """
    if precision is not None:
        formatted = f"{number:.{precision}f}"
    else:
        formatted = str(int(number))

    if use_separators:
        # Split into integer and decimal parts
        parts = formatted.split('.')
        integer_part = parts[0]

        # Add separators to integer part
        integer_with_sep = ""
        for i, digit in enumerate(reversed(integer_part)):
            if i > 0 and i % 3 == 0:
                integer_with_sep = separator + integer_with_sep
            integer_with_sep = digit + integer_with_sep

        # Recombine
        if len(parts) > 1:
            formatted = f"{integer_with_sep}.{parts[1]}"
        else:
            formatted = integer_with_sep

    return formatted
