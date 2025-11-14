#!/bin/bash

# AutoTest-RL Model Management Script
# Manage Ollama models easily

set -e

# Colors
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

OLLAMA_CONTAINER="autotest-ollama"

# Check if Ollama container is running
check_ollama() {
    if ! docker ps | grep -q $OLLAMA_CONTAINER; then
        echo -e "${RED}Error: Ollama container is not running${NC}"
        echo "Start it with: docker-compose up -d ollama"
        exit 1
    fi
}

# List all models
list_models() {
    echo -e "${BLUE}📦 Installed Models:${NC}"
    docker-compose exec ollama ollama list
}

# Pull a model
pull_model() {
    local model=$1
    if [ -z "$model" ]; then
        echo -e "${RED}Error: Please specify a model name${NC}"
        echo "Usage: $0 pull <model-name>"
        echo "Example: $0 pull phi3.5:3.8b"
        exit 1
    fi

    echo -e "${BLUE}⬇️  Downloading $model...${NC}"
    docker-compose exec ollama ollama pull "$model"
    echo -e "${GREEN}✅ $model downloaded successfully!${NC}"
}

# Remove a model
remove_model() {
    local model=$1
    if [ -z "$model" ]; then
        echo -e "${RED}Error: Please specify a model name${NC}"
        echo "Usage: $0 remove <model-name>"
        exit 1
    fi

    echo -e "${YELLOW}⚠️  Are you sure you want to remove $model? (y/N)${NC}"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        docker-compose exec ollama ollama rm "$model"
        echo -e "${GREEN}✅ $model removed${NC}"
    else
        echo "Cancelled"
    fi
}

# Test a model
test_model() {
    local model=$1
    local prompt=${2:-"Explain what API testing is in 2 sentences"}

    if [ -z "$model" ]; then
        echo -e "${RED}Error: Please specify a model name${NC}"
        echo "Usage: $0 test <model-name> [prompt]"
        exit 1
    fi

    echo -e "${BLUE}🧪 Testing $model...${NC}"
    echo -e "${BLUE}Prompt: \"$prompt\"${NC}"
    echo ""
    docker-compose exec ollama ollama run "$model" "$prompt"
}

# Show model info
info_model() {
    local model=$1
    if [ -z "$model" ]; then
        echo -e "${RED}Error: Please specify a model name${NC}"
        echo "Usage: $0 info <model-name>"
        exit 1
    fi

    echo -e "${BLUE}ℹ️  Model Info: $model${NC}"
    docker-compose exec ollama ollama show "$model"
}

# List available models (from Ollama library)
available_models() {
    echo -e "${BLUE}📚 Recommended Models for AutoTest-RL:${NC}"
    echo ""
    echo -e "${GREEN}Lightweight (4-8GB RAM):${NC}"
    echo "  phi3.5:3.8b       - ⭐ Best reasoning & coding (3.8B, ~2.3GB)"
    echo "  llama3.2:3b       - Fast general purpose (3B, ~2GB)"
    echo "  llama3.2:1b       - Very fast, basic (1B, ~1.3GB)"
    echo "  gemma2:2b         - Efficient, Google (2B, ~1.6GB)"
    echo "  qwen2.5:3b        - Multilingual (3B, ~2GB)"
    echo ""
    echo -e "${GREEN}Medium (12-16GB RAM):${NC}"
    echo "  gemma2:9b         - Better quality (9B, ~5.5GB)"
    echo "  qwen2.5:7b        - Better multilingual (7B, ~4.7GB)"
    echo "  llama3.2:7b       - Meta quality (7B, ~4.7GB)"
    echo ""
    echo "Download with: $0 pull <model-name>"
}

# Interactive menu
interactive_menu() {
    while true; do
        echo ""
        echo -e "${BLUE}╔═══════════════════════════════════════════════════╗${NC}"
        echo -e "${BLUE}║     AutoTest-RL Model Manager                     ║${NC}"
        echo -e "${BLUE}╚═══════════════════════════════════════════════════╝${NC}"
        echo ""
        echo "1) List installed models"
        echo "2) Download a model"
        echo "3) Remove a model"
        echo "4) Test a model"
        echo "5) Show model info"
        echo "6) Show available models"
        echo "7) Update all models"
        echo "8) Exit"
        echo ""
        read -p "Choose an option: " choice

        case $choice in
            1)
                list_models
                ;;
            2)
                echo "Available models: phi3.5:3.8b, llama3.2:3b, gemma2:2b, etc."
                read -p "Model to download: " model
                pull_model "$model"
                ;;
            3)
                list_models
                read -p "Model to remove: " model
                remove_model "$model"
                ;;
            4)
                list_models
                read -p "Model to test: " model
                read -p "Prompt (or press Enter for default): " prompt
                test_model "$model" "$prompt"
                ;;
            5)
                list_models
                read -p "Model to inspect: " model
                info_model "$model"
                ;;
            6)
                available_models
                ;;
            7)
                echo -e "${BLUE}Updating all models...${NC}"
                docker-compose exec ollama ollama list | tail -n +2 | awk '{print $1}' | while read -r model; do
                    echo -e "${BLUE}Updating $model...${NC}"
                    docker-compose exec ollama ollama pull "$model" || true
                done
                echo -e "${GREEN}✅ All models updated!${NC}"
                ;;
            8)
                echo "Goodbye!"
                exit 0
                ;;
            *)
                echo -e "${RED}Invalid option${NC}"
                ;;
        esac
    done
}

# Main script
main() {
    check_ollama

    if [ $# -eq 0 ]; then
        # No arguments - show interactive menu
        interactive_menu
    else
        # Handle command-line arguments
        command=$1
        shift

        case $command in
            list|ls)
                list_models
                ;;
            pull|download)
                pull_model "$@"
                ;;
            remove|rm)
                remove_model "$@"
                ;;
            test|run)
                test_model "$@"
                ;;
            info|show)
                info_model "$@"
                ;;
            available|search)
                available_models
                ;;
            update)
                echo -e "${BLUE}Updating all models...${NC}"
                docker-compose exec ollama ollama list | tail -n +2 | awk '{print $1}' | while read -r model; do
                    echo -e "${BLUE}Updating $model...${NC}"
                    docker-compose exec ollama ollama pull "$model" || true
                done
                echo -e "${GREEN}✅ All models updated!${NC}"
                ;;
            help|--help|-h)
                echo "AutoTest-RL Model Manager"
                echo ""
                echo "Usage: $0 [command] [options]"
                echo ""
                echo "Commands:"
                echo "  list, ls              - List installed models"
                echo "  pull <model>          - Download a model"
                echo "  remove <model>        - Remove a model"
                echo "  test <model> [prompt] - Test a model"
                echo "  info <model>          - Show model information"
                echo "  available             - Show available models"
                echo "  update                - Update all installed models"
                echo "  help                  - Show this help"
                echo ""
                echo "Examples:"
                echo "  $0 list"
                echo "  $0 pull phi3.5:3.8b"
                echo "  $0 test llama3.2:3b"
                echo "  $0 remove gemma2:2b"
                echo ""
                echo "Run without arguments for interactive menu"
                ;;
            *)
                echo -e "${RED}Unknown command: $command${NC}"
                echo "Run '$0 help' for usage"
                exit 1
                ;;
        esac
    fi
}

main "$@"
