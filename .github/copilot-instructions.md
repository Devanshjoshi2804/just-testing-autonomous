# AI Agent Instructions for Ollama Model Manager

## Project Overview
This is a FastAPI-based model management system for Ollama with Docker containerization. The application provides REST APIs to manage, download, and interact with local LLM models via Ollama.

## Architecture

### Core Components
- **FastAPI Application** (`src/api/main.py`): REST API with health checks and model management endpoints
- **Configuration** (`src/config.py`): Centralized settings for Ollama host, ports, and timeouts
- **Docker Setup**: Multi-stage build with Python 3.11-slim base, runs as non-root user for security

### Key Design Decisions
- **Containerized Ollama**: The app expects Ollama to run in a separate container, accessed via `host.docker.internal:11434`
- **Non-root execution**: Container runs as user `appuser` (UID 1000) for security best practices
- **Health monitoring**: Dedicated `/health` endpoint checks both API and Ollama connectivity

## Development Workflows

### Build & Run (Make commands)
```bash
make build          # Build Docker image
make run            # Run container (port 8000)
make stop           # Stop container
make logs           # View container logs
make shell          # Access container shell
make rebuild        # Clean rebuild
```

### Docker Compose (Recommended)
```bash
docker-compose up -d        # Start both API and Ollama
docker-compose down         # Stop all services
docker-compose logs -f api  # Follow API logs
```

### Local Development
```bash
pip install -r requirements.txt
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

## Project-Specific Conventions

### API Patterns
- All endpoints use FastAPI with type hints and Pydantic models
- Standard response format: `{"status": "...", "message": "...", "data": {...}}`
- Error handling returns appropriate HTTP status codes with descriptive messages

### Configuration Management
- Environment variables override defaults in `src/config.py`
- `OLLAMA_HOST`: Ollama server address (default: `http://host.docker.internal:11434`)
- `API_HOST`/`API_PORT`: API server binding (default: 0.0.0.0:8000)
- `REQUEST_TIMEOUT`: HTTP request timeout for Ollama API calls (default: 300s)

### Docker Networking
- Uses `host.docker.internal` to access host-running Ollama from container
- For production, use `docker-compose.yml` which sets up proper service networking
- API exposed on port 8000, Ollama on 11434

## Critical Integration Points

### Ollama API Communication
- All Ollama interactions use `httpx.AsyncClient` for async/await patterns
- Base URL constructed from `OLLAMA_HOST` environment variable
- Timeouts configured via `REQUEST_TIMEOUT` setting
- Health check validates Ollama connectivity before marking service healthy

### Model Management Flow
1. Models downloaded via Ollama pull API
2. List operations query Ollama's model registry
3. All model operations are asynchronous to prevent blocking

## Testing & Debugging

### Quick Health Check
```bash
curl http://localhost:8000/health
```

### Container Debugging
```bash
make shell                    # Interactive shell in container
docker logs ollama-manager    # View application logs
```

### Common Issues
- **Ollama connection failed**: Ensure Ollama is running and accessible at configured host
- **Permission denied**: Verify entrypoint.sh has execute permissions (`chmod +x entrypoint.sh`)
- **Port conflicts**: Check if port 8000 is available on host

## File Structure Insights
- `entrypoint.sh`: Sets up Python path and launches uvicorn
- `Makefile`: Primary developer interface for Docker operations
- `requirements.txt`: Minimal deps (FastAPI, uvicorn, httpx, pydantic-settings)
- `PROJECT_STATUS.md`, `QUICKSTART.md`: Project documentation and setup guides
