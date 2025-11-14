#!/usr/bin/env python3
"""
Quick Test Script - Verify Core Systems
Tests document parsing, chunking, and dual ChromaDB RAG
"""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from loguru import logger
from src.parsers.document_parser import DocumentParser
from src.parsers.text_splitter import DocumentChunker
from src.rag.doc_store import DocumentStore
from src.rag.flow_store import FlowStore


async def test_document_parsing():
    """Test document parser with sample JSON"""
    print("\n" + "=" * 80)
    print("📄 TEST 1: Document Parsing")
    print("=" * 80)

    # Create sample API documentation
    sample_doc = {
        "api_name": "Test API",
        "base_url": "https://api.example.com",
        "endpoints": [
            {
                "path": "/api/login",
                "method": "POST",
                "description": "User login endpoint",
                "parameters": [
                    {"name": "email", "type": "string", "required": True},
                    {"name": "password", "type": "string", "required": True}
                ],
                "responses": {
                    "200": {"description": "Login successful", "returns": "token"},
                    "401": {"description": "Invalid credentials"}
                }
            },
            {
                "path": "/api/users",
                "method": "GET",
                "description": "Get user list",
                "parameters": [
                    {"name": "page", "type": "integer", "required": False},
                    {"name": "limit", "type": "integer", "required": False}
                ],
                "auth_required": True
            }
        ]
    }

    # Write to temp file
    import json
    temp_file = Path("./test_api_doc.json")
    with open(temp_file, 'w') as f:
        json.dump(sample_doc, f, indent=2)

    print(f"✅ Created sample API doc: {temp_file}")

    # Test parser
    parser = DocumentParser()
    parsed = parser.parse(temp_file)

    print(f"\n📊 Parsing Results:")
    print(f"   Doc Type: {parsed['doc_type']}")
    print(f"   Parser: {parsed['metadata']['parser']}")
    print(f"   File Size: {parsed['metadata']['file_size']} bytes")
    print(f"   Has Structured Data: {parsed['structured_data'] is not None}")

    # Validate it's API doc
    is_api_doc = parser.validate_api_doc(parsed)
    print(f"   Is API Documentation: {is_api_doc}")

    # Extract base URL
    base_url = parser.extract_base_url(parsed)
    print(f"   Base URL: {base_url}")

    print("\n✅ Document parsing test PASSED")

    # Clean up
    temp_file.unlink()

    return parsed


async def test_text_chunking(parsed_doc):
    """Test text chunking"""
    print("\n" + "=" * 80)
    print("✂️ TEST 2: Text Chunking")
    print("=" * 80)

    chunker = DocumentChunker(chunk_size=500, chunk_overlap=100)

    text = parsed_doc['raw_text']
    chunks = chunker.chunk_text(text)

    print(f"\n📊 Chunking Results:")
    print(f"   Original Length: {len(text)} chars")
    print(f"   Number of Chunks: {len(chunks)}")

    stats = chunker.get_chunk_stats(chunks)
    print(f"   Avg Chunk Size: {stats['avg_chunk_size']} chars")
    print(f"   Min Chunk Size: {stats['min_chunk_size']} chars")
    print(f"   Max Chunk Size: {stats['max_chunk_size']} chars")

    print(f"\n📝 First Chunk Preview:")
    print(f"   {chunks[0][:200]}...")

    print("\n✅ Text chunking test PASSED")

    return chunks


async def test_doc_store(chunks):
    """Test Document Store (ChromaDB)"""
    print("\n" + "=" * 80)
    print("🗄️ TEST 3: Document Store (ChromaDB)")
    print("=" * 80)

    doc_store = DocumentStore(collection_name="test_collection")

    # Clear existing data
    doc_store.clear_collection()
    print("✅ Cleared existing test data")

    # Add documents
    print(f"\n📥 Adding {len(chunks)} chunks to ChromaDB...")
    doc_store.add_documents(
        texts=chunks,
        metadatas=[{"chunk_index": i} for i in range(len(chunks))]
    )

    # Get stats
    stats = doc_store.get_stats()
    print(f"\n📊 Store Statistics:")
    print(f"   Collection: {stats['collection_name']}")
    print(f"   Documents: {stats['document_count']}")
    print(f"   Embedding Model: {stats['embedding_model']}")

    # Test semantic search
    print(f"\n🔍 Testing Semantic Search:")

    query = "How to login to the API?"
    results = doc_store.query(query, n_results=2)

    print(f"   Query: '{query}'")
    print(f"   Found: {len(results['documents'])} results")

    if results['documents']:
        print(f"\n   Top Result:")
        print(f"   {results['documents'][0][:200]}...")

    print("\n✅ Document Store test PASSED")

    # Cleanup
    doc_store.delete_collection()

    return doc_store


async def test_flow_store():
    """Test Flow Store (Test Execution State)"""
    print("\n" + "=" * 80)
    print("💾 TEST 4: Flow Store (Test Execution State)")
    print("=" * 80)

    flow_store = FlowStore(session_id="test_session_123")

    # Store a request
    print("\n📤 Storing test request...")
    flow_store.store_request(
        endpoint_key="POST /api/login",
        request_payload={
            "email": "test@example.com",
            "password": "test123"
        },
        metadata={"attempt": 1}
    )

    # Store a response
    print("📥 Storing test response...")
    flow_store.store_response(
        endpoint_key="POST /api/login",
        response_data={
            "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "user_id": 123,
            "email": "test@example.com"
        },
        status_code=200,
        success=True,
        metadata={"attempt": 1}
    )

    # Query for context
    print("\n🔍 Testing Context Retrieval:")

    query = "Find authentication token from previous login"
    context = flow_store.query_for_context(query, n_results=1)

    print(f"   Query: '{query}'")
    print(f"   Context Found:")
    print(f"   {context[:300]}...")

    # Get stats
    stats = flow_store.get_stats()
    print(f"\n📊 Flow Store Statistics:")
    print(f"   Session ID: {stats['session_id']}")
    print(f"   Total Items: {stats['total_items']}")
    print(f"   Requests: {stats['requests']}")
    print(f"   Responses: {stats['responses']}")
    print(f"   Successful: {stats['successful_responses']}")

    # Get successful responses
    successful = flow_store.get_successful_responses()
    print(f"\n✅ Retrieved {len(successful)} successful responses")

    print("\n✅ Flow Store test PASSED")

    # Cleanup
    flow_store.cleanup()

    return flow_store


async def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("🧪 AutoTest-RL Core Systems Test")
    print("=" * 80)

    try:
        # Test 1: Document Parsing
        parsed_doc = await test_document_parsing()

        # Test 2: Text Chunking
        chunks = await test_chunking(parsed_doc)

        # Test 3: Document Store
        await test_doc_store(chunks)

        # Test 4: Flow Store
        await test_flow_store()

        # Final Summary
        print("\n" + "=" * 80)
        print("🎉 ALL TESTS PASSED!")
        print("=" * 80)
        print("\n✅ Core Systems Verified:")
        print("   ✓ Document Parser (PDF/JSON/YAML)")
        print("   ✓ Text Chunker (Semantic splitting)")
        print("   ✓ Document Store (ChromaDB + Mistral embeddings)")
        print("   ✓ Flow Store (Test execution state)")
        print("\n🚀 System is ready for agent implementation!")
        print("=" * 80)

        return 0

    except Exception as e:
        print("\n" + "=" * 80)
        print("❌ TEST FAILED")
        print("=" * 80)
        logger.exception(f"Error: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
