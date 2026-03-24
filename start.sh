#!/bin/bash
# Teto — Inicia o servidor
# Uso: ./start.sh (ou: bash start.sh)

echo ""
echo "  🏠 Iniciando Teto..."
echo ""

cd "$(dirname "$0")"
python3 server.py
