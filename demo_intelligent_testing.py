#!/usr/bin/env python3
"""
End-to-End Demo - Intelligent API Testing System
Demonstrates complete workflow: Document → Parse → Analyze → Test with AI
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from loguru import logger

# Import all components
from src.parsers.document_parser import DocumentParser
from src.parsers.text_splitter import DocumentChunker
from src.rag.doc_store import DocumentStore
from src.rag.flow_store import FlowStore
from src.agents.endpoint_analyzer import EndpointAnalyzer
from src.agents.test_generator import TestGenerator
from src.agents.error_fixer import ErrorFixer
from src.executors.test_runner import TestRunner


async def create_sample_api_doc():
    """Create a realistic sample API documentation"""
    print("\n" + "=" * 80)
    print("📄 STEP 1: Creating Sample API Documentation")
    print("=" * 80)

    api_doc = {
        "api_name": "UserManagement API",
        "version": "1.0.0",
        "base_url": "https://jsonplaceholder.typicode.com",
        "description": "Simple REST API for user management and posts",

        "authentication": {
            "type": "none",
            "note": "JSONPlaceholder is a free fake API, no auth required"
        },

        "endpoints": [
            {
                "path": "/users",
                "method": "GET",
                "summary": "Get all users",
                "description": "Retrieve list of all users in the system",
                "parameters": [],
                "auth_required": False,
                "responses": {
                    "200": {
                        "description": "Success",
                        "example": "[{\"id\": 1, \"name\": \"John\", \"email\": \"john@example.com\"}]"
                    }
                }
            },
            {
                "path": "/users/1",
                "method": "GET",
                "summary": "Get user by ID",
                "description": "Retrieve a specific user",
                "parameters": [
                    {"name": "id", "in": "path", "type": "integer", "required": True}
                ],
                "auth_required": False,
                "responses": {
                    "200": {"description": "User found"},
                    "404": {"description": "User not found"}
                }
            },
            {
                "path": "/posts",
                "method": "GET",
                "summary": "Get all posts",
                "description": "Retrieve all blog posts",
                "parameters": [],
                "auth_required": False
            },
            {
                "path": "/posts",
                "method": "POST",
                "summary": "Create a new post",
                "description": "Create a new blog post",
                "parameters": [
                    {"name": "title", "type": "string", "required": True, "location": "body"},
                    {"name": "body", "type": "string", "required": True, "location": "body"},
                    {"name": "userId", "type": "integer", "required": True, "location": "body"}
                ],
                "auth_required": False,
                "example_request": {
                    "title": "My Post",
                    "body": "Post content here",
                    "userId": 1
                }
            },
            {
                "path": "/posts/1",
                "method": "GET",
                "summary": "Get post by ID",
                "description": "Retrieve a specific post",
                "parameters": [
                    {"name": "id", "in": "path", "type": "integer", "required": True}
                ],
                "auth_required": False
            }
        ]
    }

    # Write to file
    doc_file = Path("./sample_api_doc.json")
    with open(doc_file, 'w') as f:
        json.dump(api_doc, f, indent=2)

    print(f"✅ Created sample API doc: {doc_file}")
    print(f"   API: {api_doc['api_name']}")
    print(f"   Base URL: {api_doc['base_url']}")
    print(f"   Endpoints: {len(api_doc['endpoints'])}")

    return doc_file, api_doc


async def test_document_processing(doc_file):
    """Test document parsing and chunking"""
    print("\n" + "=" * 80)
    print("📖 STEP 2: Document Processing")
    print("=" * 80)

    # Parse document
    parser = DocumentParser()
    parsed = parser.parse(doc_file)

    print(f"\n✅ Document Parsed:")
    print(f"   Type: {parsed['doc_type']}")
    print(f"   Size: {parsed['metadata']['file_size']} bytes")

    # Validate
    is_api_doc = parser.validate_api_doc(parsed)
    print(f"   Valid API Doc: {is_api_doc}")

    # Extract base URL
    base_url = parser.extract_base_url(parsed)
    print(f"   Base URL: {base_url}")

    # Chunk text
    chunker = DocumentChunker(chunk_size=1000, chunk_overlap=200)
    chunks = chunker.chunk_text(parsed['raw_text'])

    print(f"\n✅ Text Chunked:")
    print(f"   Chunks: {len(chunks)}")
    print(f"   Avg Size: {sum(len(c) for c in chunks) // len(chunks)} chars")

    return parsed, chunks, base_url


async def test_rag_system(chunks):
    """Test RAG system - Document Store"""
    print("\n" + "=" * 80)
    print("🗄️ STEP 3: RAG System - Document Store")
    print("=" * 80)

    # Create document store
    doc_store = DocumentStore(collection_name="demo_api_docs")
    doc_store.clear_collection()

    # Add chunks
    print(f"\n📥 Adding {len(chunks)} chunks to ChromaDB...")
    doc_store.add_documents(chunks)

    stats = doc_store.get_stats()
    print(f"\n✅ Doc Store Ready:")
    print(f"   Collection: {stats['collection_name']}")
    print(f"   Documents: {stats['document_count']}")
    print(f"   Model: {stats['embedding_model']}")

    # Test semantic search
    print(f"\n🔍 Testing Semantic Search:")
    query = "How to create a new post?"
    results = doc_store.query(query, n_results=2)

    print(f"   Query: '{query}'")
    print(f"   Results: {len(results['documents'])}")
    if results['documents']:
        print(f"   Top Match: {results['documents'][0][:150]}...")

    return doc_store


async def test_endpoint_analysis(parsed_doc, doc_store):
    """Test endpoint analyzer agent"""
    print("\n" + "=" * 80)
    print("🤖 STEP 4: AI Endpoint Analysis")
    print("=" * 80)

    analyzer = EndpointAnalyzer()

    # Analyze documentation
    print("\n🧠 Analyzing documentation with LLM...")
    analysis = analyzer.analyze_documentation(
        doc_text=parsed_doc['raw_text'],
        chunk_size=5000  # Smaller chunks for demo
    )

    print(f"\n✅ Analysis Complete:")
    print(f"   Base URL: {analysis['base_url']}")
    print(f"   Endpoints Found: {len(analysis['endpoints'])}")
    print(f"   Summary: {analysis['summary']}")

    # Show endpoints
    print(f"\n📋 Extracted Endpoints:")
    for idx, ep in enumerate(analysis['endpoints'], 1):
        auth_marker = "🔒" if ep.get('auth_required') else "🔓"
        print(f"   {idx}. {auth_marker} {ep['method']:6} {ep['path']}")
        if ep.get('summary'):
            print(f"      └─ {ep['summary']}")

    # Get testing order
    test_order = analyzer.get_testing_order(analysis['endpoints'])
    print(f"\n🎯 Optimal Testing Order:")
    for idx, endpoint_key in enumerate(test_order, 1):
        print(f"   {idx}. {endpoint_key}")

    return analysis


async def run_intelligent_testing(base_url, endpoints, doc_store):
    """Run the complete intelligent testing system"""
    print("\n" + "=" * 80)
    print("🚀 STEP 5: Intelligent API Testing with AI Agents")
    print("=" * 80)

    # Create session ID
    import time
    session_id = f"demo_{int(time.time())}"

    print(f"\n📍 Test Session: {session_id}")
    print(f"📍 Base URL: {base_url}")
    print(f"📍 Endpoints to Test: {len(endpoints)}")

    # Run tests
    async with TestRunner(base_url, session_id, doc_store) as runner:
        print(f"\n🎬 Starting test execution...")
        print(f"   Using local Ollama LLM for intelligence")
        print(f"   Max retries per endpoint: {runner.max_retries}")

        # Test all endpoints
        results = await runner.test_all_endpoints(
            endpoints,
            ordered=True  # Use optimal order
        )

        # Get summary
        summary = runner.get_results_summary()

        print(f"\n" + "=" * 80)
        print(f"📊 FINAL RESULTS")
        print(f"=" * 80)
        print(f"\n✅ Test Session Complete!")
        print(f"   Total Tests: {summary['total_tests']}")
        print(f"   Passed: {summary['passed']} ({summary['success_rate']:.1f}%)")
        print(f"   Failed: {summary['failed']}")
        print(f"   Total Time: {summary['total_time']:.2f}s")
        print(f"   Avg Time: {summary['avg_time']:.2f}s")
        print(f"   Total Attempts: {summary['total_attempts']}")

        print(f"\n💾 Flow DB Stats:")
        flow_stats = summary['flow_stats']
        print(f"   Requests Stored: {flow_stats['requests']}")
        print(f"   Responses Stored: {flow_stats['responses']}")
        print(f"   Successful: {flow_stats['successful_responses']}")

        # Show detailed results
        print(f"\n📋 Detailed Results:")
        for idx, result in enumerate(results, 1):
            status = "✅" if result['success'] else "❌"
            print(f"\n   {idx}. {status} {result['endpoint']}")
            print(f"      Status: {result['status_code']} | Time: {result['elapsed_time']:.2f}s")
            print(f"      Attempts: {result['attempts']}")
            if result['success']:
                print(f"      Response: {str(result.get('response', ''))[:100]}...")
            else:
                print(f"      Error: {str(result.get('error', result.get('response', '')))[:100]}...")

        # Cleanup
        runner.cleanup()

        return summary


async def main():
    """Run complete end-to-end demo"""
    print("\n" + "=" * 80)
    print("🎯 AutoTest-RL - Intelligent API Testing Demo")
    print("=" * 80)
    print("\nThis demo showcases:")
    print("  1. Document parsing (PDF/JSON)")
    print("  2. Text chunking for RAG")
    print("  3. ChromaDB storage with embeddings")
    print("  4. AI-powered endpoint analysis")
    print("  5. Intelligent test generation")
    print("  6. Automatic error fixing with retry")
    print("  7. Complete test execution")

    try:
        # Step 1: Create sample API doc
        doc_file, api_doc = await create_sample_api_doc()

        # Step 2: Process document
        parsed, chunks, base_url = await test_document_processing(doc_file)

        # Step 3: Setup RAG
        doc_store = await test_rag_system(chunks)

        # Step 4: Analyze endpoints with AI
        analysis = await test_endpoint_analysis(parsed, doc_store)

        # Step 5: Run intelligent testing
        summary = await run_intelligent_testing(
            base_url or analysis['base_url'],
            analysis['endpoints'],
            doc_store
        )

        # Final summary
        print("\n" + "=" * 80)
        print("🎉 DEMO COMPLETE!")
        print("=" * 80)
        print(f"\n✨ System successfully demonstrated:")
        print(f"   ✓ Document parsing & chunking")
        print(f"   ✓ Dual ChromaDB RAG system")
        print(f"   ✓ AI endpoint analysis")
        print(f"   ✓ Intelligent test generation")
        print(f"   ✓ Automatic error fixing")
        print(f"   ✓ Complete test execution")

        print(f"\n📊 Achievement:")
        print(f"   {summary['passed']}/{summary['total_tests']} tests passed")
        print(f"   {summary['success_rate']:.1f}% success rate")
        print(f"   Completed in {summary['total_time']:.2f}s")

        print(f"\n🚀 System is ready for production use!")
        print("=" * 80 + "\n")

        # Cleanup
        doc_store.delete_collection()
        doc_file.unlink()

        return 0

    except Exception as e:
        print("\n" + "=" * 80)
        print("❌ DEMO FAILED")
        print("=" * 80)
        logger.exception(f"Error: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
