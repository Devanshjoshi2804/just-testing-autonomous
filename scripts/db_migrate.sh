#!/bin/bash
#
# Database Migration Script for AutoTest-RL
#

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Print header
echo "======================================================================"
echo "AutoTest-RL Database Migration Manager"
echo "======================================================================"
echo ""

# Parse command line
COMMAND="${1:-help}"

case "$COMMAND" in
    init)
        echo -e "${YELLOW}Initializing database...${NC}"
        alembic upgrade head
        echo -e "${GREEN}Database initialized successfully!${NC}"
        ;;

    upgrade)
        echo -e "${YELLOW}Upgrading database to latest version...${NC}"
        alembic upgrade head
        echo -e "${GREEN}Database upgraded successfully!${NC}"
        ;;

    downgrade)
        REVISION="${2:--1}"
        echo -e "${YELLOW}Downgrading database to: $REVISION${NC}"
        alembic downgrade "$REVISION"
        echo -e "${GREEN}Database downgraded successfully!${NC}"
        ;;

    current)
        echo -e "${YELLOW}Current database version:${NC}"
        alembic current
        ;;

    history)
        echo -e "${YELLOW}Migration history:${NC}"
        alembic history
        ;;

    create)
        MESSAGE="${2}"
        if [ -z "$MESSAGE" ]; then
            echo -e "${RED}Error: Migration message required${NC}"
            echo "Usage: ./scripts/db_migrate.sh create \"migration message\""
            exit 1
        fi
        echo -e "${YELLOW}Creating new migration: $MESSAGE${NC}"
        alembic revision --autogenerate -m "$MESSAGE"
        echo -e "${GREEN}Migration created successfully!${NC}"
        ;;

    reset)
        echo -e "${RED}WARNING: This will drop all tables and re-create them!${NC}"
        read -p "Are you sure? (yes/no): " -r
        echo
        if [[ $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
            echo -e "${YELLOW}Resetting database...${NC}"
            alembic downgrade base
            alembic upgrade head
            echo -e "${GREEN}Database reset successfully!${NC}"
        else
            echo "Reset cancelled."
        fi
        ;;

    stamp)
        REVISION="${2:-head}"
        echo -e "${YELLOW}Stamping database at revision: $REVISION${NC}"
        alembic stamp "$REVISION"
        echo -e "${GREEN}Database stamped successfully!${NC}"
        ;;

    help|--help|-h)
        echo "Database Migration Commands:"
        echo ""
        echo "  init             - Initialize database with latest schema"
        echo "  upgrade          - Upgrade to latest migration"
        echo "  downgrade [rev]  - Downgrade to revision (default: -1)"
        echo "  current          - Show current database version"
        echo "  history          - Show migration history"
        echo "  create <msg>     - Create new migration with autogenerate"
        echo "  reset            - Drop all tables and recreate (dangerous!)"
        echo "  stamp [rev]      - Stamp database at revision (default: head)"
        echo "  help             - Show this help"
        echo ""
        echo "Examples:"
        echo "  ./scripts/db_migrate.sh init"
        echo "  ./scripts/db_migrate.sh upgrade"
        echo "  ./scripts/db_migrate.sh create \"Add user table\""
        echo "  ./scripts/db_migrate.sh downgrade -1"
        echo ""
        echo "Environment Variables:"
        echo "  DATABASE_URL     - Override database connection string"
        echo "                     (default: sqlite:///./autotest.db)"
        echo ""
        exit 0
        ;;

    *)
        echo -e "${RED}Unknown command: $COMMAND${NC}"
        echo "Run './scripts/db_migrate.sh help' for usage"
        exit 1
        ;;
esac
