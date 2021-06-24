import os
import boto3
import json

# Custom libraries
from utilities.errors import MalformedRequest, NotFound, Conflict, GameFinished
from utilities.GameState import GameState
from DropTokenSession import DropTokenSession
from utilities.Validation import Validation

# Caching area
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['DATABASE_NAME'])


def lambda_handler(event, _):
    # Give the drop token session handler access to the database and any event details from the request
    dt_session = DropTokenSession(table, event)

    try:
        # GENERAL Validations, these will raise specific errors that will be rendered with the correct status code
        # VALIDATE: that game exists if accessing a resource that requires a game ID
        validate = Validation(event)
        if 'gameId' in event:
            game_info = dt_session.get_game()
            validate.set_game_info(game_info)  # Giving the validation class access to the game data

        # VALIDATE: Player is part of the game
        validate.player_in_game()

        # ROUTES and RESPONSES
        if event['resource'] == '/drop_token':
            # Creating a game
            if event['method'] == 'POST':
                game_id = dt_session.create_game()
                return {
                    'gameId': game_id
                }

            # Showing all games
            elif event['method'] == 'GET':
                games = dt_session.get_active_games()
                return {
                    'games': games
                }

        elif event['resource'] == '/drop_token/{gameId}':
            # Retrieve one single game and all the related information
            if event['method'] == 'GET':
                game_response = {
                    "players": game_info['players'],
                    "state": game_info['state'],
                    "winner": game_info['winner']
                }
                # Per specification, no winner property should exist in an ACTIVE game
                if game_response['state'] == GameState.ACTIVE.val():
                    del game_response['winner']
                return game_response

        elif event['resource'] == '/drop_token/{gameId}/moves':
            # Retrieves an array (all, or a subset) of player moves for a specified game
            if event['method'] == 'GET':
                # VALIDATE if we received the OPTIONAL query string parameters. Both must be present
                if len(event['start']) > 0 and len(event['until']) > 0:
                    validate.unsigned_integer_values(event['start'], event['until'])
                    validate.valid_query_range(event['start'], event['until'])

                    moves = dt_session.retrieve_moves(int(event['start']), int(event['until']))
                # Otherwise, show them all the moves for the game
                else:
                    moves = dt_session.retrieve_moves()

                return {
                    "moves": moves
                }

        elif event['resource'] == '/drop_token/{gameId}/moves/{move_number}':
            # Retrieves a single move
            if event['method'] == 'GET':
                # VALIDATE that we have an unsigned integer path parameter
                validate.unsigned_integer_values(event['move_number'])

                # Repurposing the array of moves, because array slicing will still work here
                move = dt_session.retrieve_moves(int(event['move_number']), int(event['move_number'])+1)
                return move[0]

        elif event['resource'] == '/drop_token/{gameId}/{playerId}':
            # VALIDATE: Game is not in 'DONE' state
            validate.game_is_active()

            # Player is a sore loser or forgot to feed the cat, they are leaving the game, an entry in moves is recorded
            if event['method'] == 'DELETE':
                dt_session.quit_game()
                return

            # Player is making a move!
            elif event['method'] == 'POST':
                # VALIDATE: Move is an unsigned integer
                validate.unsigned_integer_values(event['body']['column'])

                # VALIDATE: Move is between designated column numbers (re-purposing the validator, logic is similar)
                validate.valid_query_range(event['body']['column'], int(game_info['columns'])-1)

                move = dt_session.create_move()
                return move

    # Begin the handling of errors sent from the game session or game
    except MalformedRequest as e:
        raise Exception(json.dumps({
            "reason": "BAD_REQUEST",
            "message": str(e)
        }))
    except NotFound as e:
        raise Exception(json.dumps({
            "reason": "NOT_FOUND",
            "message": str(e)
        }))
    except Conflict as e:
        raise Exception(json.dumps({
            "reason": "CONFLICT",
            "message": str(e)
        }))
    except GameFinished as e:
        raise Exception(json.dumps({
            "reason": "GONE",
            "message": str(e)
        }))
    # General exception case for anything I can't catch, so we don't release important information
    except Exception as e:
        print(str(e))  # Normally would do a log level here
        raise Exception(json.dumps({
            "reason": "EXCEPTION",
            "message": "See logs for details."
        }))
