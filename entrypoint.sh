#!/bin/bash
set -e

echo "🚀 Starting AutoTest-RL..."

# Wait for ChromaDB to be ready
echo "⏳ Waiting for ChromaDB..."
until curl -f http://chromadb:8000/api/v1/heartbeat > /dev/null 2>&1; do
    echo "   ChromaDB not ready yet... waiting"
    sleep 2
done
echo "✅ ChromaDB is ready!"

# Wait for Redis to be ready
echo "⏳ Waiting for Redis..."
until redis-cli -h redis -p 6379 ping > /dev/null 2>&1; do
    echo "   Redis not ready yet... waiting"
    sleep 2
done
echo "✅ Redis is ready!"

# Execute the main command
echo "🎯 Starting application..."
exec "$@"
