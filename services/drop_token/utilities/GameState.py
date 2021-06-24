from enum import Enum


class GameState(Enum):
    ACTIVE = 'IN_PROGRESS'
    COMPLETE = 'DONE'

    def val(self):
        return self.value
