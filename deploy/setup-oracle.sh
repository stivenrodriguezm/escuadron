#!/usr/bin/env bash
# Instala y arranca el Escuadrón en un servidor Ubuntu (Oracle Cloud Always Free, ARM).
# Uso, dentro del servidor:
#   git clone https://github.com/stivenrodriguezm/escuadron.git && cd escuadron
#   ./deploy/setup-oracle.sh
# Es idempotente: se puede volver a ejecutar para actualizar (git pull + rebuild).
set -euo pipefail
cd "$(dirname "$0")/.."

say()  { printf '\n\033[1;32m▸ %s\033[0m\n' "$*"; }
warn() { printf '\n\033[1;33m! %s\033[0m\n' "$*"; }
die()  { printf '\n\033[1;31m✗ %s\033[0m\n' "$*" >&2; exit 1; }

set_env() {  # set_env CLAVE VALOR → crea o reemplaza la línea en .env
  local key="$1" value="$2"
  if grep -q "^${key}=" .env; then
    sed -i "s|^${key}=.*|${key}=${value}|" .env
  else
    printf '%s=%s\n' "$key" "$value" >> .env
  fi
}

get_env() { grep "^$1=" .env 2>/dev/null | head -1 | cut -d= -f2- || true; }

[ -f /etc/os-release ] && . /etc/os-release
[ "${ID:-}" = "ubuntu" ] || die "Este script está pensado para Ubuntu (usa la imagen 'Canonical Ubuntu' en Oracle)."

say "1/6 Comprobando acceso a Binance Futures desde este servidor"
code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 https://fapi.binance.com/fapi/v1/ping || echo 000)
case "$code" in
  200) echo "Binance responde (HTTP 200)." ;;
  451|403) die "Binance bloquea la IP/región de este servidor (HTTP $code). Crea el servidor en otra región permitida." ;;
  *) die "No se pudo contactar con Binance (HTTP $code). Revisa la conexión de red del servidor." ;;
esac

say "2/6 Instalando Docker y utilidades"
sudo apt-get update -qq
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq docker.io docker-compose-v2 git curl openssl iptables-persistent >/dev/null
sudo systemctl enable --now docker >/dev/null
sudo usermod -aG docker "$USER" || true

# Servidores pequeños (p. ej. VM.Standard.E2.1.Micro, 1 GB): swap para compilar la imagen sin quedarse sin memoria
mem_mb=$(awk '/MemTotal/ {print int($2/1024)}' /proc/meminfo)
if [ "$mem_mb" -lt 2048 ] && ! swapon --show | grep -q /swapfile; then
  echo "Memoria baja (${mem_mb} MB): creando 2 GB de swap."
  sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile
  sudo mkswap /swapfile >/dev/null && sudo swapon /swapfile
  grep -q '^/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab >/dev/null
fi

say "3/6 Abriendo los puertos 80 y 443 en el firewall del sistema"
# Las imágenes Ubuntu de Oracle traen iptables con una regla REJECT al final de INPUT.
for port in 80 443; do
  if ! sudo iptables -C INPUT -p tcp --dport "$port" -m state --state NEW -j ACCEPT 2>/dev/null; then
    line=$(sudo iptables -L INPUT --line-numbers | awk '/REJECT/ {print $1; exit}')
    sudo iptables -I INPUT "${line:-1}" -p tcp --dport "$port" -m state --state NEW -j ACCEPT
  fi
done
sudo netfilter-persistent save >/dev/null
echo "Recuerda: también deben estar abiertos en la 'Security List' de la VCN (consola de Oracle)."

say "4/6 Configurando .env"
[ -f .env ] || cp .env.example .env
if [ -z "$(get_env GEMINI_API_KEY)" ]; then
  read -r -s -p "Pega tu GEMINI_API_KEY (Enter para dejar los agentes LLM en modo determinista): " gk; echo
  [ -n "$gk" ] && set_env GEMINI_API_KEY "$gk"
fi
if [ -z "$(get_env API_TOKEN)" ]; then
  set_env API_TOKEN "$(openssl rand -hex 24)"
  echo "Token de acceso generado."
fi
ip=$(curl -s --max-time 10 https://api.ipify.org || curl -s --max-time 10 https://ifconfig.me || true)
[ -n "$ip" ] || die "No se pudo averiguar la IP pública del servidor."
if [ -z "$(get_env DOMAIN)" ]; then
  set_env DOMAIN "${ip//./-}.sslip.io"
fi
chmod 600 .env
mkdir -p data
domain=$(get_env DOMAIN)

say "5/6 Construyendo y arrancando los contenedores (la primera vez tarda unos minutos)"
git pull --ff-only 2>/dev/null || warn "git pull no aplicado (cambios locales o sin red); se usa el código actual."
sudo docker compose -f docker-compose.prod.yml up -d --build

say "6/6 Esperando a que el motor y el certificado HTTPS estén listos"
ok=""
for _ in $(seq 1 60); do
  if curl -fs --max-time 5 "https://${domain}/api/health" >/dev/null 2>&1; then ok=1; break; fi
  sleep 5
done
if [ -z "$ok" ]; then
  warn "Aún no responde por HTTPS. Causas típicas: puertos 80/443 cerrados en la Security List de Oracle, o el certificado todavía se está emitiendo."
  echo "Diagnóstico: sudo docker compose -f docker-compose.prod.yml logs --tail 50"
  exit 1
fi

cat <<EOF

══════════════════════════════════════════════════════════════
  Escuadrón en marcha
  Dashboard:  https://${domain}
  También desde GitHub Pages: https://stivenrodriguezm.github.io/escuadron/
              (dirección del motor: https://${domain})
  Token de acceso (guárdalo, lo pedirá el dashboard):
     $(get_env API_TOKEN)
  Logs:       sudo docker compose -f docker-compose.prod.yml logs -f app
  Actualizar: git pull && ./deploy/setup-oracle.sh
══════════════════════════════════════════════════════════════
EOF
