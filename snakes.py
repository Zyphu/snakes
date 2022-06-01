# Snakes
# By Daniel Cumming

# An ASCII text-based terminal game inspired by the classic Snake. 
# It features classic snake singleplayer and a multiplayer mode that can be played through 
# the local network or the internet. Developed using Python and its curses module.

from select import select
import time 
import curses as crs
from collections import deque
from random import randint
from socket import *

#######################################################
# PROGGRAM VARIABLES
#######################################################
#### TERM VARIABLES ###############################
MIN_FIELD_SIZE = 10
TB_CHAR = '-'  # Top/Bottom border
SB_CHAR = '|'  # Side border

#### GAME VARIABLES ###############################
TITLE = ' Evolving Snakes '
MENU = [' Single Player ', ' Create Game Lobby ', ' Join Game ', ' Exit ']
MENU_KEY = {crs.KEY_UP:-1, crs.KEY_DOWN:1, crs.KEY_RIGHT:1, crs.KEY_LEFT:-1}

MIN_HEIGHT, MIN_WIDTH = 10, 20
INIT_SNAKE_SIZE = 4
DEFAULT_DIRECTION = crs.KEY_RIGHT
DIRECTIONS = [crs.KEY_RIGHT, crs.KEY_LEFT, crs.KEY_DOWN, crs.KEY_UP]
DIRECTION_VALUE = {crs.KEY_RIGHT:[0,1], crs.KEY_LEFT:[0,-1], crs.KEY_UP:[-1,0], crs.KEY_DOWN:[1,0]} # y,x
OPPOSITE_DIRECTION = {crs.KEY_UP:crs.KEY_DOWN, crs.KEY_DOWN:crs.KEY_UP, crs.KEY_RIGHT:crs.KEY_LEFT, crs.KEY_LEFT:crs.KEY_RIGHT}

time_delta = 0.1 # how fast snake moves 
food_delta = 4   # how often food appears

COUNTDONW = 3
#######################################################
# Networking
#######################################################
BUFFER_SIZE = 8192  
SERVER_PORT = 12000

class Snake:
    def __init__(self, h, w, y, x, dir):
        self.h, self.w = h-2,w-2
        self.change_dir(dir)
        self.body = [(y-self.dy*i, x-self.dx*i) for i in range(INIT_SNAKE_SIZE)]

    def next_move(self):
        y, x = (self.body[0][0] + self.dy) % self.h, (self.body[0][1] + self.dx) % self.w # wrap around
        if y == 0: y = self.h # wrap around left-top borders
        if x == 0: x = self.w
        return (y,x) # returns coord of next move (y,x)
    
    def change_dir(self, dir):
        self.dir = dir
        self.dy, self.dx = DIRECTION_VALUE[dir]

    def move(self):
        self.body.insert(0, self.next_move())
        self.body.pop()

    def eat(self):
        self.body.insert(0, self.next_move())
        
def check_window_size(stdscr):
    # Get minimum window requirement
    while True:
        h,w = stdscr.getmaxyx()
        if h >= MIN_HEIGHT and w >= MIN_HEIGHT: return h,w
        stdscr.erase()
        draw_border(stdscr,0,0,h,w)
        msg = 'Enlarge Terminal'
        stdscr.addstr(h//2, (w-len(msg))//2, msg)
        stdscr.refresh()
        stdscr.getch()

def countdown(scr):
    h,w = scr.getmaxyx()
    for i in range(COUNTDONW,0,-1):
        scr.erase()
        draw_border(scr,0,0,h,w)
        msg = 'Beginning Match in '+str(i)
        scr.addstr(h-h//2, (w-len(msg))//2, msg)
        scr.refresh()
        time.sleep(1)

def generate_field(stdscr, h, w):
    stdscr.erase()          # clear & refresh main window
    stdscr.refresh()            
    field = crs.newwin(h,w) # generate new window for gamefield
    field.keypad(True)      # make getch() allow for special keys
    field.nodelay(True)     # make getch() non-blocking
    countdown(field)        # display start game prompt
    return field

def draw_field(scr, h, w, snakes, food):
    mx_h,mx_w = scr.getmaxyx()
    scr.erase()
    if w > mx_w: draw_border(scr,0,0,h,mx_w)
    else:        draw_border(scr,0,0,h,w)
    for y,x in food: 
        if y < mx_h and x < mx_w: scr.addstr(y,x,'#')
    for snake in snakes:
        for y, x in snake:
            if y < mx_h and x < mx_w: scr.addstr(y,x,'*')
    scr.refresh()

def create_food(h,w):
    return (randint(2,h-2), randint(2,w-2))

def gameover(scr, msg):
    h,w = scr.getmaxyx()
    scr.erase()
    draw_border(scr,0,0,h,w)
    scr.addstr(h//2, (w-len(msg))//2, msg)
    scr.refresh()
    time.sleep(3)
#######################################################
# Single Player
#######################################################
def single_player(stdscr):
    # create gamefield window
    h, w = check_window_size(stdscr)
    field = generate_field(stdscr, h, w)

    # create player
    key = crs.KEY_RIGHT
    snake = Snake(h, w, h//2, (w-INIT_SNAKE_SIZE)//2, key)
    food = {create_food(h,w)}
    draw_field(field, h, w, [snake.body], food)

    # gameloop
    render_timer, food_timer = time.time(), time.time()
    while True: 
        keystroke = field.getch() 
        if keystroke in DIRECTIONS: key = keystroke
        if (time.time() - render_timer >= time_delta): # update is in order
            # Obtain next move
            if key != OPPOSITE_DIRECTION[snake.dir]: snake.change_dir(key)
            nxt = snake.next_move()
            
            # Handle Collisions
            if nxt in snake.body: break # Game over
            if nxt in food:             # Grow
                snake.eat()
                food.remove(nxt)
            else: snake.move()          # Move

            # Create Food
            if (time.time() - food_timer >= food_delta): 
                food.add(create_food(h,w))
                food_timer = time.time()

            draw_field(field,h,w,[snake.body],food)
            render_timer = time.time()
    gameover(field,'GAME OVER')

#######################################################
# Multiplayer
#######################################################
##############
# Server Side
#############
def server(stdscr, h, w):
    # create server & connection socket
    serverSocket = socket(AF_INET, SOCK_STREAM)         # create IPv4/TCP socket
    serverSocket.bind(('',SERVER_PORT))                 # assign port number to server socket
    serverSocket.listen(1)                              # allows accepting one connection
    connectionSocket, addr = serverSocket.accept()      # accept first client app to connect

    # obtain smallest window & fit
    ch, cw = eval(connectionSocket.recv(BUFFER_SIZE).decode())  # obtain client window size
    h = h if h < ch else ch
    w = w if w < cw else cw
    connectionSocket.send(str((h,w)).encode()) # send gamefield window size
    field =  generate_field(stdscr, h, w)      # generate gamefield
    
    # create gamefield states & send them to client
    food = {create_food(h,w)}; connectionSocket.send(str(food).encode())
    snakes = [
        Snake(h, w, h//2, (w-INIT_SNAKE_SIZE)//4, DEFAULT_DIRECTION),   # player 1
        Snake(h, w, h//2, (w-INIT_SNAKE_SIZE)*3//4, DEFAULT_DIRECTION), # player 2
    ]; connectionSocket.send(str([s.body for s in snakes]).encode())    # send snake coord data

    # render gamestate
    draw_field(field, h, w, [s.body for s in snakes], food)

    # game loop
    keys, ckeys = deque([]), deque([])
    connectionSocket.setblocking(False) # make unblocking
    render_timer, food_timer = time.time(), time.time()
    
    ckey = snakes[1].dir
    while True:
        # Input
        # get host snake moves
        key = field.getch() 
        if key in DIRECTIONS:
            if keys and key != keys[-1] and key != OPPOSITE_DIRECTION[keys[-1]]:    keys.append(key)
            elif key != snakes[0].dir and key != OPPOSITE_DIRECTION[snakes[0].dir]: keys.append(key)
        # get client snake moves
        readable, writable, in_error = select([connectionSocket], [connectionSocket],[connectionSocket])
        if readable:
            ckey = eval(connectionSocket.recv(BUFFER_SIZE))
            if ckey in DIRECTIONS:
                if ckeys and ckey != ckeys[-1] and ckey != OPPOSITE_DIRECTION[ckeys[-1]]: ckeys.append(ckey)
                elif ckey != snakes[1].dir and ckey != OPPOSITE_DIRECTION[snakes[1].dir]: ckeys.append(ckey)

        # Calculation
        if (time.time() - render_timer >= time_delta): # update is in order
            # check for change in direction
            if keys:  snakes[0].change_dir(keys.popleft())
            if ckeys: snakes[1].change_dir(ckeys.popleft())
            # check next moves of both snakes
            nxt, cnxt = [s.next_move() for s in snakes]
            if nxt == cnxt or (nxt in snakes[1].body and cnxt in snakes[0].body) or (nxt in snakes[0].body and cnxt in snakes[1].body):
                connectionSocket.send('TIE GAME'.encode()) 
                gameover(field, 'TIE GAME')
                break
            else:
                # snake collision
                if nxt in snakes[0].body or nxt in snakes[1].body:
                    connectionSocket.send('YOU WON'.encode()) 
                    gameover(field, 'YOU LOST')
                    break
                elif cnxt in snakes[0].body or cnxt in snakes[1].body:
                    connectionSocket.send('YOU LOST'.encode()) 
                    gameover(field, 'YOU WON')
                    break

                # food collision
                # player 1
                if nxt in food:             # Grow
                    snakes[0].eat()
                    food.remove(nxt)
                else: snakes[0].move()      # Move
                # player 2
                if cnxt in food:            # Grow
                    snakes[1].eat()
                    food.remove(cnxt)
                else: snakes[1].move()      # Move

                connectionSocket.send(str([s.body for s in snakes]).encode()) # send snake coord data

                # create food
                if (time.time() - food_timer >= food_delta): 
                    food.add(create_food(h,w))
                    food_timer = time.time()
                    connectionSocket.send(str(food).encode())

                # Send & Render
                draw_field(field, h, w, [s.body for s in snakes], food)
                render_timer = time.time()
        field.addstr(0,0, str(ckey))
        field.refresh()

    connectionSocket.shutdown(SHUT_RDWR)
    connectionSocket.close()
    serverSocket.shutdown(SHUT_RDWR)
    serverSocket.close()        # close server & exit

def create_game_lobby(stdscr):
    h, w = check_window_size(stdscr)

    # create lobby prompt
    stdscr.erase()              # Prepare screen
    draw_border(stdscr,0,0,h,w) # Window Border
    msg = 'Waiting for Opponent'
    stdscr.addstr(h//2, (w-len(msg))//2, msg)
    stdscr.refresh()

    # run server
    server(stdscr, h, w)
##############
# Client Side
#############
def client(stdscr, serverName):
    # check for viable window size
    h, w = check_window_size(stdscr)
    
    # establish connection
    clientSocket = socket(AF_INET, SOCK_STREAM)     # create IPv4/TCP socket
    clientSocket.connect((serverName, SERVER_PORT)) # connect client/server sockets

    # send & recieve window information
    clientSocket.send(str((h,w)).encode())
    h,w = eval(clientSocket.recv(BUFFER_SIZE).decode()) # obtain gamefield window size
    field = generate_field(stdscr, h, w)                # generate gamefield window

    # recieve gamestate info
    food   = eval(clientSocket.recv(BUFFER_SIZE).decode())
    snakes = eval(clientSocket.recv(BUFFER_SIZE).decode())
    key = DEFAULT_DIRECTION

    # render gamestate
    draw_field(field, h, w, snakes, food)

    clientSocket.setblocking(False)
    while True:        
        readable, writable, in_error = select([clientSocket],[clientSocket],[clientSocket])
        if readable:
            msg = clientSocket.recv(BUFFER_SIZE).decode()
            if msg == '': break  # server closed    
            if msg == 'TIE GAME': 
                gameover(field, 'TIE GAME')
                break
            if msg == 'YOU WON':
                gameover(field, 'YOU WON')
                break
            if msg == 'YOU LOST':
                gameover(field, 'YOU LOST')
                break
            data = eval(msg)
            if   type(data) is set:  food   = data
            elif type(data) is list: snakes = data
        draw_field(field, h, w, snakes, food)
            
        # manage input
        keystroke = field.getch()
        # if writable and keystroke in DIRECTIONS and keystroke != key: # and keystroke != OPPOSITE_DIRECTION[key]:
        if keystroke in DIRECTIONS:
            clientSocket.send(str(keystroke).encode())
            field.addstr(0,0, str(keystroke))
            field.refresh()

    clientSocket.shutdown(SHUT_RDWR)
    clientSocket.close()

# Game Search
def join_game_lobby(stdscr):
    msg = 'Enter Lobby IP Address: '
    
    h, w = stdscr.getmaxyx()
    y, x = h//2, (w-len(msg)-15)//2
    
    crs.nocbreak()  # Turn on line buffering
    crs.echo()      # Show input
    while True:
        stdscr.erase()                          # Prepare screen
        draw_border(stdscr,0,0,h,w)             # Window Border
        stdscr.addstr(y,x, msg)                 # Draw Prompt
        stdscr.refresh()
        serverName = stdscr.getstr().decode()   # decode byte object to str
        try:inet_aton(serverName); break        # Validate IP
        except error: msg = 'Please Enter Valid Lobby IP Address: '          
    crs.noecho()
    crs.cbreak()

    client(stdscr, serverName)   
#######################################################
# Main Menu
#######################################################
def print_main(stdscr,selection):  
    h, w = stdscr.getmaxyx()    # Get window height & width
    stdscr.erase()              # Prepare screen
    draw_border(stdscr,0,0,h,w) # Window Border

    stdscr.addstr(0, (w- len(TITLE))//2, TITLE, crs.A_BOLD)             # Add title
    for option, text in enumerate(MENU):                                # Draw menu items
        y, x = (h-len(MENU))//2 + option, (w-len(text))//2              # Center items
        if (selection==option): stdscr.addstr(y,x,text,crs.A_REVERSE)
        else:                   stdscr.addstr(y,x,text)
    stdscr.refresh()                                                    # Refresh

# Draws border from given window's orgin to given height and width
def draw_border(scr, y, x, h, w):
    try:
        scr.addstr(y,x,TB_CHAR*w)
        scr.vline (y+1,x,SB_CHAR, h-2)
        scr.vline (y+1,x+w-1,SB_CHAR, h-2)
        scr.addstr(y+h-1,x,TB_CHAR*w) 
    except crs.error: pass # due to error in addstr advancing cursor when drawing bottom right char

# Initialize settings 
def init(stdscr):
    try:
        stdscr.nodelay(False)       # Makes getch() blocking, that is wait for user input 
        crs.curs_set(False)         # Makes cursor invisible
        # crs.has_colors()          # True if term can display colors
        crs.use_default_colors()    # Allow use of terminal default color/transparency values 
    except crs.error:
        pass

# Main Menu & Game Mode Selection
def main(stdscr):
    # Initiate curses settings
    init(stdscr)    

    # Initiate Main Menu
    selection = 0
    print_main(stdscr, selection)

    # Waits for user input & updates main menu
    GAME_OPTION = { 0: single_player, 1: create_game_lobby, 2: join_game_lobby}
    while True:
        keystroke = stdscr.getch()
        if keystroke in DIRECTIONS:                                   # User Navigation
            selection = (selection + MENU_KEY[keystroke]) % len(MENU) # Selection Highlight code
            print_main(stdscr, selection)                             # Displays menu
        elif keystroke == crs.KEY_RESIZE:
            print_main(stdscr, selection)
        elif keystroke == crs.KEY_ENTER or keystroke in [10,13]:      # User Selection, pressed: Enter, LineFeed, or CarriageReturn
            if selection == len(MENU) - 1: break # Exit game                          
            GAME_OPTION[selection](stdscr) # Enter game mode
            selection = 0                  # reset selection
            print_main(stdscr,selection)   # Re-enter main menu
            time.sleep(0.5)                # allow users to grasp menu change
            crs.flushinp()                 # flushes previous input buffers
            try:   stdscr.nodelay(False)   # Makes getch() blocking, that is wait for user input
            except crs.error: pass 
#######################################################
# Wrapper
#######################################################
# Sets default curses env & resets term upon exit
    # stdscr = crs.initscr()    # creates window covering entire term screen
    # crs.noecho()              # turns of key echo
    # crs.cbreak()              # makes app react to key without requiring Enter key to be pressed
    # stdscr.keypad(True)       # makes curses manages special keys (Arrow Keys, Page, Home, etc...)
crs.wrapper(main)