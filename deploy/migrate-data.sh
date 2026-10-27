#!/usr/bin/env bash
# Migra el estado del motor local (ledger, estrategia calibrada, histórico) al servidor.
# Uso, desde el Mac y en la carpeta del proyecto:
#   ./deploy/migrate-data.sh ~/Downloads/ssh-key-oracle.key 129.146.10.20
# Detiene el motor local (para no tener dos escuadrones operando a la vez),
# empaqueta data/ de forma consistente y la restaura en el servidor.
set -euo pipefail
cd "$(dirname "$0")/.."

KEY="${1:?Uso: $0 <clave-ssh> <ip-del-servidor> [usuario]}"
HOST="${2:?Falta la IP del servidor}"
USER_REMOTE="${3:-ubuntu}"
SSH=(ssh -i "$KEY" -o StrictHostKeyChecking=accept-new "$USER_REMOTE@$HOST")
ARCHIVE="$(mktemp -d)/escuadron-data.tgz"

chmod 600 "$KEY"
"${SSH[@]}" "test -f ~/escuadron/docker-compose.prod.yml" \
  || { echo "Primero instala el motor en el servidor (deploy/setup-oracle.sh)."; exit 1; }

echo "▸ Deteniendo el motor local"
./start.sh stop || true

echo "▸ Consolidando el WAL de SQLite y empaquetando data/"
.venv/bin/python - <<'PY'
import sqlite3
con = sqlite3.connect("data/ledger.db")
con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
con.close()
PY
tar -czf "$ARCHIVE" --exclude='ledger.db-wal' --exclude='ledger.db-shm' data
echo "  $(du -h "$ARCHIVE" | cut -f1) empaquetados"

echo "▸ Copiando al servidor y restaurando"
scp -i "$KEY" -q "$ARCHIVE" "$USER_REMOTE@$HOST:/tmp/escuadron-data.tgz"
"${SSH[@]}" bash -s <<'REMOTE'
set -euo pipefail
cd ~/escuadron
sudo docker compose -f docker-compose.prod.yml stop app
ts=$(date +%Y%m%d-%H%M%S)
[ -d data ] && sudo mv data "data.antes-de-migrar-$ts"
sudo tar -xzf /tmp/escuadron-data.tgz -C .
rm -f /tmp/escuadron-data.tgz
sudo docker compose -f docker-compose.prod.yml up -d app
echo "  Datos restaurados (copia previa: data.antes-de-migrar-$ts)"
REMOTE

echo "✓ Migración completa. El motor local queda DETENIDO: no lo vuelvas a arrancar"
echo "  mientras el servidor esté operando, o tendrás dos escuadrones con ledgers distintos."
