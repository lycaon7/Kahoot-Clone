import socket
import threading

import encryption
import gui

LOCAL_HOST = '127.0.0.1'
PORT = 2110

TIME_PER_QUESTION = 30
LEADERBOARD_TIME = 15


# Creates a new user with the server or authenticates an existing one
def authentication(sock):
    print('Enter existing name and password or if a new user, choose a name and password')
    valid_entry = False
    while not valid_entry:
        new_user = input('If New User enter N else Enter E: ')
        if new_user == 'E' or new_user == 'N':
            valid_entry = True
            sock.sendall(encryption.encrypt(new_user))
        else:
            print('Invalid entry')

    valid_name = False
    while not valid_name:
        name = input("Name: ")
        sock.sendall(encryption.encrypt(name))
        name_check = encryption.decrypt(sock.recv(1024))
        if name_check == 'valid':
            valid_name = True
            print("Your name is valid")
        else:
            print("Invalid Name")

    valid_password = False
    while not valid_password:
        password = input("Password: ")
        sock.sendall(encryption.encrypt(password))
        pass_check = encryption.decrypt(sock.recv(1024))
        if pass_check == 'valid':
            valid_password = True
            print("Logged in successfully")
        else:
            print("Incorrect Password")


question = ''
options = ['', '', '', '']

modes = ['question', 'answer', 'score', 'leaderboard','in lobby']
mode = ''

if __name__ == '__main__':
    # Try to connect to server and terminate if unable
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((LOCAL_HOST, PORT))
    except ConnectionRefusedError:
        sock.close()
        exit('Connection Error')

    connected = True
    authentication(sock)

    # Print quiz subjects and send chosen one to server
    valid_quiz = False
    number_of_quizzes = int(encryption.decrypt(sock.recv(1024)))
    print("The Quizzes are:")
    for i in range(number_of_quizzes):
        print(encryption.decrypt(sock.recv(1024)))
    while not valid_quiz:
        quiz_code = input("Enter quiz code: ")
        sock.sendall(encryption.encrypt(quiz_code))
        quiz_check = encryption.decrypt(sock.recv(1024))
        if quiz_check == 'valid':
            valid_quiz = True
            print("In Quiz")
        else:
            print("Invalid Quiz")

    while connected:
        if mode == 'answer':
            # getting player answer
            gui_thread = threading.Thread(target=gui.open_gui, args=(sock, question, options))
            print("Waiting for all players to answer")
            gui_thread.start()
            gui_thread.join(TIME_PER_QUESTION)

        data = encryption.decrypt(sock.recv(1024))
        if data in modes:
            mode = data
        else:
            if mode == 'in lobby':
                # Waiting for next round
                print(data)
            if mode == 'question':
                # Print question to player
                split = data.split(':')
                question = split[0]
                for i in range(1, len(split)):
                    options[i - 1] = split[i]
            elif mode == 'score':
                # Print solution and score to player
                print(f'The correct answer is: {data}')
                data = encryption.decrypt(sock.recv(1024))
                print(f"You're current score: {data}")
            elif mode == 'leaderboard':
                # Open final leaderboard
                players_scores = []
                for i in range(int(data)):
                    name = encryption.decrypt(sock.recv(1024))
                    score = int(encryption.decrypt(sock.recv(1024)))
                    players_scores.append((name, score))

                leaderboard_thread = threading.Thread(target=gui.open_leaderboard, args=(sock, players_scores))
                leaderboard_thread.start()
                leaderboard_thread.join(LEADERBOARD_TIME)
                connected = False
