# 🤖 Local Models Guide - AutoTest-RL

## 🎉 Run Completely FREE with Local Models!

AutoTest-RL now supports **local LLM models** via **Ollama** - no API keys needed (except Mistral for embeddings)!

---

## 🚀 Quick Start (Local Mode)

### 1. Minimal Setup

```bash
# Copy environment template
cp .env.template .env

# Edit .env - ONLY need Mistral API key for embeddings
# All other API keys can be left blank!
nano .env
```

### 2. Start Services

```bash
# Start everything including Ollama
./start.sh

# Or using make
make up-build

# Or using docker-compose
docker-compose up -d --build
```

### 3. Models Auto-Download

The system automatically downloads:
- **Phi-3.5 Mini** (3.8B params, ~2.3GB) - Primary model
- **Llama 3.2 3B** (~2GB) - Backup model

First startup takes 5-10 minutes to download models.

---

## 📊 Available Local Models

| Model | Size | RAM | Download | Best For |
|-------|------|-----|----------|----------|
| **phi3.5:3.8b** | 3.8B | 8GB | ~2.3GB | ⭐ **Reasoning, coding** (RECOMMENDED) |
| **llama3.2:3b** | 3B | 6GB | ~2GB | General purpose, fast |
| **llama3.2:1b** | 1B | 4GB | ~1.3GB | Very fast, basic tasks |
| **gemma2:2b** | 2B | 4GB | ~1.6GB | Efficient, Google quality |
| **gemma2:9b** | 9B | 16GB | ~5.5GB | Best quality (needs more RAM) |
| **qwen2.5:3b** | 3B | 6GB | ~2GB | Multilingual, efficient |
| **qwen2.5:7b** | 7B | 12GB | ~4.7GB | Better multilingual |

---

## 🎯 Model Selection

### In `.env` file:

```bash
# Primary LLM (for endpoint analysis, test generation)
LLM_PROVIDER=ollama
LLM_MODEL=phi3.5:3.8b  # Change to any model above

# Fast LLM (for quick tasks)
FAST_LLM_PROVIDER=ollama
FAST_LLM_MODEL=llama3.2:3b  # Use smaller model for speed
```

### Recommended Configurations:

**Balanced (Default)**:
```bash
LLM_MODEL=phi3.5:3.8b       # Best reasoning
FAST_LLM_MODEL=llama3.2:3b  # Fast for retries
```

**Maximum Speed**:
```bash
LLM_MODEL=llama3.2:3b       # Fast
FAST_LLM_MODEL=llama3.2:1b  # Very fast
```

**Maximum Quality** (requires 16GB+ RAM):
```bash
LLM_MODEL=gemma2:9b         # Best quality
FAST_LLM_MODEL=phi3.5:3.8b  # Good quality backup
```

---

## 🛠️ Managing Models

### View Available Models

```bash
# List downloaded models
docker-compose exec ollama ollama list

# Check model info
docker-compose exec ollama ollama show phi3.5:3.8b
```

### Download Additional Models

```bash
# Download a specific model
docker-compose exec ollama ollama pull gemma2:2b

# Download quantized version (smaller, faster)
docker-compose exec ollama ollama pull phi3.5:3.8b-q4_K_M
```

### Remove Models

```bash
# Delete a model to free space
docker-compose exec ollama ollama rm llama3.2:1b
```

### Test a Model

```bash
# Interactive test
docker-compose exec ollama ollama run phi3.5:3.8b "Explain API testing in 3 sentences"

# API test
curl http://localhost:11434/api/generate -d '{
  "model": "phi3.5:3.8b",
  "prompt": "Write a test case for a login API"
}'
```

---

## 🎮 GPU Support (Optional)

### Enable GPU Acceleration

If you have an NVIDIA GPU, enable it for 10-50x faster inference:

#### 1. Install NVIDIA Container Toolkit

```bash
# Ubuntu/Debian
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

#### 2. Uncomment GPU Config in docker-compose.yml

```yaml
ollama:
  # ... other config ...
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1  # or "all" for all GPUs
            capabilities: [gpu]
```

#### 3. Restart Services

```bash
docker-compose down
docker-compose up -d
```

#### 4. Verify GPU Usage

```bash
# Should show GPU utilization
nvidia-smi

# Check Ollama sees GPU
docker-compose exec ollama nvidia-smi
```

---

## 💻 Hardware Requirements

### Minimum (CPU Only)

- **RAM**: 8GB (for phi3.5:3.8b or llama3.2:3b)
- **Storage**: 50GB free
- **CPU**: 4+ cores recommended
- **Speed**: 2-10 tokens/second (slow but works)

### Recommended (CPU)

- **RAM**: 16GB
- **Storage**: 100GB free
- **CPU**: 8+ cores (Intel i7/i9, AMD Ryzen 7/9)
- **Speed**: 5-15 tokens/second

### Optimal (GPU)

- **RAM**: 16GB system + 8GB VRAM
- **GPU**: NVIDIA GTX 1660 / RTX 3060 or better
- **Storage**: 100GB SSD
- **Speed**: 50-200+ tokens/second

---

## 🔍 Model Quantization

Models come in different quantization levels (trade size vs. quality):

| Quantization | Size | Quality | Speed |
|--------------|------|---------|-------|
| **Q4_K_M** | Small | Good | Fast | ⭐ RECOMMENDED |
| **Q5_K_M** | Medium | Better | Medium |
| **Q8_0** | Large | Best | Slow |
| **F16** | Huge | Perfect | Very Slow |

Download specific quantization:
```bash
docker-compose exec ollama ollama pull phi3.5:3.8b-q4_K_M
```

Default models use Q4_K_M for best balance.

---

## 📈 Performance Comparison

### Phi-3.5 Mini (phi3.5:3.8b)

**Strengths:**
- Excellent reasoning abilities
- Great at code generation
- Strong instruction following
- Good at technical content

**Weaknesses:**
- Slower than smaller models
- Needs 8GB+ RAM

**Use For:** Endpoint analysis, test case generation, error fixing

### Llama 3.2 3B

**Strengths:**
- Very fast inference
- Good general purpose
- Meta quality
- Efficient memory use

**Weaknesses:**
- Less reasoning power than Phi-3.5
- May struggle with complex logic

**Use For:** Quick retries, simple payload generation, fast iterations

### Gemma 2 2B

**Strengths:**
- Extremely fast
- Very low memory
- Google quality
- Multilingual support

**Weaknesses:**
- Less capable than larger models
- May need more retries

**Use For:** Ultra-fast operations, resource-constrained environments

---

## 🌐 Ollama API (OpenAI-Compatible)

Ollama provides an OpenAI-compatible API on port 11434:

```python
import openai

# Point to Ollama
client = openai.OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="not-needed"  # Ollama doesn't need keys!
)

# Use like OpenAI
response = client.chat.completions.create(
    model="phi3.5:3.8b",
    messages=[
        {"role": "user", "content": "Explain API testing"}
    ]
)
print(response.choices[0].message.content)
```

---

## 🔄 Switching Between Local and Cloud

### Use Local by Default

```bash
# .env
LLM_PROVIDER=ollama
LLM_MODEL=phi3.5:3.8b
```

### Fallback to Cloud if Needed

```bash
# .env
LLM_PROVIDER=groq  # or openai, anthropic
LLM_MODEL=meta-llama/llama-4-maverick-17b-128e-instruct
GROQ_API_KEY=your_key_here
```

### Hybrid Approach

Use different providers for different tasks:

```python
# config.py
LLM_PROVIDER=ollama          # Local for main work
FAST_LLM_PROVIDER=groq       # Cloud for critical fast tasks
```

---

## 💰 Cost Comparison

### Local (Ollama)

- **Setup Cost**: $0
- **Per Request**: $0
- **Monthly**: $0
- **Requirements**: Your hardware
- **Privacy**: 100% private

### Cloud APIs

- **Setup Cost**: $0
- **Per Request**: $0.0001 - $0.03
- **Monthly**: $10 - $100+ (depending on usage)
- **Requirements**: Internet + API key
- **Privacy**: Data sent to provider

### Recommendation

- **Development/Testing**: Use local (free)
- **Production (high volume)**: Use local (free + private)
- **Production (critical)**: Use cloud for reliability

---

## 🐛 Troubleshooting

### Models Not Downloading

```bash
# Check Ollama logs
docker-compose logs ollama

# Check loader logs
docker-compose logs ollama_loader

# Manual download
docker-compose exec ollama ollama pull phi3.5:3.8b
```

### Out of Memory

```bash
# Use smaller model
LLM_MODEL=llama3.2:1b  # Only 4GB RAM needed

# Or increase Docker memory
# Docker Desktop → Settings → Resources → Memory → 16GB
```

### Slow Performance

```bash
# Use faster model
FAST_LLM_MODEL=llama3.2:1b

# Or enable GPU (see GPU Support section)

# Or use quantized version
docker-compose exec ollama ollama pull phi3.5:3.8b-q4_K_M
```

### Ollama Not Starting

```bash
# Check if port 11434 is available
lsof -i :11434

# Restart Ollama
docker-compose restart ollama

# Check health
curl http://localhost:11434/api/tags
```

---

## 🎓 Best Practices

### 1. Start with Defaults

Use the auto-downloaded models first:
- phi3.5:3.8b for main work
- llama3.2:3b for fast tasks

### 2. Monitor Performance

```bash
# Watch resource usage
docker stats autotest-ollama

# Check response times in logs
make logs-api | grep "Process-Time"
```

### 3. Adjust Based on Results

- **Tests failing?** → Use larger model (gemma2:9b)
- **Too slow?** → Use smaller model (llama3.2:1b)
- **Out of memory?** → Use quantized version (q4_K_M)

### 4. Keep Models Updated

```bash
# Update all models
docker-compose exec ollama ollama list | tail -n +2 | awk '{print $1}' | xargs -I {} docker-compose exec ollama ollama pull {}
```

---

## 📚 Learn More

- **Ollama Docs**: https://ollama.com/
- **Model Library**: https://ollama.com/library
- **Phi-3.5 Info**: https://ollama.com/library/phi3.5
- **Llama 3.2 Info**: https://ollama.com/library/llama3.2
- **Gemma 2 Info**: https://ollama.com/library/gemma2

---

## ✅ Quick Reference

```bash
# List models
docker-compose exec ollama ollama list

# Download model
docker-compose exec ollama ollama pull <model>

# Remove model
docker-compose exec ollama ollama rm <model>

# Test model
docker-compose exec ollama ollama run <model> "test prompt"

# Check Ollama health
curl http://localhost:11434/api/tags

# View Ollama logs
docker-compose logs -f ollama

# Restart Ollama
docker-compose restart ollama
```

---

**🎉 Enjoy FREE, Private, Local AI Testing!**
