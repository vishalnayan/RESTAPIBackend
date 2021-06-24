from utilities.errors import MalformedRequest
from typing import List


class DropTokenGame(object):
    """
    Class that controls the major components of game logic
    """
    def __init__(self, board_state=None, x=4, y=4):
        # Generate a blank board if none has been created
        self.board_state = self.generate_board(x, y) if not board_state else board_state
        self.row_count = y  # A count of how many rows the board has
        self.column_count = x  # A count of how many columns the board has

        self.current_move = None  # A dict of the column and row position of a dropped token
        self.current_player_token = None  # Identifier for the player, None, 0, or 1; 0 == player 1, 1 == player 2
        self.win_length = 4  # Size of consecutive tokens to determine a win

    def set_player(self, player_token):
        self.current_player_token = player_token

    @staticmethod
    def generate_board(x: int, y: int) -> List[List[None]]:
        """
        List comprehension pythonic way to generate a multi dimensional array
        :param x: unsigned integer
        :param y: unsigned integer
        :return: Should look like this:
        [[None, None, None, None], [None, None, None, None], [None, None, None, None], [None, None, None, None]]
        """
        return [[None for _ in range(x)] for _ in range(y)]

    def set_move(self, column) -> None:
        """
        Enumerate over the reversed board, this will allow us to check the bottom of the column first, and then
        work our way upwards to consider any open spots
        :param column:
        """
        rbs = self.board_state[::-1]  # Reverse board state

        for i, cell in enumerate(rbs):
            if cell[column] is None:  # Found an open spot!
                rbs[i][column] = self.current_player_token  # Set the value in our array based on the player identifier
                row = len(self.board_state) - 1 - i  # Need to reverse the index position to the proper original board
                self.current_move = {
                    'column': column,
                    'row': row
                }
                return

        raise MalformedRequest('Malformed input. Illegal move')

    def get_win_state(self) -> bool:
        """
        This method checks for a win state by exploring the surrounding positions from the last move. It keeps track of
        the consecutive positions in 2 directions until it hits the minimum win condition.
        """

        # Directions to check for, first tuple is vertical checks, 2nd tuple is horizontal checks, 3rd and 4th are
        # the two varying diagonal checks
        for delta_row, delta_col in [(1, 0), (0, 1), (1, 1), (1, -1)]:
            consecutive_moves = 1

            # This loops allows us to switch directions when we hit a boundary.
            for delta in (1, -1):
                # Calculate the direction (positive or negative) for the position
                delta_row *= delta
                delta_col *= delta

                # Compute the next row based on the existing position
                next_row = self.current_move['row'] + delta_row
                next_col = self.current_move['column'] + delta_col

                # Once we have our direction, we will keep incrementing in that direction until we hit a boundary, an
                # opponent's position, or a win condition.
                while 0 <= next_row < self.row_count and 0 <= next_col < self.column_count:
                    # Player token here is the identifier of '1, 0, or None', indicating a specific player or no move
                    if self.board_state[next_row][next_col] == self.current_player_token:
                        consecutive_moves += 1
                    else:
                        break
                    if consecutive_moves == self.win_length:
                        return True

                    # Keep tallying up the counts, and we may revert to the parent 'for' loop to check the other
                    # direction and keep tallying up 'consecutive_moves'
                    next_row += delta_row
                    next_col += delta_col

        return False
