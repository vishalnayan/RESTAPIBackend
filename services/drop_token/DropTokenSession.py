import uuid
from boto3.dynamodb.conditions import Key, Attr

from utilities.GameState import GameState
from utilities.errors import NotFound, Conflict
from DropTokenGame import DropTokenGame


class DropTokenSession(object):
    """
    Class that handles interactions and transformations from the database
    """
    def __init__(self, db, event):
        self.db = db
        self.event = event
        self.game_data = None

    def create_game(self) -> str:
        """
        Creates a game session with a unique identifier, and the payload that the user submitted. Additional validation
        Could be performed here
        :return: string of game ID
        """
        game_id = str(uuid.uuid4())  # Generate random unique identifier
        self.db.put_item(
            Item={
                'gameId': game_id,
                'state': GameState.ACTIVE.val(),
                'players': self.event['body']['players'],
                'rows': self.event['body']['rows'],
                'columns': self.event['body']['columns'],
                'moves': [],
                'winner': ''
            }
        )
        return game_id

    def get_active_games(self) -> []:
        """
        Retrieves all active games
        Does a table scan (can be slow, but works fine given the requirements)
        In the future if these needed to scale a lot, would need a continuation token / while loop
        :return: Array of game IDs
        """
        # Retrieve results
        response = self.db.scan(
            FilterExpression=Attr('state').eq(GameState.ACTIVE.val())
        )
        # Parse for just game ids
        game_ids = []
        for game in response['Items']:
            game_ids.append(game['gameId'])

        return game_ids

    def get_game(self) -> dict:
        """
        Retrieves the game, and will throw a 404 error if it cannot locate the game ID
        :return: dict of all game data (unparsed)
        """
        try:
            response = self.db.query(
                KeyConditionExpression=Key('gameId').eq(self.event['gameId'])
            )
            self.game_data = response['Items'][0]
            return response['Items'][0]
        except Exception as _:
            raise NotFound("Game not found.")

    def retrieve_moves(self, start: int = None, until: int = None) -> []:
        """
        Retrieves the game moves, with optional query string parameters that can select a subset of moves in the array
        :param start: the starting position of the slice of the moves array
        :param until: the ending position of the slice array
        :return: [] - All moves or subset of moves played
        """
        # Takes a slice of the moves, if start and until are blank, it selects the whole array
        moves = self.game_data['moves'][start:until]
        if len(moves) == 0:
            raise NotFound('No moves found.')

        for item in moves:
            item['column'] = int(item['column'])
        return moves

    def quit_game(self) -> None:
        """
        User selects to quit the game, which posts a move without a column and a QUIT 'type'
        :return: Nothing
        """
        # Append new move to move array (potentially make 'moves' a model)
        self.game_data['moves'].append({
            'type': 'QUIT',
            'player': str(self.event['playerId'])
        })
        # Update game state and moves array
        self.db.update_item(
            Key={'gameId': self.event['gameId']},
            UpdateExpression="set moves=:m, #st=:s",
            ExpressionAttributeValues={
                ':m': self.game_data['moves'],
                ':s': GameState.COMPLETE.val()
            },
            ExpressionAttributeNames={
                "#st": "state"
            }
        )

    def create_move(self):
        """
        Creates a move to be saved into the database. The move is evaluated on whether or not it is the winning move
        :return: {} - Reference to the location of the move (part of a URL to invoke via the API)
        """
        # Retrieve latest move number and player, validate that it is in fact the person's turn
        last_player, num = self.get_latest_move()
        if last_player == self.event['playerId']:
            raise Conflict("It is not this player's turn yet.")

        # Append move to game session data
        self.game_data['moves'].append({
            "type": "MOVE",
            "player": self.event['playerId'],
            "column": self.event['body']['column']
        })

        # Retrieve the resultant state of the move just made
        board_state, winner, state = self.get_win_state()

        # If this is the final move, and a winner hasn't been declared, we will mark the game as DONE
        total_possible_moves = int(self.game_data['columns']) * int(self.game_data['rows'])
        if len(winner) == 0 and num + 1 >= total_possible_moves:
            state = GameState.COMPLETE.val()

        # Update the database accordingly
        self.db.update_item(
            Key={'gameId': self.event['gameId']},
            UpdateExpression="set moves=:m, #st=:s, winner=:w, board_state=:b",
            ExpressionAttributeValues={
                ':m': self.game_data['moves'],
                ':s': state,
                ':w': winner,
                ':b': board_state
            },
            ExpressionAttributeNames={
                "#st": "state"
            }
        )
        return {
            'move': f"{self.event['gameId']}/moves/{num}"
        }

    def get_win_state(self):
        """
        Validates the current state of the board to determine if the board has entered in a win condition
        :return: Tuple - board state, winning player (if any), and game state (i.e. DONE, IN_PROGRESS)
        """
        # Get board array, and set to None so game machine can create it
        board_state = self.game_data['board_state'] if 'board_state' in self.game_data else None

        # Designate the player as either 0 or 1, based on their position in the array
        current_player_token = 0 if self.game_data['players'][0] == self.event['playerId'] else 1

        # Instantiate a model of the game, so we can check for a win state
        dt = DropTokenGame(board_state, int(self.game_data['columns']), int(self.game_data['rows']))
        dt.set_player(current_player_token)
        dt.set_move(self.event['body']['column'])

        # Perform check only if there are the required amount of moves to win
        if len(self.game_data['moves']) >= (len(self.game_data['players']) * dt.win_length) - 1:
            win_state = dt.get_win_state()
        else:
            win_state = False

        return (dt.board_state, self.event['playerId'], GameState.COMPLETE.val()) if win_state is True \
            else (dt.board_state, '', GameState.ACTIVE.val())

    def get_latest_move(self):
        """
        Retrieves the last player to make a move and the total count of moves made
        :return: Tuple - last player ID, current total move count
        """
        count = len(self.game_data['moves'])
        # Check if this is the first move being made
        if count > 0:
            last_player = self.game_data['moves'][count-1]['player']
        else:
            last_player = ''

        return last_player, count
