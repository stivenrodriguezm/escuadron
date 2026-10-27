"""Estado de los 5 agentes y registro de consenso persistente."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import select

from backend.core.database import atomic
from backend.models.ledger import AgentConsensusLog
from backend.models.schemas import AgentStatus

AGENTS = [
    ("01", "Analista Cuantitativo", True),
    ("02", "Analista de Sentimiento", False),
    ("03", "Estratega", False),
    ("04", "Guardián de Riesgo", True),
    ("05", "Ejecutor de Órdenes", True),
]


class Telemetry:
    def __init__(self) -> None:
        self.agents: dict[str, AgentStatus] = {
            aid: AgentStatus(id=aid, name=name, status="En espera", metric="—", deterministic=det)
            for aid, name, det in AGENTS}

    def set_status(self, agent_id: str, status: str, metric: str | None = None,
                   tokens: int = 0) -> None:
        agent = self.agents[agent_id]
        agent.status = status
        if metric is not None:
            agent.metric = metric
        agent.tokens_used += tokens
        agent.last_update = datetime.now(timezone.utc)

    def log(self, agent_id: str, status: str, message: str, tokens: int = 0) -> AgentConsensusLog:
        """Registra una decisión en el historial de consenso (SQLite)."""
        entry = AgentConsensusLog(agent_id=agent_id, status=status,
                                  summary_message=message[:240], token_cost=tokens)
        with atomic() as s:
            s.add(entry)
            s.flush()
            s.refresh(entry)
        return entry

    @staticmethod
    def logs_after(last_id: int, limit: int = 100) -> list[AgentConsensusLog]:
        with atomic() as s:
            rows = s.exec(select(AgentConsensusLog).where(AgentConsensusLog.id > last_id)
                          .order_by(AgentConsensusLog.id.desc()).limit(limit)).all()
            return list(reversed(rows))

    @staticmethod
    def recent(limit: int = 100) -> list[AgentConsensusLog]:
        with atomic() as s:
            rows = s.exec(select(AgentConsensusLog).order_by(AgentConsensusLog.id.desc()).limit(limit)).all()
            return list(reversed(rows))

    def restore_token_totals(self) -> None:
        """Recupera el consumo de tokens acumulado tras un reinicio."""
        with atomic() as s:
            for row in s.exec(select(AgentConsensusLog).where(AgentConsensusLog.token_cost > 0)).all():
                if row.agent_id in self.agents:
                    self.agents[row.agent_id].tokens_used += row.token_cost
