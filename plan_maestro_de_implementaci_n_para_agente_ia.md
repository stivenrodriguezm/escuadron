# 🤖 PLAN MAESTRO DE IMPLEMENTACIÓN: SISTEMA MULTI-AGENTE DE TRADING (PAPER & LIVE)

> **DIRECTIVA CRÍTICA PARA EL AGENTE DE CÓDIGO IA (CLAUDE / GPT / ANTIGRAVITY / CURSOR):**
> Este documento es tu **Fuente Única de Verdad (Single Source of Truth)** y tu **Memoria de Estado**.
> 1. **Flujo de Ejecución:** Lee primero la sección `8. MEMORIA ACTIVA Y MAPA DE CONTEXTO` al final de este archivo antes de explorar el repositorio.
> 2. **Ahorro de Tokens (Regla Estricta):** **PROHIBIDO** leer archivos completos innecesariamente o escanear carpetas como `node_modules`, `.venv`, `.git` o `__pycache__`. Usa el índice de archivos en la Sección 8 para ir directo a las líneas o módulos que necesitas modificar.
> 3. **Actualización Obligatoria:** Cada vez que completes una subtarea:
>    - Cambia su estado de `- [ ]` a `- [x]` en este mismo archivo.
>    - Actualiza la **Sección 8** registrando qué archivos creaste/modificaste, sus firmas/exportaciones clave y cualquier nota técnica relevante para la siguiente sesión.
> 4. **Modularidad:** Ningún archivo de código debe superar las **250 líneas**. Si crece más, divídelo en submódulos claros.

---

## 1. DEFINICIÓN DEL PRODUCTO Y CORRECCIONES DE ARQUITECTURA

### 1.1 Qué Construiremos (El Núcleo)
Una aplicación web financiera de estilo **SaaS institucional minimalista (inspirada en Linear / Stripe)** con **navegación lateral izquierda (Sidebar)** donde un escuadrón de **5 Agentes de IA especializados** opera en tiempo real sobre el mercado cripto (Binance API / WebSockets).
- **Foco Principal:** Operación continua en vivo con **Dinero Falso (Paper Trading Hiperrealista)**. El usuario define cualquier capital inicial (ej. $\$1,000$ o $\$10,000\text{ USDT}$), puede modificarlo cuando quiera y dejar el sistema encendido indefinidamente.
- **Interés Compuesto y Fricción Exacta:** Cada operación ganada o perdida actualiza automáticamente el capital de trabajo disponible para la siguiente operación (interés compuesto real). Se descuentan en tiempo real las comisiones exactas de Binance (Maker/Taker), el *spread* real del libro de órdenes (Order Book L2), el deslizamiento (*slippage*) y las tasas de financiamiento (*funding rates*).
- **El Usuario NO mira velas:** Los agentes analizan los datos matemáticos en segundo plano; el usuario supervisa la evolución compuesta de su cartera, el estado de los 5 agentes, el registro de consenso en tiempo real y el control de riesgo.

### 1.2 Qué Eliminamos (Optimización de Alcance y Tokens)
- ❌ **Eliminado el reproductor visual de velas "Viaje en el Tiempo":** No se construirá un reproductor gráfico pesado para ver velas históricas moverse a 2x/10x.
- ❌ **Eliminado el gráfico de velas (TradingView) de la pantalla principal:** El dashboard principal solo muestra la **Curva de Evolución de Cartera (Rendimiento Compuesto)** limpia.
- ❌ **Eliminadas las pruebas automatizadas de UI (Cypress/Playwright):** El testing se centrará al 100% en las matemáticas del motor de dinero, cálculo de comisiones y reglas del Guardián de Riesgo.
- ✅ **Calibración Histórica Headless (En segundo plano):** Las pruebas con datos del pasado se ejecutan en un motor *headless* ultrarrápido (sin gráficos de velas) que devuelve directamente métricas de rendimiento esperado, Ratio de Sharpe y Drawdown para calibrar a los agentes antes de dejarlos operando en vivo.

---

## 2. ARQUITECTURA TÉCNICA Y OPTIMIZACIÓN DE TOKENS DE IA

### 2.1 Stack Tecnológico
- **Backend (Motor Core, Agentes y Ledger):** Python 3.11+, `FastAPI`, `asyncio`, `websockets`, `ccxt` (conexión a Binance en vivo), `polars` / `pandas` (cálculo vectorial), `SQLModel` + `SQLite` (en modo WAL para persistencia instantánea 24/7 sin perder datos si se reinicia el servidor), `Pydantic v2`.
- **Orquestación de IA:** SDK oficial del proveedor LLM (con *Structured Outputs* en JSON estricto).
- **Frontend (Vista PC - SaaS Minimalista):** `React 19` + `TypeScript` + `Vite`, `Tailwind CSS`, `Lucide React` (iconografía limpia), `Lightweight Charts` o `Recharts` (exclusivamente para el gráfico de área de rendimiento compuesto).

### 2.2 Estrategia de "Cero Desperdicio de Tokens" en Tiempo de Ejecución
Llamar a un LLM cada segundo o en cada vela agotaría el presupuesto de API en horas. El sistema debe implementar **Activación por Eventos (Event-Driven Gating)**:
1. **Filtro Determinista Previo (Costo = $0$ tokens):** El **Agente 01 (Quant)** está escrito 100% en Python matemático. Analiza el flujo de precios de Binance cada segundo/cierre de vela. Mientras el mercado esté en ruido sin estructura clara, **NO invoca a ningún LLM**.
2. **Disparo por Anomalía/Setup:** Solo cuando el Agente Quant detecta una señal matemática con puntuación $\ge 75/100$ (ej. ruptura de estructura + anomalía de volumen + volatilidad ATR favorable), despierta al **Agente 02 (Sentimiento)** y al **Agente 03 (Estratega LLM)**.
3. **Payloads Ultra-Compactos:** Al LLM nunca se le envían tablas de 500 velas en texto. Se le envía un JSON resumido de máximo 180 tokens con las métricas ya calculadas por Python.

---

## 3. FÓRMULAS MATEMÁTICAS OBLIGATORIAS DEL MOTOR (CONTABILIDAD REAL)

El agente de código debe implementar estas ecuaciones exactas en el módulo `backend/core/accounting.py`:

1. **Cálculo de Tamaño de Posición con Interés Compuesto:**
   Cada nueva operación utiliza el Balance Compuesto Actual ($E_t$):
   $$\text{Riesgo en USD } (R_{\text{usd}}) = E_t \times r_{\text{max}}$$
   Donde $r_{\text{max}}$ es el porcentaje de riesgo permitido por operación (por defecto $0.015$ o $1.5\%$).
   $$\text{Tamaño de Posición en Activo } (Q) = \frac{R_{\text{usd}}}{\left| P_{\text{entrada\_efectivo}} - P_{\text{stop\_loss}} \right|}$$

2. **Precio de Entrada y Salida Efectivo (Con Spread y Slippage Real):**
   Consultando el Order Book L2 en vivo de Binance en el milisegundo de ejecución:
   $$P_{\text{entrada\_efectivo}} = P_{\text{ask\_ponderado}}(Q) \times (1 + s_{\text{latencia}})$$
   Donde $P_{\text{ask\_ponderado}}(Q)$ recorre los niveles reales de liquidez del libro de órdenes para cubrir la cantidad $Q$, y $s_{\text{latencia}}$ simula una latencia de red de $150\text{ ms}$.

3. **Deducción de Comisiones y Neto Compuesto:**
   $$\text{Comisión Total } (F) = (Q \times P_{\text{entrada\_efectivo}} \times f_{\text{rate}}) + (Q \times P_{\text{salida\_efectivo}} \times f_{\text{rate}}) + F_{\text{funding}}$$
   Donde $f_{\text{rate}} = 0.0005$ ($0.05\%$ Taker en Binance Futures) o $0.0002$ ($0.02\%$ Maker).
   $$\text{PnL Neto} = Q \times (P_{\text{salida\_efectivo}} - P_{\text{entrada\_efectivo}}) - F$$
   $$E_{t+1} = E_t + \text{PnL Neto}$$

---

## 4. HOJA DE RUTA DE IMPLEMENTACIÓN (CHECKLIST PASO A PASO)

> **Instrucción para el Agente:** Ejecuta las fases en orden estricto. Al terminar cada ítem, márcalo con `[x]` y actualiza la Sección 8.

### FASE 1: Estructura Base, Configuración y Persistencia (Ledger 24/7)
- [x] **1.1 Inicializar Estructura de Directorios:** Crear árbol limpio `backend/` (`core/`, `agents/`, `services/`, `api/`, `models/`, `tests/`) y `frontend/` (`src/components/`, `src/hooks/`, `src/types/`, `src/views/`).
- [x] **1.2 Variables de Entorno y Configuración (`backend/core/config.py`):** Configurar `.env.example` con `LLM_API_KEY`, `BINANCE_API_KEY` (opcional para datos públicos, requerido para Testnet/Real), `EXECUTION_MODE=PAPER_LIVE`, `DEFAULT_VIRTUAL_CAPITAL=10000.0`, `MAX_RISK_PER_TRADE=0.015`, `MAX_DAILY_DRAWDOWN=0.03`.
- [x] **1.3 Modelos de Base de Datos (`backend/models/ledger.py`):** Crear tablas en SQLite (modo WAL) con SQLModel:
  - `PortfolioState`: `id`, `initial_capital`, `current_compound_equity`, `available_balance`, `allocated_margin`, `total_fees_paid`, `total_slippage_cost`, `high_water_mark`, `max_drawdown_pct`, `is_running`, `updated_at`.
  - `Position`: `id`, `symbol`, `side` (`LONG`/`SHORT`), `entry_price`, `current_price`, `quantity`, `stop_loss`, `take_profit`, `unrealized_pnl`, `accumulated_funding`, `opened_at`, `status` (`OPEN`/`CLOSED`).
  - `TradeHistory`: registro inmutable de operaciones cerradas con desglose exacto de PnL bruto, comisión de entrada, comisión de salida, *slippage* real sufrido y PnL neto compuesto.
  - `AgentConsensusLog`: `timestamp`, `agent_id`, `status`, `summary_message`, `token_cost`.
- [x] **1.4 Servicio de Gestión de Capital Virtual (`backend/services/capital_manager.py`):** Implementar funciones para:
  - Inicializar el capital falso en cualquier monto elegido por el usuario.
  - Modificar el capital en caliente (`set_virtual_capital(new_amount)`), recalculando proporcionalmente o reiniciando la curva compuesta según elija el usuario.
  - Calcular métricas en vivo: Rendimiento Total ($\%$), Rendimiento Diario ($\%$), Ratio de Sharpe anualizado, Win Rate ($\%$) y Exposición Actual ($\%$).

### FASE 2: Conexión en Tiempo Real a Binance y Simulador de Fricción Exacta
- [x] **2.1 Cliente de Datos en Vivo (`backend/services/market_stream.py`):** Conectar vía WebSockets públicos de Binance (`wss://fstream.binance.com/ws`) a los pares líquidos (`BTCUSDT`, `ETHUSDT`, `SOLUSDT`) para recibir en tiempo real:
  - Velas cerradas y en formación (`kline_15m`, `kline_1h`).
  - Libro de órdenes en vivo (`depth20@100ms`) para calcular *spread* y *slippage* real.
  - Tasa de financiamiento en vivo (`markPrice@1s`).
- [x] **2.2 Motor de Ejecución Paper Hiperrealista (`backend/core/paper_broker.py`):**
  - Implementar clase `VirtualBroker` con la misma interfaz exacta que el conector real de Binance (`place_order`, `cancel_order`, `get_positions`).
  - Cuando un agente envía una orden con dinero falso, el `VirtualBroker` toma una foto instantánea del Order Book L2 real de Binance en ese milisegundo, calcula el precio de llenado real según la liquidez disponible, resta la comisión oficial de Binance y registra la posición activa.
  - Implementar un bucle asíncrono de vigilancia de ticks (cada $500\text{ ms}$) que verifique si el precio en vivo de Binance tocó el `Stop-Loss` o el `Take-Profit` de alguna posición abierta, cerrándola automáticamente y sumando/restando el resultado al **Balance Compuesto**.

### FASE 3: El Escuadrón de 5 Agentes de IA
- [x] **3.1 Agente 01 - Analista Cuantitativo (`backend/agents/quant_agent.py`):**
  - **100% Determinista en Python (0 tokens).**
  - Calcula en cada cierre de vela o cambio estructural: EMA 20/50/200, RSI(14), ATR(14) para volatilidad, Z-Score de Volumen, estructura de mercado (Higher Highs / Lower Lows) y desequilibrio del Order Book (*Order Book Imbalance*).
  - Emite un objeto `QuantSignal` con un `setup_score` de $0$ a $100$. Si `setup_score < 75`, el ciclo termina aquí y reporta en la UI: `Analizando estructura - Sin anomalías accionables`.
- [x] **3.2 Agente 02 - Analista de Sentimiento y Contexto (`backend/agents/sentiment_agent.py`):**
  - Se activa cuando `setup_score >= 75` o cada 30 minutos con caché en memoria.
  - Analiza *Funding Rates* extremos, cambios bruscos en *Open Interest* y titulares clave de cripto/macro.
  - Devuelve un estado estructurado: `sentiment_score` ($-1.0$ a $+1.0$), `regime_alert` (`NORMAL`, `EUPHORIA`, `PANIC_EVENT`) y resumen de 1 línea.
- [x] **3.3 Agente 03 - Estratega / Orquestador (`backend/agents/strategist_agent.py`):**
  - Único agente que realiza inferencia LLM profunda solo cuando el Quant y el Sentimiento habilitan una ventana de oportunidad.
  - Recibe un *prompt* de sistema ultracompacto con los JSON de `QuantSignal`, `SentimentState` y el estado actual de la cartera.
  - Debe responder exclusivamente con un esquema JSON validado por Pydantic (`TradeProposal`): `action` (`BUY`, `SELL`, `HOLD`), `symbol`, `entry_type` (`MARKET`, `LIMIT`), `suggested_stop_loss`, `suggested_take_profit`, `confidence` ($0$-$100$) y `reasoning_1_line` (máximo 140 caracteres para mostrar en la tabla de consenso de la UI).
- [x] **3.4 Agente 04 - Guardián de Riesgo (`backend/agents/risk_guardian.py`):**
  - **100% Código Duro Determinista (Inhackeable por alucinaciones de IA).**
  - Evalúa el `TradeProposal` del Estratega contra 5 reglas de fuego:
    1. ¿La relación Riesgo/Beneficio neta (después de restar comisiones de entrada y salida estimadas) es $\ge 1:2.0$?
    2. ¿La pérdida diaria acumulada hoy es menor al límite máximo ($3.0\%$)?
    3. ¿La exposición total de la cartera es menor al límite configurado?
    4. ¿La distancia al Stop-Loss es coherente con el ATR actual (ni muy pegada al ruido ni excesivamente amplia)?
    5. ¿Cuál es el tamaño exacto de posición $Q$ aplicando la fórmula de interés compuesto sobre el `current_compound_equity`?
  - Si falla cualquier regla, emite `VETOED` y registra el motivo en el historial de decisiones. Si aprueba, emite `APPROVED` con el tamaño de lote exacto al centavo.
- [x] **3.5 Agente 05 - Ejecutor de Órdenes (`backend/agents/executor_agent.py`):**
  - Recibe la orden aprobada por el Guardián y la ejecuta en el `VirtualBroker` (o en Binance Testnet/Real según configuración).
  - Gestiona posiciones abiertas (ej. mover el Stop-Loss a *Break-Even* cuando la ganancia supera $1.5\text{R}$).

### FASE 4: Motor de Calibración Histórica Headless (Laboratorio Rápido)
- [x] **4.1 Descargador y Caché de Datos Históricos (`backend/services/historical_loader.py`):** Descargar velas históricas reales de Binance y guardarlas en archivos `.parquet` locales para lectura instantánea.
- [x] **4.2 Simulador Vectorial / Basado en Eventos sin Sesgo de Futuro (`backend/core/headless_backtester.py`):**
  - Ejecutar la lógica exacta del Agente Quant + Guardián de Riesgo + Fricción Real sobre cualquier rango de fechas pasado sin interfaz gráfica pesada, garantizando aislamiento estricto punto-en-el-tiempo (*Zero Look-Ahead Bias*).
  - Devolver en segundos el reporte de calibración: Tasa de rendimiento compuesto, Win Rate, Sharpe Ratio, Max Drawdown y total de comisiones pagadas, permitiendo aplicar los parámetros óptimos directamente al modo en vivo.

### FASE 5: API Backend y Streaming WebSocket hacia la Interfaz
- [x] **5.1 Servidor FastAPI (`backend/api/main.py`):**
  - `GET /api/portfolio`: Estado completo del balance compuesto, métricas y posiciones abiertas.
  - `POST /api/capital`: Modificar el capital de dinero falso o reiniciar la simulación.
  - `POST /api/engine/toggle`: Iniciar, pausar o activar el *Kill-Switch* (cerrar todas las posiciones de inmediato).
  - `POST /api/backtest/run`: Disparar una calibración histórica rápida en segundo plano.
  - `WS /ws/telemetry`: WebSocket unificado que envía al frontend cada segundo la actualización del balance compuesto, estado de los 5 agentes y nuevas filas del historial de consenso.

### FASE 6: Interfaz Web Minimalista SaaS con Sidebar (Vista PC)
- [x] **6.1 Sistema de Diseño y Layout con Sidebar (`frontend/src/components/Layout.tsx`):**
  - **Estética:** Fondo principal `#090A0F`, paneles secundarios `#11131A`, bordes sutiles `1px solid #1E2230`, tipografía `Inter` para UI y `JetBrains Mono` (`tabular-nums`) para todas las cifras de dinero y porcentajes. Cero estética de videojuego, cero neones saturados.
  - **Sidebar Izquierdo Fijo (`240px` de ancho):**
    - Logo minimalista en la parte superior.
    - Enlaces de navegación vertical:
      1. `Dashboard` (Vista principal de operación en vivo).
      2. `Módulos de Agentes` (Configuración y telemetría detallada de los 5 agentes).
      3. `Posiciones y Ledger` (Tabla contable de operaciones abiertas/cerradas con desglose de comisiones).
      4. `Calibración (Backtest)` (Panel limpio para lanzar pruebas históricas *headless*).
      5. `Configuración & API` (Cambio entre Dinero Falso / Binance Testnet / Dinero Real).
    - En la parte inferior del Sidebar: Indicador de estado de conexión (`● Binance Stream Activo`), badge del modo actual (`Modo Simulado - Dinero Falso`) y botón rápido de control (`Pausar Algoritmo` / `Kill-Switch`).
- [x] **6.2 Vista Principal (`frontend/src/views/DashboardView.tsx`):**
  - **Fila Superior (4 Tarjetas KPI Limpias):**
    1. **Balance Estimado (Compuesto):** Monto en grande (`$12,450.50 USDT`), variación porcentual neta (`+24.50%`) y botón sutil `Ajustar Capital` que abre un modal limpio para cambiar la cantidad de dinero falso en cualquier momento.
    2. **Capital Base / En Trabajo:** Monto inicial vs. margen actualmente desplegado en posiciones abiertas.
    3. **Rendimiento Neto y Fricción:** Ganancia del día (`+$154.10`) y subtítulo transparente mostrando `Comisiones y Slippage restados: -$18.42 USDT`.
    4. **Exposición de Riesgo:** Riesgo actual comprometido (`1.50% / Máx 2.0%`) y Drawdown Máximo registrado.
  - **Cuerpo Principal (Grid de 2 Columnas Asimétricas en PC):**
    - **Columna Izquierda (`38%` de ancho) - Módulos de Agentes:** Lista limpia de los 5 servicios (`01. Analista Cuantitativo`, `02. Analista de Sentimiento`, `03. Estratega`, `04. Guardián de Riesgo`, `05. Ejecutor de Órdenes`). Cada tarjeta muestra un indicador de estado minimalista (`● Analizando`, `● Activo`, `● Vigilando`), la métrica clave que está evaluando en este segundo y su consumo de tokens.
    - **Columna Derecha Superior (`62%` de ancho) - Evolución de Cartera (Rendimiento Compuesto):** Gráfico de área limpio y elegante (curva verde esmeralda suave `#10B981` sobre fondo oscuro) que traza en tiempo real el crecimiento compuesto del dinero falso, comparándolo opcionalmente con una línea punteada gris del capital inicial.
    - **Columna Derecha Inferior (`62%` de ancho) - Historial de Decisiones (Consenso en Vivo):** Tabla cronológica formal con marca de tiempo (`15:30:12`), nombre del agente y decisión concisa en una sola línea.

### FASE 7: Verificación Matemática y Prueba de Estrés
- [x] **7.1 Tests Unitarios de Contabilidad (`backend/tests/test_accounting.py`):** Verificar mediante `pytest` que:
  - El interés compuesto reinvierte exactamente las ganancias netas y reduce el tamaño de posición tras una racha de pérdidas.
  - Las comisiones y el *slippage* nunca pueden ser cero ni negativos.
  - El Guardián de Riesgo bloquea el 100% de las órdenes si el Stop-Loss está ausente o si se supera el límite de pérdida diaria.
- [x] **7.2 Script de Arranque Unificado (`start.sh` / `docker-compose.yml`):** Crear comando único para levantar Backend + Frontend y dejar el sistema operando dinero falso en segundo plano de forma continua.

---

## 5. REGLAS ESTRICTAS DE CODIFICACIÓN PARA EL AGENTE IA

1. **Prohibido usar datos Mock en el modo en vivo:** Los precios de `BTCUSDT` / `ETHUSDT` y el libro de órdenes deben provenir del WebSocket real de Binance (`wss://fstream.binance.com/ws`), incluso cuando se opera con dinero falso.
2. **Tipado Estricto:** Usa `Pydantic` en todo el backend y `TypeScript` estricto (sin `any`) en el frontend.
3. **Persistencia ante Caídas:** Cada cambio en el balance compuesto o estado de una posición debe guardarse en SQLite inmediatamente mediante transacciones atómicas. Si el usuario cierra el navegador y vuelve a entrar 3 días después, la aplicación debe mostrar la rentabilidad compuesta exacta acumulada durante esos 3 días.

---

## 8. 🧠 MEMORIA ACTIVA Y MAPA DE CONTEXTO (ACTUALIZAR EN CADA PASO)

> **INSTRUCCIÓN PARA EL AGENTE DE CÓDIGO:** Mantén esta sección actualizada al finalizar cada tarea. En tu próxima ejecución, **lee primero esta sección** para saber exactamente dónde quedaste y qué archivos existen sin gastar tokens explorando el proyecto.

### 8.1 Estado Actual de Ejecución
- **Fase Actual:** `FASES 1–7 COMPLETADAS`
- **Última Tarea Completada:** `7.2 Script de arranque unificado (start.sh + Dockerfile + docker-compose.yml)`
- **Próxima Acción Inmediata:** `Dejar operar en PAPER_LIVE ≥ 8 semanas y comparar con la expectativa del backtest (≈ +0.8 %/semana de media, mediana ≈ 0). Recalibrar trimestralmente con validación fuera de muestra. No pasar a TESTNET/LIVE sin ese historial.`
- **Comandos:** `./start.sh` (segundo plano, http://localhost:8000) · `./start.sh dev` (UI en :5173) · `./start.sh test` · `./start.sh stop`

### 8.2 Mapa de Archivos e Interfaces Creadas (Índice para Ahorro de Tokens)
| Ruta del Archivo | Propósito Principal | Clases / Funciones Exportadas | Estado |
| :--- | :--- | :--- | :--- |
| `backend/core/config.py` | Settings desde `.env` | `Settings`, `get_settings()`, `ExecutionMode`, `ROOT_DIR`, `DATA_DIR` | ✅ |
| `backend/core/accounting.py` | Fórmulas puras Sección 3 | `min_take_profit`, `risk_usd`, `position_size`, `weighted_fill_price`, `latency_slippage`, `effective_price`, `fee`, `total_fees`, `gross_pnl`, `net_pnl`, `compound`, `funding_payment`, `net_reward_risk`, `slippage_cost` | ✅ |
| `backend/core/database.py` | SQLite WAL + transacciones | `get_engine(url=None)`, `set_engine()`, `atomic()` (context manager) | ✅ |
| `backend/core/fills.py` | Llenado contra libro L2 | `simulate_market_fill(md,cfg,sym,side,qty,is_entry)->Fill`, `simulate_maker_fill`, `exit_trigger_price`, `MarketDataProvider`, `StaleBookError` | ✅ |
| `backend/core/paper_broker.py` | Broker paper | `VirtualBroker(md,cfg,on_event)`: `place_order`, `cancel_order`, `get_positions`, `update_stop`, `close_position`, `close_all`, `watch_tick`, `_market_fill` (extensión); `run_watch_loop()` | ✅ |
| `backend/core/exchange_broker.py` | Broker real ccxt (TESTNET/LIVE) | `ExchangeBroker(VirtualBroker)` sobreescribe `_market_fill` | ⚠️ sin probar con claves |
| `backend/core/engine.py` | Orquestador del pipeline | `TradingEngine`: `start`, `stop`, `toggle(action)`, `apply_strategy(StrategyUpdate)`, `on_candle_close`, `portfolio_view()`, `symbols`; vigila también pares con posiciones abiertas fuera de la estrategia | ✅ |
| `backend/core/telemetry.py` | Estado agentes + log consenso | `Telemetry`: `set_status`, `log`, `logs_after`, `recent`, `restore_token_totals` | ✅ |
| `backend/core/params.py` | Estrategia calibrada por par | `SymbolStrategy`, `DEFAULT_STRATEGY` (DOGE 4h, XRP 4h, SOL 1h), `load_strategy()`, `save_strategy()` → `data/params.json` | ✅ |
| `backend/core/headless_backtester.py` | Backtest sin look-ahead (incluye break-even del Ejecutor) | `precompute_signals(series,symbol)`, `run_backtest(series,funding,symbol,interval_ms,cfg,threshold,sl,tp,capital,signal_cache=None)->BacktestResult` | ✅ |
| `backend/models/ledger.py` | Tablas SQLModel | `PortfolioState`, `Position`, `TradeHistory`, `AgentConsensusLog`, `EquitySnapshot`, `utcnow()` | ✅ |
| `backend/models/schemas.py` | Contratos Pydantic | `Candle`, `QuantSignal`, `SentimentState`, `TradeProposal`, `RiskDecision`, `Fill`, `OrderResult`, `AgentStatus`, `CapitalUpdate`, `EngineToggle`, `BacktestRequest`, `BacktestResult`, `StrategyUpdate` | ✅ |
| `backend/services/capital_manager.py` | Capital virtual | `get_portfolio(s)`, `init_virtual_capital`, `set_virtual_capital(amount, "RESCALE"/"RESET")`, `apply_realized_pnl`, `set_running`, `record_snapshot` | ✅ |
| `backend/services/metrics.py` | Métricas en vivo | `compute_metrics(s,state)->PortfolioMetrics`, `annualized_sharpe`, `position_risk_usd` | ✅ |
| `backend/services/market_stream.py` | WS Binance (rutas `/public` + `/market`) | `MarketStream`: `bootstrap(only=None)`, `start`, `stop`, `reconfigure(symbols, intervals)`, `on_candle_close(cb)`, `book()`, `last_price()`, `sigma_per_second()`, `healthy`; `BookSnapshot`, `MarkState` | ✅ |
| `backend/services/binance_rest.py` | REST público | `fetch_klines`, `fetch_open_interest_hist`, `fetch_long_short_ratio`, `fetch_premium_index`, `fetch_depth`, `fetch_funding_history` | ✅ |
| `backend/services/historical_loader.py` | Caché parquet | `load_klines(sym,interval,start,end)->pl.DataFrame`, `load_funding()`, `INTERVAL_MS` | ✅ |
| `backend/services/calibration.py` | Jobs de calibración | `launch(BacktestRequest)->BacktestJob`, `JOBS` | ✅ |
| `backend/agents/indicators.py` | Indicadores causales | `ema`, `rsi`, `atr`, `volume_zscore`, `pivots`, `IndicatorSeries` (`build`, `ready`, `structure`, `breakout`) | ✅ |
| `backend/agents/quant_agent.py` | Agente 01 | `score_at(series,i,...)->QuantSignal`, `QuantAgent.analyze/is_actionable` | ✅ |
| `backend/agents/sentiment_agent.py` | Agente 02 | `evaluate(...)` (regla pura), `blend_news(...)`, `SentimentAgent.analyze(symbol, with_news=False)->(SentimentState, tokens)` (caché 30 min por capa) | ✅ |
| `backend/agents/strategist_agent.py` | Agente 03 (LLM) | `StrategistAgent.propose(q,s,portfolio,entry_ref)->(TradeProposal,tokens)`, `compact_payload` (incluye `tpmin`), `deterministic_proposal` | ✅ |
| `backend/services/llm_client.py` | Cliente LLM multi-proveedor | `build_client(cfg, model, fallbacks)->LLMClient|None`, `GeminiClient` (REST, reintentos 429/5xx, cadena de respaldo), `AnthropicClient`, `LLMResult`, `LLMError` | ✅ |
| `backend/services/news_feed.py` | Titulares RSS reales | `recent_headlines(hours=24, limit=20)` (CoinDesk, Cointelegraph, Decrypt; caché 15 min) | ✅ |
| `backend/agents/risk_guardian.py` | Agente 04 | `RiskGuardian.evaluate(proposal, ref_entry, atr, PortfolioView)->RiskDecision` | ✅ |
| `backend/agents/executor_agent.py` | Agente 05 | `ExecutorAgent.execute(decision)`, `manage_positions()`, `breakeven_price(side, entry, fee)`, `reached_breakeven_trigger(...)` | ✅ |
| `backend/api/main.py` | FastAPI | `GET /api/portfolio`, `POST /api/capital`, `POST /api/engine/toggle`, `POST /api/backtest/run`, `GET /api/backtest[/{id}]`, `POST /api/backtest/apply` (body `StrategyUpdate`: par + intervalo + parámetros), `GET /api/trades`, `GET /api/equity`, `GET /api/consensus`, `GET /api/settings`, `WS /ws/telemetry`, SPA estática | ✅ |
| `backend/api/serializers.py` | Payloads JSON | `portfolio_payload`, `telemetry_payload`, `log_row` | ✅ |
| `backend/tests/test_accounting.py` | Tests pytest (motor de dinero + Guardián) | 14 tests; `conftest.py` con `FakeMarket` (solo tests) | ✅ |
| `frontend/src/components/Layout.tsx` | Sidebar 240px + `PageHeader` | `Layout`, `PageHeader` | ✅ |
| `frontend/src/components/*` | UI | `KpiCard`, `AgentList`, `EquityChart` (Recharts), `ConsensusTable`, `CapitalModal`, `format.ts` | ✅ |
| `frontend/src/hooks/*` | Datos | `useTelemetry` (WS con reconexión), `useEquityCurve`, `api` | ✅ |
| `frontend/src/views/*` | Vistas | `DashboardView`, `AgentsView`, `LedgerView`, `BacktestView`, `SettingsView` | ✅ |
| `frontend/src/types/index.ts` | Tipos TS estrictos | Interfaces de todos los payloads | ✅ |
| `backend/api/auth.py` | Token de acceso | `require_token` (Bearer en REST), `websocket_authorized` (`?token=`), `WS_UNAUTHORIZED=4401`; sin `API_TOKEN` no exige nada | ✅ |
| `docker-compose.prod.yml`, `deploy/Caddyfile` | Producción | Motor + Caddy (HTTPS Let's Encrypt, dominio `<ip>.sslip.io`), `REQUIRE_API_TOKEN=1` | ✅ |
| `deploy/setup-oracle.sh`, `deploy/migrate-data.sh`, `deploy/ORACLE.md` | Despliegue en Oracle Cloud Always Free | Instalación idempotente en el servidor y migración de `data/` desde el Mac | ✅ |
| `.github/workflows/ci.yml`, `pages.yml` | CI/CD | Tests + imagen Docker ARM64 con prueba de humo; dashboard en GitHub Pages | ✅ |
| `start.sh`, `Dockerfile`, `docker-compose.yml` | Arranque | `start|stop|status|install-service|uninstall-service|dev|test`; servicio launchd `com.escuadron.motor` | ✅ |

### 8.3 Registro de Decisiones Técnicas y Optimización del Agente
- **[Inicialización]:** Se definió arquitectura híbrida donde el Agente 01 (Quant) y el Agente 04 (Guardián de Riesgo) son 100% deterministas en Python. El LLM solo se invoca en el Agente 03 (Estratega) cuando `setup_score >= 75`, reduciendo el consumo de tokens de API en más de un $90\%$ durante la operación continua 24/7.
- **[WebSocket Binance]:** La URL heredada `wss://fstream.binance.com/ws|/stream` ya no emite `kline` ni `markPrice` (verificado 2026-10-26). Se usan dos conexiones: `/public/stream` (depth20@100ms) y `/market/stream` (kline_15m, kline_1h, markPrice@1s).
- **[LLM — 2026-10-26]:** Proveedor por defecto Gemini (`LLM_PROVIDER=gemini`, `GEMINI_API_KEY` en `.env`); Anthropic sigue disponible (`LLM_PROVIDER=anthropic`, `claude-opus-5-5`). Modelos por agente elegidos por benchmark real (3 escenarios con validación del Guardián): Estratega `gemini-3.5-flash` (todas las respuestas correctas, ~5 s) → respaldo `gemini-3-flash-preview` → `gemini-3.5-flash-lite`; Sentimiento `gemini-3.5-flash-lite` (~1 s, sin thinking). Descartados: `gemini-3.1-pro-preview`/`gemini-4-argon` (cuota 0 en plan gratuito), `gemini-3.8-flash` (sin respuesta en 150 s), flash-lite como Estratega (ignora comisiones al fijar TP). Si toda la cadena falla, el Estratega usa el respaldo determinista (el Guardián sigue validando).
- **[tpmin — REVERTIDO]:** Pasar al Estratega un TP mínimo neto hacía que el Guardián aprobara ~16 operaciones/semana sin ventaja (−3.25 %/semana en backtest). Ahora el Estratega debe usar el SL/TP calibrados y solo puede acercar el TP o elegir HOLD.
- **[Agente 02]:** Capa determinista (funding, OI, L/S) + capa LLM solo en setups: puntúa titulares RSS reales de 24 h (peso 40 %); `headline_risk=EXTREME` con noticias negativas → `PANIC_EVENT`. Google Search grounding descartado: sin cuota en la clave gratuita.
- **[Contabilidad]:** Comisiones de entrada y salida y funding se liquidan en el cierre (`E_{t+1} = E_t + PnL neto`); el PnL no realizado ya descuenta comisión de entrada, comisión de salida estimada y funding acumulado. El slippage está embebido en los precios efectivos y se registra aparte solo como métrica.
- **[s_latencia]:** `σ_1s(mark price) × √0.150 s`, con mínimo `MIN_LATENCY_SLIPPAGE=0.002%` para que nunca sea cero.
- **[Guardián]:** Regla 3 usa riesgo comprometido (pérdida hasta SL) ≤ `MAX_PORTFOLIO_RISK=2%` y tope de apalancamiento nocional `MAX_LEVERAGE=3`. Regla 4: SL entre 0.5 y 4 ATR.
- **[Backtester]:** Señal al cierre de i, entrada en apertura de i+1, SL antes que TP si ambos se tocan, funding histórico real, medio spread fijo 0.5 pb. El Estratega usa su respaldo determinista (0 tokens) para que calibrar sea gratuito.
- **[LIMIT]:** Órdenes LIMIT pasivas en memoria (TTL 60 s, comisión maker); no sobreviven a un reinicio.
- **[ExchangeBroker]:** Hereda del VirtualBroker; SL/TP vigilados desde el proceso (no hay órdenes stop en el exchange). Requiere `pip install ccxt` y no se ha probado con claves reales.
- **[Dependencias]:** `pyarrow` omitido: polars lee/escribe parquet de forma nativa. Versiones verificadas: anthropic 2.3.0, sqlmodel 0.0.48 (exige datetimes con zona → `utcnow()` es UTC aware), polars 2.1.0.
- **[TLS]:** El WebSocket usa `truststore` (almacén de certificados del SO, igual que httpx) para funcionar detrás de proxies TLS corporativos sin desactivar la verificación.
- **[Calibración con validación fuera de muestra — 2026-10-27]:** 6 pares × {15m, 1h, 4h} × 210 combinaciones (umbral, SL, TP). Selección en 2025-04→2026-04 por Sharpe robusto (mediana de celdas vecinas), validación en 2026-04→2026-10 y en 2024-04→2025-04. 15m: pierde en todos los pares. Con break-even a 1.5R: media fuera de muestra +7.5 %, 2/12 pasan las 3 pruebas; sin break-even: +21.9 %, 4/12. Elegidos (ganan en los 3 periodos): DOGE 4h (85, 1.5, 8.0), XRP 4h (60, 1.0, 5.0), SOL 1h (75, 3.0, 8.0). Descartado BNB 1h (win 14 %, DD 34–45 %). Sesgo de selección: 3 de 18 combinaciones; la expectativa real probablemente es menor que la del backtest.
- **[Riesgo — 2026-10-27]:** `MAX_RISK_PER_TRADE=1%` (antes 1.5 %), `MAX_PORTFOLIO_RISK=3%` (una posición por par), `BREAKEVEN_R=0`. Cartera simulada fuera de muestra (80 semanas): media +0.79 %/semana, mediana ≈ 0 %, 48 % semanas positivas, p10 −4.8 %, p90 +7.4 %, drawdown máx 15–18 % (26 % en entrenamiento). Rendimiento sesgado: pocas semanas muy buenas compensan muchas planas o negativas.
- **[Pendiente de validar]:** el filtro HOLD de Gemini no está en el backtest (coste de tokens); en una estrategia con 15–35 % de aciertos puede filtrar los pocos ganadores grandes. El límite de pérdida diaria a nivel cartera tampoco se modela en la simulación conjunta.
- **[Despliegue — 2026-10-27]:** Servidor objetivo: Oracle Cloud Always Free (Ampere A1, Ubuntu 24.04, ARM64). La API exige token cuando `API_TOKEN` está definido (en producción es obligatorio, `REQUIRE_API_TOKEN=1`). El dashboard (servido por el motor o desde GitHub Pages) pide el token y lo guarda en el navegador. `start.sh` escucha solo en 127.0.0.1. La imagen ARM64 se valida en CI porque no hay Docker en el Mac de desarrollo.
- **[Mac como servidor — 2026-10-27]:** Servicio launchd (`./start.sh install-service`): RunAtLoad + KeepAlive (reinicio verificado en ~15 s tras matar el proceso) y `caffeinate -i -s` (impide el reposo por inactividad y, con cargador, el del sistema). El proyecto se movió de `~/Desktop/Nuevo` a `~/escuadron` (con enlace simbólico en el Escritorio) porque la protección de privacidad de macOS impide a los servicios leer el Escritorio (EX_CONFIG 78 / `Operation not permitted`). Con FileVault activo el servicio arranca al iniciar sesión, no antes. Cerrar la tapa del portátil lo duerme igualmente.

