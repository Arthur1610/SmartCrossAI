from enum import StrEnum


class Phase(StrEnum):
    IDLE = "INATIVA"
    CONFIRMING = "DETECÇÃO"
    ACTIVE = "ATIVA"
    HOLDING = "AGUARDANDO DESATIVAÇÃO"


class Lighting:
    def __init__(self):
        self.phase = Phase.IDLE
        self.since = 0.0
        self.active_since = None

    def update(self, present, now, confirmation, hold):
        if present:
            if self.phase == Phase.IDLE:
                self.phase, self.since = Phase.CONFIRMING, now
            elif self.phase == Phase.CONFIRMING and now - self.since >= confirmation:
                self.phase, self.active_since = Phase.ACTIVE, now
                return "ativacao"
            elif self.phase == Phase.HOLDING:
                self.phase = Phase.ACTIVE
        elif self.phase == Phase.CONFIRMING:
            self.phase = Phase.IDLE
        elif self.phase in (Phase.ACTIVE, Phase.HOLDING):
            if self.phase == Phase.ACTIVE:
                self.phase, self.since = Phase.HOLDING, now
            if now - self.since >= hold:
                self.phase, self.active_since = Phase.IDLE, None
                return "desativacao"
        return None
