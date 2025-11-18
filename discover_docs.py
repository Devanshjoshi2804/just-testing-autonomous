#!/usr/bin/env python3
"""
Quick script to discover API documentation files
"""
from pathlib import Path

def discover_docs():
    """Find all API documentation in project"""

    # Directories to check
    doc_dirs = [
        Path("docs/api-specs"),
        Path("uploads"),
        Path("data/api-docs")
    ]

    print("=" * 80)
    print("API Documentation Discovery")
    print("=" * 80)

    all_docs = []

    for doc_dir in doc_dirs:
        print(f"\n📁 Searching: {doc_dir}/")

        if not doc_dir.exists():
            print(f"   ⚠️  Directory doesn't exist")
            continue

        # Find PDFs
        pdfs = list(doc_dir.glob("**/*.pdf"))
        # Find JSON
        jsons = list(doc_dir.glob("**/*.json"))
        # Find YAML
        yamls = list(doc_dir.glob("**/*.yaml")) + list(doc_dir.glob("**/*.yml"))

        docs_in_dir = pdfs + jsons + yamls
        all_docs.extend(docs_in_dir)

        if docs_in_dir:
            print(f"   ✅ Found {len(docs_in_dir)} files:")
            for doc in docs_in_dir:
                size_kb = doc.stat().st_size / 1024
                print(f"      📄 {doc.name} ({size_kb:.1f} KB)")
        else:
            print(f"   📭 No files found")

    print("\n" + "=" * 80)
    print(f"TOTAL: {len(all_docs)} API documentation files")
    print("=" * 80)

    if all_docs:
        print("\n✅ Ready to test! Run: python test_real_apis.py")
    else:
        print("\n⚠️  No API documentation found!")
        print("\nPlease add your API docs (PDF, JSON, YAML) to:")
        print("  • docs/api-specs/  (recommended)")
        print("  • uploads/")
        print("  • data/api-docs/")

    return all_docs

if __name__ == "__main__":
    docs = discover_docs()
