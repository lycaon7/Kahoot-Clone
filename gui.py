import time
from tkinter import *

import encryption

TIME_PER_QUESTION = 30
BROADCAST_DELAY = 0.5

gui_alive = False
to_send = ''
t = TIME_PER_QUESTION
elapsed_time = TIME_PER_QUESTION


# Open the quiz GUI
def open_gui(client_socket, question, options):
    global t
    global gui_alive
    root = Tk()
    root.title("GUI")
    gui_alive = True
    t = TIME_PER_QUESTION

    time_var = StringVar()
    time_var.set(str(TIME_PER_QUESTION))
    timer_label = Label(root, textvariable=time_var, height=5, width=10)
    timer_label.pack()

    question_label = Label(root, text=question, height=5, width=50)
    question_label.pack()

    frame = Frame(root)
    frame.pack()

    # Timer display during quiz
    # Terminate gui when timer ends and send an empty answer to the server
    def timer():
        global gui_alive
        global to_send
        global t
        while t > 0:
            time_var.set(str(t))
            root.update()
            time.sleep(1)
            t -= 1
        client_socket.send(encryption.encrypt(to_send))
        time.sleep(BROADCAST_DELAY)
        client_socket.send(encryption.encrypt(str(elapsed_time)))
        if gui_alive:
            gui_alive = False
            root.destroy()

    # When button is clicked send the answer to the server and terminate the gui
    def on_button_click(button_text):
        global gui_alive
        global to_send
        global elapsed_time
        to_send = button_text
        elapsed_time = TIME_PER_QUESTION - t
        if gui_alive:
            gui_alive = False
            root.destroy()

    button1 = Button(frame, text=options[0], height=5, width=30, bg="blue", fg="white",
                     command=lambda: on_button_click(options[0]))
    button1.grid(row=0, column=0)

    button2 = Button(frame, text=options[1], height=5, width=30, bg="red", fg="white",
                     command=lambda: on_button_click(options[1]))
    button2.grid(row=0, column=1)

    button3 = Button(frame, text=options[2], height=5, width=30, bg="green", fg="black",
                     command=lambda: on_button_click(options[2]))
    button3.grid(row=1, column=0)

    button4 = Button(frame, text=options[3], height=5, width=30, bg="yellow", fg="black",
                     command=lambda: on_button_click(options[3]))
    button4.grid(row=1, column=1)

    timer()


# Open the leaderboard GUI
def open_leaderboard(socket, players_scores):
    # Exit quiz on button press
    def exit_quiz():
        socket.sendall(encryption.encrypt('exit'))
        socket.close()
        root.destroy()

    root = Tk()
    root.title("Leaderboard")

    frame = Frame(root)
    frame.pack()

    # Sort players_scores in descending order of scores
    sorted_players_scores = sorted(players_scores, key=lambda x: x[1], reverse=True)

    for i, (player, score) in enumerate(sorted_players_scores):
        label = Label(frame, text=f"{i + 1}. {player}: {score}")
        label.pack()

    # Add an exit button
    exit_button = Button(root, text='Exit', command=exit_quiz)
    exit_button.pack()

    root.mainloop()
