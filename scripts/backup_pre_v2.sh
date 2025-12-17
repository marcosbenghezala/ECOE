#!/usr/bin/env bash
set -euo pipefail

TS="$(date +%Y%m%d_%H%M%S)"
DEST="backups/pre-v2-migration-${TS}"

mkdir -p "$DEST"

echo "📦 Creando backup en $DEST"

cp -r TO_GITHUB/data "$DEST"/data
cp -r TO_GITHUB/simulador "$DEST"/simulador
cp -r TO_GITHUB/casos_procesados "$DEST"/casos_procesados
cp -r TO_GITHUB/scripts "$DEST"/scripts

echo "✅ Backup listo en $DEST"
