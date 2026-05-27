# Author: Jiwoo Jeong <jeongji7@msu.edu>
from flask import current_app as app
from flask import render_template, redirect, request, session, url_for, send_from_directory
from flask_socketio import SocketIO, emit, join_room, leave_room, close_room, rooms, disconnect
from .utils.database.database import database
import json
import functools
from . import socketio

db = database()
room_users = {}  # board room -> set of usernames currently connected

#######################################################################################
# AUTHENTICATION RELATED
#######################################################################################
def login_required(func):
    @functools.wraps(func)
    def secure_function(*args, **kwargs):
        if "email" not in session:
            return redirect(url_for("login", next=request.url))
        return func(*args, **kwargs)
    return secure_function

def getUser():
	return db.reversibleEncrypt('decrypt', session['email'])  if 'email' in session else 'Unknown'

@app.route('/login')
def login():
	return render_template('login.html', user=getUser())

@app.route('/logout')
def logout():
	session.pop('email', default=None)
	return redirect('/')

@app.route('/processlogin', methods = ["POST","GET"])
def processlogin():
	form_fields = request.form
	email = form_fields.get('email')
	password = form_fields.get('password')
	status = db.authenticate(email, password)
	if status.get("success") == 1:
		session['email'] = db.reversibleEncrypt('encrypt', email)
	return json.dumps(status)

@app.route('/processsignup', methods=['GET', 'POST'])
def processsignup():
    email = request.form['email']
    password = request.form['password']
    status = db.createUser(email, password)
    return json.dumps(status)

#######################################################################################
# 
#######################################################################################
@app.route('/')
def root():
    return redirect('/home')

@app.route('/home')
@login_required
def home():
    email = getUser()
    boards = db.getUserBoards(email)
    return render_template('home.html', user=email, boards=boards)

@app.route("/static/<path:path>")
def static_dir(path):
    return send_from_directory("static", path)

@app.after_request
def add_header(r):
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, public, max-age=0"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    return r
#######################################################################################
# Boards & Lists & Cards related
#######################################################################################

@app.route('/create_board', methods=['POST'])
@login_required
def create_board():
    board_name = request.form['board_name']
    member_emails = request.form.getlist('members')

    creator_email = db.reversibleEncrypt('decrypt', session['email'])

    db.createBoards(board_name, creator_email, member_emails)
    return redirect('/home')

@app.route('/board/<int:board_id>')
@login_required
def view_board(board_id):
    email = getUser()
    # Query the database for the board and its lists
    board = db.query("SELECT * FROM boards WHERE board_id = %s", [board_id])
    lists = db.query("SELECT * FROM lists WHERE board_id = %s", [board_id])
    cards = {}
    for list_item in lists:
        list_id = list_item['list_id']
        cards[list_id] = db.query("SELECT * FROM cards WHERE list_id = %s", [list_id])
        print(f"Cards for list_id {list_id}:", cards[list_id])  # Debug log
    if not board:
        return "Board not found", 404

    # Render the board.html template with the board and its lists
    return render_template('board.html', user=email, board=board[0], lists=lists, cards=cards)

@socketio.on('new_card', namespace='/board')
def new_card(data):
    board_id = data.get('board_id')
    list_id = data.get('list_id')
    card_name = data.get('card_name')
    description = data.get('description', '')

    if not list_id or not card_name:
        emit('error', {'message': 'Invalid data'})
        return

    # Create the card in the database
    result = db.createCard(list_id, card_name, description)
    print("Result:", result)
    if result.get("success"):
        # Broadcast the new card event to all clients in the board
        emit('new_card', {
            'card_id': result['card_id'],
            'list_id': list_id,
            'card_name': card_name,
            'description': description
        }, room=f'board_{board_id}')
    else:
        emit('error', {'message': 'Failed to create card'})


@socketio.on('move_card', namespace='/board')
def move_card(data):
    card_id = data.get('card_id')
    list_id = data.get('list_id')
    board_id = data.get('board_id')

    if not card_id or not list_id:
        emit('error', {'message': 'Invalid data'})
        return

    # Update the card's list in the database
    db.query("UPDATE cards SET list_id = %s WHERE card_id = %s", [list_id, card_id])

    # Broadcast the card move event
    emit('card_moved', {
        'card_id': card_id,
        'list_id': list_id
    }, room=f'board_{board_id}')

@socketio.on('lock_card', namespace='/board')
def lock_card(data):
    card_id = data.get('card_id')
    board_id = data.get('board_id')
    emit('lock_card', {'card_id': card_id, 'user': getUser()}, room=f'board_{board_id}', include_self=False)

@socketio.on('unlock_card', namespace='/board')
def unlock_card(data):
    card_id = data.get('card_id')
    board_id = data.get('board_id')
    emit('unlock_card', {'card_id': card_id}, room=f'board_{board_id}', include_self=False)

@socketio.on('update_card_description', namespace='/board')
def update_card_description(data):
    card_id = data.get('card_id')
    description = data.get('description')
    board_id = data.get('board_id')

    if not card_id or not description:
        emit('error', {'message': 'Invalid data'})
        return

    # Update the card's description in the database
    db.query("UPDATE cards SET description = %s WHERE card_id = %s", [description, card_id])

    # Notify all clients in the board
    emit('card_updated', {
        'card_id': card_id,
        'description': description
    }, room=f'board_{board_id}')


@socketio.on('delete_card', namespace='/board')
def delete_card(data):
    card_id = data.get('card_id')
    board_id = data.get('board_id')

    if not card_id:
        emit('error', {'message': 'Invalid card_id'})
        return

    # Delete the card from the database
    db.query("DELETE FROM cards WHERE card_id = %s", [card_id])

    # Notify all clients in the board
    emit('card_deleted', {'card_id': card_id}, room=f'board_{board_id}')




#######################################################################################
# CHATROOM RELATED
#######################################################################################
@socketio.on("connect", namespace="/board")
def connect_board():
    print("Client connected to /board namespace")

@socketio.on('joined', namespace='/board')
def joined(message):
    board_id = message.get('board_id')
    if not board_id:
        return
    room = f"board_{board_id}"
    join_room(room)

    user = getUser()
    username = user[:user.find("@")] if "@" in user else user

    if room not in room_users:
        room_users[room] = set()
    room_users[room].add(username)

    emit('user_joined', {'user': username}, room=room)
    emit('active_users', {'users': list(room_users[room])}, room=room)

@socketio.on('send_message', namespace='/board')
def send_message(message):
    user = getUser()
    board_id = message.get('board_id')
    room = f"board_{board_id}"
    username = user[:user.find("@")]
    emit('message', {'msg': f"{username}:{message['msg']}",'sender': user}, room=room)

@socketio.on('left', namespace='/board')
def left(message):
    user = getUser()
    board_id = message.get('board_id')
    room = f"board_{board_id}"
    username = user[:user.find("@")] if "@" in user else user

    if room in room_users:
        room_users[room].discard(username)

    emit('user_left', {'user': username}, room=room)
    emit('active_users', {'users': list(room_users.get(room, set()))}, room=room)
    leave_room(room)
