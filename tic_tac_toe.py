# Tic Tac Toe game
# Project from Python 3 Udemy course

import random
import os


def display_board(board):
    os.system("clear")
    print(board[7] + '|' + board[8] + '|' + board[9])
    print('-----')
    print(board[4] + '|' + board[5] + '|' + board[6])
    print('-----')
    print(board[1] + '|' + board[2] + '|' + board[3])


def player_input():
    """
    OUTPUT = (Player1 marker, Player2 marker)
    """
    marker = ''

    while marker != 'X' and marker != 'O':
        marker = input("\nPlayer1, please pick a marker 'X' or 'O': ").upper()

    if marker == 'X':
        return 'X', 'O'
    else:
        return 'O', 'X'


def place_marker(board, marker, position):
    board[position] = marker


def win_check(board, marker):
    return ((board[1] == board[2] == board[3] == marker) or
            (board[4] == board[5] == board[6] == marker) or
            (board[7] == board[8] == board[9] == marker) or
            (board[1] == board[2] == board[3] == marker) or
            (board[1] == board[4] == board[7] == marker) or
            (board[2] == board[5] == board[8] == marker) or
            (board[3] == board[6] == board[9] == marker) or
            (board[1] == board[5] == board[9] == marker) or
            (board[3] == board[5] == board[7] == marker))


def choose_first():
    players = ['Player1', 'Player2']
    return players[random.randint(0, 1)]


def space_check(board, position):
    return board[position] == ' '


def full_board_check(board):
    for i in range(1, 10):
        if space_check(board, i):
            return False
    return True


def player_choice(turn, board):
    next_position = 0

    while next_position not in range(1, 10) or not space_check(board, next_position):
        next_position = int(input('\n%s, please choose your next move as a number 1-9: ' % turn ))

    return next_position


def replay():
    while True:
        question = input("\nDo you want to play again (yes/no)? ")
        if not (question == 'yes' or question == 'no'):
            continue
        else:
            if question == 'yes':
                return True
            else:
                return False


print('Welcome to TIC TAC TOE')

while True:

    the_board = [' '] * 10
    player1_marker, player2_marker = player_input()

    turn = choose_first()
    print('\n' + turn + ' will go first.')

    start_game = input('\nAre you ready to play? yes or no? ')

    if start_game == 'yes':
        game_on = True
    else:
        game_on = False

    while game_on:

        if turn == 'Player1':
            display_board(the_board)

            next_position = player_choice(turn, the_board)

            place_marker(the_board, player1_marker, next_position)

            if win_check(the_board, player1_marker):
                display_board(the_board)
                print('\nPlayer1 has won the game!')
                game_on = False
            else:
                if full_board_check(the_board):
                    display_board(the_board)
                    print('\nThis is a tie')
                    game_on = False
                else:
                    turn = 'Player2'

        elif turn == 'Player2':
            display_board(the_board)

            next_position = player_choice(turn, the_board)

            place_marker(the_board, player2_marker, next_position)

            if win_check(the_board, player2_marker):
                display_board(the_board)
                print('\nPlayer2 has won the game!')
                game_on = False
            else:
                if full_board_check(the_board):
                    display_board(the_board)
                    print('\nThis is a tie')
                    game_on = False
                else:
                    turn = 'Player1'

    if not replay():
        break
