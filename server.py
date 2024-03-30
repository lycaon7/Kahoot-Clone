import socket
import threading
import time
import json

import encryption
import pandas as pd

# _____________________________________________________________________________________________ #

# Constants
LOCAL_HOST = '127.0.0.1'
PORT = 2110

TIME_PER_QUESTION = 30
SCORE_DELAY = 5
BROADCAST_DELAY = 0.5
LEADERBOARD_DELAY = 20
WAIT_FOR_PLAYERS = 30

# _____________________________________________________________________________________________ #

# Global Variables
lock = threading.Lock()
lobbies = {}
participants = {}
scoreboard = {}
running_quizzes = {}

# Setup lobbies with each their own subject
with open('quiz.json', 'r') as f:
    quiz = json.load(f)
for s in quiz:
    lobbies[s] = []
    participants[s] = []
    running_quizzes[s] = False


def update_csv(name, password):
    names.append(name)
    passwords.append(password)
    df = pd.DataFrame({'names': names, 'passwords': passwords})
    df.to_csv('authentication.csv', index=False)


csv = pd.read_csv('authentication.csv').to_numpy()
names = csv[:, 0].tolist()
passwords = csv[:, 1].tolist()


# _____________________________________________________________________________________________ #

# Support Functions
def authenticate(client_socket):
    # Ask if user is new or existing
    new_user = encryption.decrypt(client_socket.recv(1024))
    # Create new user
    if new_user == 'N':
        valid_name = False
        while not valid_name:
            name = encryption.decrypt(client_socket.recv(1024))
            if name not in names:
                valid_name = True
                client_socket.sendall(encryption.encrypt('valid'))
                password = encryption.decrypt(client_socket.recv(1024))
                client_socket.sendall(encryption.encrypt('valid'))
                update_csv(name, password)
                return name
            else:
                client_socket.sendall(encryption.encrypt('invalid'))
    # Authenticate existing user
    elif new_user == 'E':
        name = encryption.decrypt(client_socket.recv(1024))
        valid_name = False
        while not valid_name:
            if name in names:
                valid_name = True
                client_socket.sendall(encryption.encrypt('valid'))
            else:
                client_socket.sendall(encryption.encrypt('invalid'))
        valid_password = False
        while not valid_password:
            password = encryption.decrypt(client_socket.recv(1024))
            if password == passwords[names.index(name)]:
                valid_password = True
                client_socket.sendall(encryption.encrypt('valid'))
                return name
            else:
                client_socket.sendall(encryption.encrypt('invalid'))


# Broadcast question and options for current question and get participant response
def broadcast_question(participant, subject, question_number, answer, index):
    participant[1].sendall(encryption.encrypt('question'))
    # Send question and options.
    package = quiz.get(subject)[question_number].get('question')
    for option in quiz.get(subject)[question_number].get('options'):
        package += f':{option}'
    participant[1].sendall(encryption.encrypt(package))
    time.sleep(BROADCAST_DELAY)

    # Tell client we are waiting for answer
    participant[1].sendall(encryption.encrypt('answer'))
    time.sleep(BROADCAST_DELAY)

    # Receive their answer.
    data = encryption.decrypt(participant[1].recv(1024))
    elapsed_time = int(encryption.decrypt(participant[1].recv(1024)))
    answer[index] = (data, elapsed_time)


# Broadcast what was the correct answer and player's current score
def broadcast_score_and_correct_answer(participant, score, correct_answer):
    participant[1].sendall(encryption.encrypt('score'))
    time.sleep(BROADCAST_DELAY)
    participant[1].sendall(encryption.encrypt(correct_answer))
    time.sleep(BROADCAST_DELAY)
    participant[1].sendall(encryption.encrypt(str(score)))
    time.sleep(BROADCAST_DELAY)


# Send scores to open player's and display leaderboard
def show_leaderboard(subject, participant):
    global lobbies
    participant[1].sendall(encryption.encrypt('leaderboard'))
    time.sleep(BROADCAST_DELAY)
    names = list(scoreboard.keys())
    participant[1].sendall(encryption.encrypt(str(len(names))))
    time.sleep(BROADCAST_DELAY)
    for i in range(len(names)):
        participant[1].sendall(encryption.encrypt(names[i]))
        time.sleep(BROADCAST_DELAY)
        participant[1].sendall(encryption.encrypt(str(scoreboard[names[i]])))
        time.sleep(BROADCAST_DELAY)
    time.sleep(BROADCAST_DELAY)
    data = encryption.decrypt(participant[1].recv(1024))
    if data == 'exit':
        lobbies.get(subject).pop(lobbies.get(subject).index(participant))


# _____________________________________________________________________________________________ #


# Runs the quiz
def run_quiz(subject):
    global participants
    global scoreboard
    global running_quizzes
    quiz_participants = participants.get(subject)

    for participant in quiz_participants:
        scoreboard[participant[0]] = 0

    for i in range(len(quiz.get(subject))):
        # Send question and a time to all participants and get their answers until time is over
        answers = [('', 30) for i in range(len(quiz_participants))]
        threads = []
        for p, participant in enumerate(quiz_participants):
            # Broadcast question
            question_thread = threading.Thread(target=broadcast_question,
                                               args=(participant, subject, i, answers, p))
            threads.append(question_thread)
            question_thread.start()

        # Wait for clients to answer question
        for thread in threads:
            thread.join()

        # Check if answers are correct and update scoreboard
        for p, participant in enumerate(quiz_participants):
            # Check if the answer is correct.
            if answers[p][0].lower() == quiz.get(subject)[i].get('correct_answer').lower():
                scoreboard[participant[0]] += int(200 * (1 - answers[p][1] / 30) + 800)

        # Broadcast each player's score
        for p, participant in enumerate(quiz_participants):
            score_thread = threading.Thread(target=broadcast_score_and_correct_answer,
                                            args=(participant, scoreboard.get(participant[0]),
                                                  quiz.get(subject)[i].get('correct_answer').lower()))
            score_thread.start()

        # Add a delay to aloy the users to look their score before next question
        time.sleep(SCORE_DELAY)

    threads = []
    # At end of quiz show final leader board
    for participant in quiz_participants:
        leaderboard_thread = threading.Thread(target=show_leaderboard, args=(subject, participant,))
        threads.append(leaderboard_thread)
        leaderboard_thread.start()

    # Wait for all the leaderboards threads to terminate before continuing
    for thread in threads:
        thread.join()

    running_quizzes[subject] = False


# Runs the lobby. Starts quiz and deals with players waiting for next round
def run_lobby(subject):
    global lobbies
    global participants
    global running_quizzes
    in_lobby = []
    waiting = []
    sent_message = []

    while server_running:
        in_lobby = lobbies.get(subject)

        # When we are ready and a quiz isn't already running start the quiz
        if len(in_lobby) >= 2 and not running_quizzes[subject]:
            t = WAIT_FOR_PLAYERS
            while t > 0:
                participants[subject] = in_lobby.copy()
                waiting.clear()
                sent_message.clear()
                for participant in participants[subject]:
                    participant[1].sendall(encryption.encrypt('in lobby'))
                time.sleep(BROADCAST_DELAY)
                for participant in participants[subject]:
                    participant[1].sendall(encryption.encrypt(f'Quiz starting in: {t}'))
                time.sleep(0.5)
                t -= 1
            quiz_thread = threading.Thread(target=run_quiz, args=(subject,))
            quiz_thread.start()
            running_quizzes[subject] = True

        # If clients join the lobby after the quiz is started we tell them to wait
        waiting = list(set(in_lobby) - set(participants[subject]))
        if running_quizzes[subject] and len(waiting) > 0:
            for participant in waiting:
                if participant not in sent_message:
                    participant[1].sendall(encryption.encrypt('in lobby'))
                    time.sleep(BROADCAST_DELAY)
                    participant[1].sendall(encryption.encrypt('Game in progress please wait for next round'))
                    sent_message.append(participant)

    # If server shuts down close all participants
    for participant in in_lobby:
        participant[1].close()

    for participant in in_lobby:
        participant[1].sendall(encryption.encrypt("End of quiz"))
        participant.close()
    in_lobby.clear()


# Authenticates client then adds them to their desired quiz
def handle_client(client_socket, address):
    global lobbies

    name = authenticate(client_socket)

    # Send the client the quiz options
    subjects = list(lobbies.keys())
    client_socket.sendall(encryption.encrypt(str(len(subjects))))
    for subject in subjects:
        client_socket.sendall(encryption.encrypt(subject))
        time.sleep(0.5)

    # Get desired quiz subject from client and connect to that quiz.
    in_quiz = False
    quiz_subject = ''
    while not in_quiz:
        quiz_subject = encryption.decrypt(client_socket.recv(1024))
        if quiz_subject in subjects:
            client_socket.sendall(encryption.encrypt('valid'))
            in_quiz = True
        else:
            client_socket.sendall(encryption.encrypt('invalid'))
    print(f'Client connected!')
    lobbies[quiz_subject].append((name, client_socket))


# Opens lobbies and accepts connections before delegating them to a thread
def main_thread():
    print('Server started. Waiting for connection...')

    # Set up a lobbies to run in all the quizzes parallel
    for subject in list(lobbies.keys()):
        lobby_thread = threading.Thread(target=run_lobby, args=(subject,))
        lobby_thread.start()

    while server_running:
        # Accept Clients connecting to server and parce it on to its own thread for handling
        client_socket, address = server_socket.accept()
        client_thread = threading.Thread(target=handle_client, args=(client_socket, address))
        client_thread.start()

    server_socket.close()


if __name__ == '__main__':
    server_running = True
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((LOCAL_HOST, PORT))
    server_socket.listen()

    try:
        main_thread()
    except KeyboardInterrupt:
        print("Stopping server...")
        server_running = False
