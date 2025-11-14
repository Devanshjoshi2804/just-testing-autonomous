# 🐳 Docker Commands Reference

Quick reference for common Docker operations with AutoTest-RL.

## 🚀 Starting Services

```bash
# Start all services in background
docker-compose up -d

# Start with build (if Dockerfile changed)
docker-compose up -d --build

# Start specific service
docker-compose up -d api

# Start with logs visible
docker-compose up

# Start RL training service (optional)
docker-compose --profile training up rl_trainer
```

## 📊 Monitoring & Logs

```bash
# View all logs
docker-compose logs

# Follow logs (live tail)
docker-compose logs -f

# Logs for specific service
docker-compose logs -f api
docker-compose logs -f celery_worker

# Last 100 lines
docker-compose logs --tail=100 api

# Logs with timestamps
docker-compose logs -f -t api
```

## 🔍 Service Status

```bash
# Check running services
docker-compose ps

# Check all containers (including stopped)
docker-compose ps -a

# Check resource usage
docker stats

# Inspect service
docker-compose exec api env
```

## 🛠️ Executing Commands

```bash
# Python shell
docker-compose exec api python

# IPython shell (if installed)
docker-compose exec api ipython

# Bash shell
docker-compose exec api bash

# Run tests
docker-compose exec api pytest tests/ -v

# Run tests with coverage
docker-compose exec api pytest tests/ --cov=src

# Check Python packages
docker-compose exec api pip list
```

## 🔄 Restarting Services

```bash
# Restart all services
docker-compose restart

# Restart specific service
docker-compose restart api
docker-compose restart chromadb

# Stop all services
docker-compose stop

# Stop specific service
docker-compose stop api

# Start stopped service
docker-compose start api
```

## 🗑️ Cleanup

```bash
# Stop and remove containers
docker-compose down

# Remove containers and volumes (⚠️ deletes data)
docker-compose down -v

# Remove containers, volumes, and images
docker-compose down -v --rmi all

# Clean up unused Docker resources
docker system prune

# Remove all stopped containers
docker container prune

# Remove unused images
docker image prune
```

## 🔧 Rebuilding

```bash
# Rebuild all services
docker-compose build

# Rebuild without cache
docker-compose build --no-cache

# Rebuild specific service
docker-compose build api

# Rebuild and start
docker-compose up -d --build
```

## 📦 Volume Management

```bash
# List volumes
docker volume ls

# Inspect volume
docker volume inspect just-testing-autonomous_redis_data

# Remove specific volume (⚠️ deletes data)
docker volume rm just-testing-autonomous_redis_data

# Backup ChromaDB data
docker-compose exec chromadb tar -czf /tmp/chroma-backup.tar.gz /chroma/chroma
docker cp autotest-chromadb:/tmp/chroma-backup.tar.gz ./backups/

# Restore ChromaDB data
docker cp ./backups/chroma-backup.tar.gz autotest-chromadb:/tmp/
docker-compose exec chromadb tar -xzf /tmp/chroma-backup.tar.gz -C /
```

## 🔍 Debugging

```bash
# Check service health
docker-compose exec api curl http://localhost:8000/health

# Check ChromaDB
docker-compose exec api curl http://chromadb:8000/api/v1/heartbeat

# Check Redis
docker-compose exec api redis-cli -h redis ping

# View environment variables
docker-compose exec api env | grep -E "(API_|LLM_|CHROMA_)"

# Check disk usage
docker-compose exec api df -h

# Check memory usage inside container
docker-compose exec api free -h
```

## 🎯 Scaling Services

```bash
# Scale celery workers
docker-compose up -d --scale celery_worker=4

# Scale back down
docker-compose up -d --scale celery_worker=2
```

## 📈 Performance

```bash
# Real-time resource stats
docker stats

# Service-specific stats
docker stats autotest-rl-api

# View logs with performance metrics
docker-compose logs -f api | grep "Process-Time"
```

## 🔐 Security

```bash
# Scan image for vulnerabilities
docker scan autotest-rl-api

# Check running processes
docker-compose exec api ps aux

# Check open ports
docker-compose exec api netstat -tulpn
```

## 🌐 Network

```bash
# List networks
docker network ls

# Inspect network
docker network inspect just-testing-autonomous_autotest-network

# Test connectivity between services
docker-compose exec api ping chromadb
docker-compose exec api telnet redis 6379
```

## 📝 File Operations

```bash
# Copy file TO container
docker cp local-file.pdf autotest-rl-api:/app/uploads/

# Copy file FROM container
docker cp autotest-rl-api:/app/results/report.json ./local-results/

# View file content
docker-compose exec api cat /app/logs/autotest-rl.log

# Edit file (if vim installed)
docker-compose exec api vi /app/.env
```

## 🎓 Common Workflows

### Fresh Start
```bash
docker-compose down -v
docker-compose up -d --build
docker-compose logs -f api
```

### Quick Restart After Code Change
```bash
docker-compose restart api
```

### Full Cleanup and Rebuild
```bash
docker-compose down -v --rmi all
docker-compose build --no-cache
docker-compose up -d
```

### Check if Everything is Working
```bash
docker-compose ps
curl http://localhost:8000/health
curl http://localhost:8001/api/v1/heartbeat
redis-cli -h localhost -p 6379 ping
open http://localhost:8000/docs
```

### Debugging Failed Tests
```bash
docker-compose logs -f api | grep ERROR
docker-compose exec api pytest tests/ -v -s
docker-compose exec api python -m pdb tests/test_file.py
```

## 💡 Pro Tips

1. **Use `-d` flag** to run in background (detached mode)
2. **Use `-f` flag** with logs to follow in real-time
3. **Use `--build` flag** when Dockerfile or requirements.txt change
4. **Use `--no-cache` flag** for clean rebuild (slower but guaranteed fresh)
5. **Use `docker-compose exec`** instead of `docker exec` for service names
6. **Always backup volumes** before running `down -v`
7. **Check logs first** when debugging issues
8. **Use `docker stats`** to monitor resource usage
9. **Scale workers** based on CPU cores available
10. **Use profiles** for optional services (like RL training)

## 🆘 Emergency Commands

```bash
# Kill all containers (nuclear option)
docker kill $(docker ps -q)

# Remove everything (⚠️ DANGER)
docker system prune -a --volumes

# Force remove stuck container
docker rm -f autotest-rl-api

# Force rebuild everything
docker-compose down -v --rmi all && docker-compose build --no-cache && docker-compose up -d
```

## 📚 Learn More

- Docker Compose Docs: https://docs.docker.com/compose/
- Docker CLI Reference: https://docs.docker.com/engine/reference/commandline/cli/
- Best Practices: https://docs.docker.com/develop/dev-best-practices/
