# Escuadrón · Trading multi-agente (paper & live)

Sistema de trading para futuros cripto de Binance en el que **5 agentes especializados** analizan el mercado en tiempo real y operan con **dinero falso sobre datos reales** (libro de órdenes L2, velas, funding), descontando comisiones, spread, slippage y funding exactos. El balance se reinvierte con interés compuesto.

**Dashboard:** https://stivenrodriguezm.github.io/escuadron/. Es solo la interfaz: se conecta a tu motor, ya sea local (`./start.sh`) o en tu servidor (con token de acceso).

> ⚠️ Proyecto experimental. No es asesoría financiera. Por defecto opera en modo simulado (`PAPER_LIVE`). Lee la sección de resultados antes de pensar en dinero real.

## Los 5 agentes

| # | Agente | Implementación | Función |
|---|---|---|---|
| 01 | Analista Cuantitativo | Python determinista · 0 tokens | EMA 20/50/200, RSI, ATR, Z-score de volumen, estructura HH/LL, desequilibrio del libro → `setup_score` 0–100 |
| 02 | Analista de Sentimiento | Python + `gemini-3.5-flash-lite` | Funding, Open Interest, ratio long/short; puntúa titulares RSS reales solo cuando hay setup |
| 03 | Estratega | `gemini-3.5-flash` (respaldo: `gemini-3-flash-preview` → `gemini-3.5-flash-lite`) | Propone BUY/SELL/HOLD en JSON validado; solo despierta si el score supera el umbral |
| 04 | Guardián de Riesgo | Python determinista | R/B neta ≥ 1:2 tras comisiones, pérdida diaria < 3 %, riesgo de cartera ≤ 3 %, stop coherente con ATR, tamaño exacto con interés compuesto |
| 05 | Ejecutor | Python determinista | Ejecuta en el `VirtualBroker` (o Binance Testnet/Real vía ccxt) y vigila SL/TP cada 500 ms |

Los LLM se invocan solo por eventos (setup accionable), con payloads de ~150 tokens. Sin clave de API, los agentes 02 y 03 usan reglas deterministas. También se puede usar Anthropic (`LLM_PROVIDER=anthropic`).

## Estrategia actual y resultados

Calibrada con validación fuera de muestra: parámetros elegidos en abril 2025 → abril 2026 y comprobados en dos periodos no vistos (abril 2024 → abril 2025 y abril 2026 → octubre 2026). Se probaron 6 pares × {15m, 1h, 4h} × 210 combinaciones.

| Par | Velas | Umbral | Stop | Take-profit |
|---|---|---|---|---|
| DOGEUSDT | 4h | 85 | 1.5 ATR | 8 ATR |
| XRPUSDT | 4h | 60 | 1.0 ATR | 5 ATR |
| SOLUSDT | 1h | 75 | 3.0 ATR | 8 ATR |

Riesgo del 1 % por operación, sin stop a break-even (cortaba las tendencias).

**Cartera simulada, 80 semanas fuera de muestra:** media +0.79 %/semana, mediana ≈ 0 %, 48 % de semanas positivas, 1 de cada 10 semanas peor que −4.8 % y 1 de cada 10 mejor que +7.4 %, drawdown máximo del 15–18 %.

Limitaciones honestas:
- Solo 3 de 18 combinaciones par/intervalo pasaron las tres pruebas. Hay sesgo de selección y la expectativa real probablemente es menor.
- El filtro HOLD del LLM no está incluido en el backtest.
- Las velas de 15m pierden en todos los pares probados.

El detalle completo está en [`plan_maestro_de_implementaci_n_para_agente_ia.md`](plan_maestro_de_implementaci_n_para_agente_ia.md), Sección 8.

## Puesta en marcha

Requisitos: Python 3.11+ y Node 20+.

```bash
git clone https://github.com/stivenrodriguezm/escuadron.git
cd escuadron
./start.sh          # instala, compila la UI y deja el motor en segundo plano → http://localhost:8000
./start.sh status | stop | dev | test
```

La primera ejecución crea `.env` a partir de `.env.example`. Añade `GEMINI_API_KEY` (Google AI Studio) para activar los agentes LLM. También se puede levantar con `docker compose up -d`.

En el dashboard pulsa **Iniciar** para que el escuadrón empiece a operar. **Ajustar Capital** cambia el dinero falso en cualquier momento. En **Calibración** puedes lanzar backtests headless y aplicar parámetros a un par en caliente.

## Servidor 24/7 (Oracle Cloud Always Free)

`docker-compose.prod.yml` levanta el motor y Caddy con HTTPS automático (dominio `sslip.io`, sin necesidad de comprar uno) y obliga a usar un token de acceso. La guía paso a paso está en [`deploy/ORACLE.md`](deploy/ORACLE.md):

```bash
./deploy/setup-oracle.sh                    # en el servidor: instala y arranca todo
./deploy/migrate-data.sh CLAVE.key IP       # en el Mac: mueve el ledger al servidor
```

## Arquitectura

- **Backend:** FastAPI, asyncio, WebSockets de Binance (`/public` + `/market`), SQLModel + SQLite en modo WAL (el ledger persiste entre reinicios), polars + parquet para el histórico.
- **Frontend:** React 19, TypeScript estricto, Vite, Tailwind, Recharts.
- **Tests:** `pytest` sobre la contabilidad (interés compuesto, fricción nunca nula, Guardián de Riesgo).

Mapa de archivos y decisiones técnicas: Sección 8 del plan maestro.
