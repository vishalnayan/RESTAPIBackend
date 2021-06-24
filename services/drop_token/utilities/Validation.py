from utilities.errors import MalformedRequest, NotFound, Conflict, GameFinished
from utilities.GameState import GameState


class Validation(object):
    def __init__(self, event):
        self.event = event
        self.game_info = None

    def set_game_info(self, game_info):
        self.game_info = game_info

    def player_in_game(self):
        if 'playerId' in self.event and self.event['playerId'] not in self.game_info['players']:
            raise NotFound('Player is not part of this game.')

    def game_is_active(self):
        if self.game_info['state'] == GameState.COMPLETE.val():
            raise GameFinished("Game has already been completed, please begin a new one.")

    @staticmethod
    def valid_query_range(start: int, until: int):
        if int(start) > int(until):
            raise MalformedRequest("There was a problem with your request payload.")

    @staticmethod
    def unsigned_integer_values(*values):
        try:
            for value in values:
                if int(value) < 0:
                    raise Exception
        except Exception:
            raise MalformedRequest("There was a problem with your request payload.")