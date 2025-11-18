"""
Text Utility Functions
Detailed text processing, cleaning, and extraction functions
"""
import re
import json
import unicodedata
from typing import List, Optional, Dict, Any
from pathlib import Path


def clean_text(
    text: str,
    remove_extra_whitespace: bool = True,
    remove_special_chars: bool = False,
    lowercase: bool = False,
    remove_numbers: bool = False,
) -> str:
    """
    Clean and normalize text with various options

    Args:
        text: Input text
        remove_extra_whitespace: Remove extra spaces and newlines
        remove_special_chars: Remove special characters (keep alphanumeric)
        lowercase: Convert to lowercase
        remove_numbers: Remove numbers

    Returns:
        Cleaned text

    Examples:
        >>> clean_text("  Hello   World!  \\n\\n  ")
        "Hello World!"
        >>> clean_text("Hello123!", remove_numbers=True, remove_special_chars=True)
        "Hello"
    """
    if not text:
        return ""

    # Normalize unicode characters
    text = unicodedata.normalize('NFKD', text)

    # Remove control characters
    text = ''.join(char for char in text if unicodedata.category(char) != 'Cc' or char in '\n\t')

    # Lowercase
    if lowercase:
        text = text.lower()

    # Remove numbers
    if remove_numbers:
        text = re.sub(r'\d+', '', text)

    # Remove special characters
    if remove_special_chars:
        text = re.sub(r'[^a-zA-Z0-9\s]', '', text)

    # Remove extra whitespace
    if remove_extra_whitespace:
        # Replace multiple spaces with single space
        text = re.sub(r' +', ' ', text)

        # Replace multiple newlines with double newline
        text = re.sub(r'\n{3,}', '\n\n', text)

        # Strip leading/trailing whitespace
        text = text.strip()

    return text


def truncate_text(
    text: str,
    max_length: int,
    suffix: str = "...",
    preserve_words: bool = True,
) -> str:
    """
    Truncate text to maximum length

    Args:
        text: Input text
        max_length: Maximum length (including suffix)
        suffix: Suffix to add when truncated
        preserve_words: Don't cut words in the middle

    Returns:
        Truncated text

    Examples:
        >>> truncate_text("Hello World!", 8)
        "Hello..."
        >>> truncate_text("Hello World!", 8, preserve_words=True)
        "Hello..."
    """
    if not text or len(text) <= max_length:
        return text

    if suffix:
        max_content = max_length - len(suffix)
    else:
        max_content = max_length

    if max_content <= 0:
        return suffix if suffix else ""

    # Truncate
    truncated = text[:max_content]

    # Preserve words if requested
    if preserve_words and ' ' in truncated:
        # Find last space
        last_space = truncated.rfind(' ')
        if last_space > max_content * 0.5:  # Only if we're not cutting too much
            truncated = truncated[:last_space]

    # Add suffix
    return truncated.rstrip() + suffix if suffix else truncated.rstrip()


def extract_urls(
    text: str,
    include_query: bool = True,
    include_fragment: bool = False,
) -> List[str]:
    """
    Extract URLs from text with detailed options

    Args:
        text: Input text
        include_query: Include query parameters
        include_fragment: Include URL fragments (#section)

    Returns:
        List of extracted URLs

    Examples:
        >>> extract_urls("Visit https://example.com and http://test.org")
        ['https://example.com', 'http://test.org']
    """
    if not text:
        return []

    # URL regex pattern
    # Matches http(s)://domain.com/path?query#fragment
    pattern = (
        r'https?://'  # Protocol
        r'(?:www\.)?'  # Optional www
        r'[a-zA-Z0-9]+'  # Domain start
        r'(?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?'  # Domain middle
        r'(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*'  # Subdomains and TLD
        r'(?::[0-9]{1,5})?'  # Optional port
        r'(?:/[^\s]*)?'  # Path
    )

    urls = re.findall(pattern, text, re.IGNORECASE)

    # Process URLs based on options
    processed_urls = []
    for url in urls:
        # Remove query parameters if not needed
        if not include_query and '?' in url:
            url = url.split('?')[0]

        # Remove fragment if not needed
        if not include_fragment and '#' in url:
            url = url.split('#')[0]

        # Remove trailing punctuation (common in text)
        url = url.rstrip('.,;:!?)')

        if url:
            processed_urls.append(url)

    # Remove duplicates while preserving order
    seen = set()
    unique_urls = []
    for url in processed_urls:
        if url not in seen:
            seen.add(url)
            unique_urls.append(url)

    return unique_urls


def extract_json(
    text: str,
    strict: bool = False,
) -> List[Dict[str, Any]]:
    """
    Extract JSON objects from text (even if embedded)

    Args:
        text: Input text
        strict: Use strict JSON parsing

    Returns:
        List of extracted JSON objects

    Examples:
        >>> text = "Here's the data: {\"key\": \"value\"} and more text"
        >>> extract_json(text)
        [{'key': 'value'}]
    """
    if not text:
        return []

    json_objects = []

    # Find potential JSON objects/arrays
    # Look for { ... } or [ ... ]
    potential_jsons = []

    # Find object boundaries
    brace_depth = 0
    bracket_depth = 0
    start_pos = None
    start_char = None

    for i, char in enumerate(text):
        if char == '{' and bracket_depth == 0:
            if brace_depth == 0:
                start_pos = i
                start_char = '{'
            brace_depth += 1

        elif char == '}' and bracket_depth == 0:
            brace_depth -= 1
            if brace_depth == 0 and start_char == '{':
                potential_jsons.append(text[start_pos:i+1])
                start_pos = None

        elif char == '[' and brace_depth == 0:
            if bracket_depth == 0:
                start_pos = i
                start_char = '['
            bracket_depth += 1

        elif char == ']' and brace_depth == 0:
            bracket_depth -= 1
            if bracket_depth == 0 and start_char == '[':
                potential_jsons.append(text[start_pos:i+1])
                start_pos = None

    # Try to parse each potential JSON
    for potential_json in potential_jsons:
        try:
            if strict:
                obj = json.loads(potential_json)
            else:
                # Try to fix common JSON issues
                fixed = potential_json
                # Replace single quotes with double quotes
                fixed = re.sub(r"'", '"', fixed)
                obj = json.loads(fixed)

            json_objects.append(obj)

        except json.JSONDecodeError:
            # Not valid JSON, skip
            continue

    return json_objects


def sanitize_filename(
    filename: str,
    replacement: str = "_",
    max_length: int = 255,
    preserve_extension: bool = True,
) -> str:
    """
    Sanitize filename to be safe for filesystem

    Args:
        filename: Input filename
        replacement: Character to replace invalid chars
        max_length: Maximum filename length
        preserve_extension: Keep file extension within length limit

    Returns:
        Sanitized filename

    Examples:
        >>> sanitize_filename("my file@#$.txt")
        "my_file___.txt"
        >>> sanitize_filename("a" * 300 + ".txt", max_length=255)
        # Returns shortened filename with .txt preserved
    """
    if not filename:
        return "unnamed"

    # Split extension if preserving
    if preserve_extension:
        path = Path(filename)
        name = path.stem
        ext = path.suffix
    else:
        name = filename
        ext = ""

    # Remove/replace invalid characters
    # Invalid: \ / : * ? " < > |
    invalid_chars = r'[\\/:*?"<>|]'
    name = re.sub(invalid_chars, replacement, name)

    # Remove leading/trailing dots and spaces
    name = name.strip('. ')

    # Replace multiple replacements with single
    if replacement:
        pattern = re.escape(replacement) + '+'
        name = re.sub(pattern, replacement, name)

    # Handle max length
    if preserve_extension:
        max_name_length = max_length - len(ext)
    else:
        max_name_length = max_length

    if len(name) > max_name_length:
        name = name[:max_name_length].rstrip('. ' + replacement)

    # Ensure not empty
    if not name:
        name = "unnamed"

    return name + ext if ext else name


def count_tokens_approximate(
    text: str,
    method: str = "words",
) -> int:
    """
    Approximate token count (for LLM usage estimation)

    Args:
        text: Input text
        method: Counting method
            - "words": ~1.3 tokens per word (rough estimate)
            - "chars": ~4 characters per token (OpenAI estimate)
            - "precise": Use tiktoken if available

    Returns:
        Approximate token count

    Examples:
        >>> count_tokens_approximate("Hello world this is a test")
        8  # 6 words * 1.3 ≈ 8 tokens
    """
    if not text:
        return 0

    if method == "words":
        # Simple word count * 1.3 (rough estimate)
        words = len(text.split())
        return int(words * 1.3)

    elif method == "chars":
        # OpenAI's estimate: 1 token ≈ 4 characters
        return len(text) // 4

    elif method == "precise":
        try:
            import tiktoken

            # Use GPT-3.5/4 encoding
            encoding = tiktoken.get_encoding("cl100k_base")
            tokens = encoding.encode(text)
            return len(tokens)

        except ImportError:
            # Fall back to word method
            words = len(text.split())
            return int(words * 1.3)

    else:
        raise ValueError(f"Unknown method: {method}")


def extract_code_blocks(
    text: str,
    language: Optional[str] = None,
) -> List[Dict[str, str]]:
    """
    Extract code blocks from markdown text

    Args:
        text: Markdown text
        language: Filter by language (e.g., "python", "json")

    Returns:
        List of dicts with 'language' and 'code' keys

    Examples:
        >>> text = "```python\\nprint('hello')\\n```"
        >>> extract_code_blocks(text)
        [{'language': 'python', 'code': "print('hello')"}]
    """
    if not text:
        return []

    # Pattern for fenced code blocks: ```language\ncode\n```
    pattern = r'```(\w+)?\n(.*?)\n```'

    matches = re.findall(pattern, text, re.DOTALL)

    code_blocks = []
    for lang, code in matches:
        # Filter by language if specified
        if language and lang.lower() != language.lower():
            continue

        code_blocks.append({
            'language': lang or 'text',
            'code': code.strip(),
        })

    return code_blocks


def normalize_whitespace(text: str) -> str:
    """
    Normalize whitespace while preserving structure

    Args:
        text: Input text

    Returns:
        Text with normalized whitespace
    """
    if not text:
        return ""

    # Replace tabs with spaces
    text = text.replace('\t', '    ')

    # Replace carriage returns
    text = text.replace('\r\n', '\n')
    text = text.replace('\r', '\n')

    # Remove trailing whitespace from each line
    lines = text.split('\n')
    lines = [line.rstrip() for line in lines]

    # Remove leading/trailing empty lines
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()

    # Rejoin
    return '\n'.join(lines)


def extract_emails(text: str) -> List[str]:
    """
    Extract email addresses from text

    Args:
        text: Input text

    Returns:
        List of email addresses
    """
    if not text:
        return []

    # Email regex
    pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'

    emails = re.findall(pattern, text)

    # Remove duplicates while preserving order
    seen = set()
    unique_emails = []
    for email in emails:
        email_lower = email.lower()
        if email_lower not in seen:
            seen.add(email_lower)
            unique_emails.append(email)

    return unique_emails


def word_count(text: str, exclude_numbers: bool = False) -> int:
    """
    Count words in text

    Args:
        text: Input text
        exclude_numbers: Don't count pure numbers as words

    Returns:
        Word count
    """
    if not text:
        return 0

    # Split by whitespace
    words = text.split()

    if exclude_numbers:
        words = [w for w in words if not w.isdigit()]

    return len(words)


def line_count(text: str, exclude_empty: bool = True) -> int:
    """
    Count lines in text

    Args:
        text: Input text
        exclude_empty: Don't count empty/whitespace-only lines

    Returns:
        Line count
    """
    if not text:
        return 0

    lines = text.split('\n')

    if exclude_empty:
        lines = [line for line in lines if line.strip()]

    return len(lines)


def char_count(text: str, exclude_whitespace: bool = False) -> int:
    """
    Count characters in text

    Args:
        text: Input text
        exclude_whitespace: Don't count whitespace characters

    Returns:
        Character count
    """
    if not text:
        return 0

    if exclude_whitespace:
        text = ''.join(text.split())

    return len(text)
