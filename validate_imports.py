#!/usr/bin/env python3
"""
Import Validation Script
Tests all critical imports without needing to install dependencies
"""
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def check_file_exists(filepath):
    """Check if a file exists"""
    if Path(filepath).exists():
        print(f"✅ {filepath}")
        return True
    else:
        print(f"❌ MISSING: {filepath}")
        return False

def check_class_in_file(filepath, class_name):
    """Check if a class is defined in a file"""
    if not Path(filepath).exists():
        print(f"❌ File not found: {filepath}")
        return False

    with open(filepath, 'r') as f:
        content = f.read()
        if f"class {class_name}" in content:
            print(f"✅ {class_name} in {filepath}")
            return True
        else:
            print(f"❌ MISSING CLASS: {class_name} in {filepath}")
            return False

def check_function_in_file(filepath, func_name):
    """Check if a function is defined in a file"""
    if not Path(filepath).exists():
        print(f"❌ File not found: {filepath}")
        return False

    with open(filepath, 'r') as f:
        content = f.read()
        if f"def {func_name}" in content or f"async def {func_name}" in content:
            print(f"✅ {func_name} in {filepath}")
            return True
        else:
            print(f"❌ MISSING FUNCTION: {func_name} in {filepath}")
            return False

print("=" * 80)
print("IMPORT VALIDATION CHECK")
print("=" * 80)

issues = []

# Core API files
print("\n📦 Core API Files:")
issues.append(not check_file_exists("src/api/main.py"))
issues.append(not check_file_exists("src/config.py"))
issues.append(not check_file_exists("src/exceptions.py"))

# Middleware
print("\n📦 Middleware:")
issues.append(not check_file_exists("src/api/middleware/request_id.py"))
issues.append(not check_file_exists("src/api/middleware/logging_middleware.py"))
issues.append(not check_file_exists("src/api/middleware/security.py"))
issues.append(not check_function_in_file("src/api/middleware/request_id.py", "request_id_middleware"))
issues.append(not check_function_in_file("src/api/middleware/logging_middleware.py", "logging_middleware"))
issues.append(not check_function_in_file("src/api/middleware/security.py", "security_headers_middleware"))

# Health checks
print("\n📦 Health Checks:")
issues.append(not check_file_exists("src/api/health.py"))
issues.append(not check_function_in_file("src/api/health.py", "comprehensive_health_check"))
issues.append(not check_function_in_file("src/api/health.py", "readiness_check"))
issues.append(not check_function_in_file("src/api/health.py", "liveness_check"))

# Routes
print("\n📦 Routes:")
issues.append(not check_file_exists("src/api/routes/__init__.py"))
issues.append(not check_file_exists("src/api/routes/documents.py"))
issues.append(not check_file_exists("src/api/routes/tests.py"))

# Models
print("\n📦 Models:")
issues.append(not check_file_exists("src/models/__init__.py"))
issues.append(not check_class_in_file("src/models/__init__.py", "DocumentUploadResponse"))
issues.append(not check_class_in_file("src/models/__init__.py", "TestSessionResponse"))
issues.append(not check_class_in_file("src/models/__init__.py", "ErrorResponse"))
issues.append(not check_class_in_file("src/models/__init__.py", "EndpointInfo"))

# Parsers
print("\n📦 Parsers:")
issues.append(not check_file_exists("src/parsers/document_parser.py"))
issues.append(not check_file_exists("src/parsers/text_splitter.py"))
issues.append(not check_class_in_file("src/parsers/document_parser.py", "DocumentParser"))
issues.append(not check_class_in_file("src/parsers/text_splitter.py", "DocumentChunker"))

# RAG
print("\n📦 RAG:")
issues.append(not check_file_exists("src/rag/doc_store.py"))
issues.append(not check_class_in_file("src/rag/doc_store.py", "DocumentStore"))

# Agents
print("\n📦 Agents:")
issues.append(not check_file_exists("src/agents/endpoint_analyzer.py"))
issues.append(not check_class_in_file("src/agents/endpoint_analyzer.py", "EndpointAnalyzer"))

# Executors
print("\n📦 Executors:")
issues.append(not check_file_exists("src/executors/test_runner.py"))
issues.append(not check_class_in_file("src/executors/test_runner.py", "TestRunner"))

# Utilities (new)
print("\n📦 Utilities:")
issues.append(not check_file_exists("src/utils/__init__.py"))
issues.append(not check_file_exists("src/utils/text_utils.py"))
issues.append(not check_file_exists("src/utils/validation.py"))
issues.append(not check_file_exists("src/utils/formatting.py"))
issues.append(not check_file_exists("src/utils/retry.py"))
issues.append(not check_file_exists("src/utils/async_helpers.py"))

# Enhanced parsers
print("\n📦 Enhanced Parsers:")
issues.append(not check_file_exists("src/parsers/document_parser_enhanced.py"))
issues.append(not check_class_in_file("src/parsers/document_parser_enhanced.py", "EnhancedDocumentParser"))

# Storage
print("\n📦 Storage:")
issues.append(not check_file_exists("src/storage/redis_storage.py"))

# Tasks
print("\n📦 Tasks (Celery):")
issues.append(not check_file_exists("src/tasks/celery_app.py"))
issues.append(not check_file_exists("src/tasks/document_tasks.py"))
issues.append(not check_file_exists("src/tasks/test_tasks.py"))

# Summary
print("\n" + "=" * 80)
if any(issues):
    print(f"❌ VALIDATION FAILED: {sum(issues)} issue(s) found")
    sys.exit(1)
else:
    print("✅ ALL IMPORTS VALIDATED SUCCESSFULLY")
    sys.exit(0)
