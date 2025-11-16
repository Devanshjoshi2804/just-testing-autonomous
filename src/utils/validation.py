"""
Validation Utility Functions
Comprehensive validation for URLs, emails, JSON, API keys, and more
"""
import re
import json
import urllib.parse
from typing import Optional, Dict, Any, Tuple, List
from email.utils import parseaddr


# HTTP methods from RFC 7231
VALID_HTTP_METHODS = [
    "GET", "HEAD", "POST", "PUT", "DELETE",
    "CONNECT", "OPTIONS", "TRACE", "PATCH"
]

# HTTP status code ranges
STATUS_CODE_RANGES = {
    "informational": (100, 199),
    "success": (200, 299),
    "redirection": (300, 399),
    "client_error": (400, 499),
    "server_error": (500, 599),
}


def validate_url(
    url: str,
    require_https: bool = False,
    allow_localhost: bool = True,
    check_reachable: bool = False,
) -> Tuple[bool, Optional[str]]:
    """
    Comprehensive URL validation

    Args:
        url: URL to validate
        require_https: Require HTTPS protocol
        allow_localhost: Allow localhost/127.0.0.1
        check_reachable: Check if URL is reachable (makes HTTP request)

    Returns:
        Tuple of (is_valid, error_message)

    Examples:
        >>> validate_url("https://example.com")
        (True, None)
        >>> validate_url("http://example.com", require_https=True)
        (False, "HTTPS required")
    """
    if not url or not isinstance(url, str):
        return False, "URL is empty or not a string"

    url = url.strip()

    # Basic URL regex
    url_pattern = re.compile(
        r'^https?://'  # http or https
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # or IP
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE
    )

    if not url_pattern.match(url):
        return False, "Invalid URL format"

    # Parse URL
    try:
        parsed = urllib.parse.urlparse(url)
    except Exception as e:
        return False, f"Failed to parse URL: {e}"

    # Check protocol
    if parsed.scheme not in ['http', 'https']:
        return False, f"Invalid protocol: {parsed.scheme}"

    if require_https and parsed.scheme != 'https':
        return False, "HTTPS required"

    # Check localhost
    if not allow_localhost:
        localhost_patterns = ['localhost', '127.0.0.1', '0.0.0.0', '::1']
        if parsed.hostname in localhost_patterns:
            return False, "Localhost not allowed"

    # Check for valid hostname
    if not parsed.hostname:
        return False, "Missing hostname"

    # Validate hostname format
    if not _is_valid_hostname(parsed.hostname):
        return False, f"Invalid hostname: {parsed.hostname}"

    # Check port if present
    if parsed.port:
        if not (1 <= parsed.port <= 65535):
            return False, f"Invalid port: {parsed.port}"

    # Check if reachable (optional)
    if check_reachable:
        is_reachable, error = _check_url_reachable(url)
        if not is_reachable:
            return False, f"URL not reachable: {error}"

    return True, None


def _is_valid_hostname(hostname: str) -> bool:
    """Check if hostname is valid"""
    if not hostname or len(hostname) > 253:
        return False

    # Hostname labels
    labels = hostname.split('.')

    # Each label must be 1-63 characters
    for label in labels:
        if not label or len(label) > 63:
            return False

        # Label must start and end with alphanumeric
        if not re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$', label):
            return False

    return True


def _check_url_reachable(url: str, timeout: int = 5) -> Tuple[bool, Optional[str]]:
    """Check if URL is reachable"""
    try:
        import httpx

        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.head(url)

            if response.status_code < 400:
                return True, None
            else:
                return False, f"HTTP {response.status_code}"

    except Exception as e:
        return False, str(e)


def validate_email(email: str, check_mx: bool = False) -> Tuple[bool, Optional[str]]:
    """
    Comprehensive email validation

    Args:
        email: Email address to validate
        check_mx: Check if domain has MX records (requires DNS lookup)

    Returns:
        Tuple of (is_valid, error_message)

    Examples:
        >>> validate_email("user@example.com")
        (True, None)
        >>> validate_email("invalid.email")
        (False, "Invalid email format")
    """
    if not email or not isinstance(email, str):
        return False, "Email is empty or not a string"

    email = email.strip()

    # Basic format check
    if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
        return False, "Invalid email format"

    # Parse email
    name, addr = parseaddr(email)
    if not addr:
        return False, "Could not parse email address"

    # More detailed regex validation
    email_pattern = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )

    if not email_pattern.match(addr):
        return False, "Email contains invalid characters"

    # Check length limits (RFC 5321)
    local, domain = addr.split('@')

    if len(local) > 64:
        return False, "Local part too long (max 64 chars)"

    if len(domain) > 253:
        return False, "Domain too long (max 253 chars)"

    # Check for common typos
    common_domains = {
        'gmail': 'gmail.com',
        'yahoo': 'yahoo.com',
        'outlook': 'outlook.com',
        'hotmail': 'hotmail.com',
    }

    domain_lower = domain.lower()
    for service, correct_domain in common_domains.items():
        if service in domain_lower and domain_lower != correct_domain:
            return False, f"Did you mean {local}@{correct_domain}?"

    # Check MX records (optional)
    if check_mx:
        has_mx, error = _check_mx_records(domain)
        if not has_mx:
            return False, f"No MX records for domain: {error}"

    return True, None


def _check_mx_records(domain: str) -> Tuple[bool, Optional[str]]:
    """Check if domain has MX records"""
    try:
        import dns.resolver

        mx_records = dns.resolver.resolve(domain, 'MX')
        return len(list(mx_records)) > 0, None

    except ImportError:
        return True, "dnspython not available, skipping MX check"

    except Exception as e:
        return False, str(e)


def validate_json(
    json_str: str,
    schema: Optional[Dict[str, Any]] = None,
    strict: bool = True,
) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """
    Validate JSON string

    Args:
        json_str: JSON string to validate
        schema: Optional JSON schema to validate against
        strict: Use strict parsing

    Returns:
        Tuple of (is_valid, error_message, parsed_data)

    Examples:
        >>> validate_json('{"key": "value"}')
        (True, None, {'key': 'value'})
        >>> validate_json('invalid')
        (False, "Invalid JSON: ...", None)
    """
    if not json_str or not isinstance(json_str, str):
        return False, "JSON string is empty or not a string", None

    json_str = json_str.strip()

    # Try to parse JSON
    try:
        if strict:
            data = json.loads(json_str)
        else:
            # Try to fix common issues
            fixed = json_str
            # Replace single quotes with double quotes (not perfect but helps)
            fixed = re.sub(r"'", '"', fixed)
            data = json.loads(fixed)

    except json.JSONDecodeError as e:
        error_msg = f"Invalid JSON: {e.msg} at line {e.lineno}, column {e.colno}"
        return False, error_msg, None

    # Validate against schema if provided
    if schema:
        try:
            import jsonschema

            jsonschema.validate(instance=data, schema=schema)

        except ImportError:
            return True, "jsonschema not available, skipping schema validation", data

        except jsonschema.ValidationError as e:
            return False, f"Schema validation failed: {e.message}", data

    return True, None, data


def validate_api_key(
    api_key: str,
    min_length: int = 20,
    max_length: int = 100,
    allow_spaces: bool = False,
) -> Tuple[bool, Optional[str]]:
    """
    Validate API key format

    Args:
        api_key: API key to validate
        min_length: Minimum length
        max_length: Maximum length
        allow_spaces: Allow spaces in API key

    Returns:
        Tuple of (is_valid, error_message)

    Examples:
        >>> validate_api_key("sk-abcdef1234567890")
        (True, None)
        >>> validate_api_key("short")
        (False, "API key too short")
    """
    if not api_key or not isinstance(api_key, str):
        return False, "API key is empty or not a string"

    # Check for spaces
    if not allow_spaces and ' ' in api_key:
        return False, "API key contains spaces"

    # Check length
    if len(api_key) < min_length:
        return False, f"API key too short (minimum {min_length} characters)"

    if len(api_key) > max_length:
        return False, f"API key too long (maximum {max_length} characters)"

    # Check for common patterns
    if api_key.lower() in ['test', 'demo', 'example', 'placeholder']:
        return False, "API key looks like a placeholder"

    # Check entropy (rough check - real key should have variety)
    unique_chars = len(set(api_key))
    if unique_chars < 10:  # Too few unique characters
        return False, "API key has too little entropy (may be invalid)"

    return True, None


def is_valid_http_method(method: str) -> bool:
    """
    Check if HTTP method is valid

    Args:
        method: HTTP method (GET, POST, etc.)

    Returns:
        True if valid

    Examples:
        >>> is_valid_http_method("GET")
        True
        >>> is_valid_http_method("INVALID")
        False
    """
    if not method or not isinstance(method, str):
        return False

    return method.upper() in VALID_HTTP_METHODS


def is_valid_status_code(status_code: int) -> Tuple[bool, Optional[str]]:
    """
    Check if HTTP status code is valid and return its category

    Args:
        status_code: HTTP status code

    Returns:
        Tuple of (is_valid, category)

    Examples:
        >>> is_valid_status_code(200)
        (True, "success")
        >>> is_valid_status_code(999)
        (False, None)
    """
    if not isinstance(status_code, int):
        return False, None

    if status_code < 100 or status_code > 599:
        return False, None

    # Determine category
    for category, (min_code, max_code) in STATUS_CODE_RANGES.items():
        if min_code <= status_code <= max_code:
            return True, category

    return False, None


def validate_json_path(obj: Dict[str, Any], path: str) -> bool:
    """
    Validate that a JSON path exists in an object

    Args:
        obj: JSON object
        path: Dot-notation path (e.g., "user.profile.name")

    Returns:
        True if path exists

    Examples:
        >>> obj = {"user": {"name": "John"}}
        >>> validate_json_path(obj, "user.name")
        True
        >>> validate_json_path(obj, "user.age")
        False
    """
    if not path:
        return False

    parts = path.split('.')
    current = obj

    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return False

    return True


def validate_file_extension(filename: str, allowed_extensions: List[str]) -> bool:
    """
    Validate file extension

    Args:
        filename: Filename to check
        allowed_extensions: List of allowed extensions (with or without dot)

    Returns:
        True if extension is allowed

    Examples:
        >>> validate_file_extension("doc.pdf", ["pdf", "doc"])
        True
        >>> validate_file_extension("file.exe", ["pdf", "doc"])
        False
    """
    if not filename:
        return False

    # Normalize extensions
    normalized_allowed = [
        ext.lower().lstrip('.') for ext in allowed_extensions
    ]

    # Get file extension
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''

    return ext in normalized_allowed


def validate_ip_address(ip: str, version: Optional[int] = None) -> Tuple[bool, Optional[str]]:
    """
    Validate IP address (IPv4 or IPv6)

    Args:
        ip: IP address string
        version: Optional IP version (4 or 6)

    Returns:
        Tuple of (is_valid, ip_version)

    Examples:
        >>> validate_ip_address("192.168.1.1")
        (True, "ipv4")
        >>> validate_ip_address("2001:0db8::1")
        (True, "ipv6")
    """
    import ipaddress

    if not ip or not isinstance(ip, str):
        return False, None

    try:
        ip_obj = ipaddress.ip_address(ip)

        ip_version = "ipv4" if ip_obj.version == 4 else "ipv6"

        # Check version if specified
        if version and ip_obj.version != version:
            return False, None

        return True, ip_version

    except ValueError:
        return False, None


def validate_port(port: int) -> bool:
    """
    Validate port number

    Args:
        port: Port number

    Returns:
        True if valid

    Examples:
        >>> validate_port(80)
        True
        >>> validate_port(70000)
        False
    """
    return isinstance(port, int) and 1 <= port <= 65535


def sanitize_input(
    text: str,
    max_length: Optional[int] = None,
    allow_html: bool = False,
    remove_null_bytes: bool = True,
) -> str:
    """
    Sanitize user input for security

    Args:
        text: Input text
        max_length: Maximum allowed length
        allow_html: Allow HTML tags
        remove_null_bytes: Remove null bytes

    Returns:
        Sanitized text

    Examples:
        >>> sanitize_input("<script>alert('xss')</script>")
        "alert('xss')"
    """
    if not text:
        return ""

    # Remove null bytes
    if remove_null_bytes:
        text = text.replace('\x00', '')

    # Remove HTML if not allowed
    if not allow_html:
        text = re.sub(r'<[^>]+>', '', text)

    # Truncate if needed
    if max_length and len(text) > max_length:
        text = text[:max_length]

    return text
