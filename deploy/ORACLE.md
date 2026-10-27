# Despliegue en Oracle Cloud Always Free

Resultado: el escuadrón opera 24/7 en un servidor gratuito, con HTTPS y contraseña, y lo ves desde cualquier dispositivo.

## 1. Crear el servidor (consola de Oracle)

1. Espera el correo de Oracle confirmando que la cuenta está lista (*fully provisioned*).
2. **Menú ☰ → Compute → Instances → Create instance**.
   - **Name:** `escuadron`.
   - **Image:** *Change image* → **Canonical Ubuntu 24.04**.
   - **Shape:** *Change shape* → **Ampere** → **VM.Standard.A1.Flex** → **1 OCPU y 6 GB** (sobra; el máximo gratuito es 2 OCPU y 12 GB). Debe aparecer la etiqueta *Always Free-eligible*.
   - **Networking:** crea una VCN nueva con subred **pública** y marca **Assign a public IPv4 address**.
   - **SSH keys:** **Generate a key pair for me** → **Download private key**. Guarda ese archivo; sin él no podrás entrar.
3. **Create**. Si aparece *Out of capacity*, reintenta más tarde o elige otro *Availability Domain*.
4. Cuando esté en *Running*, copia la **Public IP address**.

## 2. Abrir los puertos 80 y 443

Instancia → enlace de la **Subnet** → **Security Lists** → *Default Security List* → **Add Ingress Rules**. Crea dos reglas:

| Source CIDR | IP Protocol | Destination Port |
|---|---|---|
| `0.0.0.0/0` | TCP | `80` |
| `0.0.0.0/0` | TCP | `443` |

El puerto 80 lo necesita Let's Encrypt para emitir el certificado HTTPS.

## 3. Instalar el motor (desde tu Mac)

```bash
chmod 600 ~/Downloads/ssh-key-*.key
ssh -i ~/Downloads/ssh-key-*.key ubuntu@IP_PUBLICA
```

Ya dentro del servidor:

```bash
git clone https://github.com/stivenrodriguezm/escuadron.git
cd escuadron
./deploy/setup-oracle.sh
```

El script comprueba que Binance es accesible desde el servidor, instala Docker, abre el firewall interno, te pide la `GEMINI_API_KEY`, genera el token de acceso y arranca todo con HTTPS. Al final muestra la **URL** y el **token**: guárdalos.

## 4. Migrar el ledger actual (desde tu Mac, en la carpeta del proyecto)

```bash
./deploy/migrate-data.sh ~/Downloads/ssh-key-XXXX.key IP_PUBLICA
```

Detiene el motor local, copia `data/` (ledger, estrategia calibrada, histórico) al servidor y lo reinicia. Desde ese momento **no vuelvas a arrancar el motor en el Mac**.

## 5. Usarlo

- Abre `https://IP-CON-GUIONES.sslip.io` e introduce el token.
- O usa https://stivenrodriguezm.github.io/escuadron/ con la dirección `https://IP-CON-GUIONES.sslip.io` y el token.

## Mantenimiento

| Tarea | Comando (en el servidor, dentro de `~/escuadron`) |
|---|---|
| Ver logs | `sudo docker compose -f docker-compose.prod.yml logs -f app` |
| Actualizar a la última versión | `git pull && ./deploy/setup-oracle.sh` |
| Reiniciar | `sudo docker compose -f docker-compose.prod.yml restart app` |
| Copia de seguridad (desde el Mac) | `scp -i CLAVE -r ubuntu@IP:~/escuadron/data ./backup-data` |

## Avisos

- **Recuperación de instancias inactivas.** Oracle puede reclamar instancias Always Free con uso muy bajo de CPU, red y memoria durante 7 días, y este motor consume poco. La forma recomendada de evitarlo es pasar la cuenta a **Pay As You Go**: sigue sin cobrar mientras te mantengas en los límites Always Free.
- El token da control total del motor (capital, Kill-Switch). No lo compartas. Para cambiarlo, edita `API_TOKEN` en `~/escuadron/.env` y vuelve a ejecutar `./deploy/setup-oracle.sh`.
