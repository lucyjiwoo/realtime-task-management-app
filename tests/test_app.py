import json
import pytest


# ──────────────────────────────────────────────────────────────────────────────
# Register
# ──────────────────────────────────────────────────────────────────────────────
class TestRegister:
    def test_register_success(self, client, db_mock):
        db_mock.createUser.return_value = {'success': 1, 'message': 'User created successfully.'}
        response = client.post('/processsignup', data={
            'email': 'newuser@example.com',
            'password': 'password123',
        })
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == 1

    def test_register_duplicate_email(self, client, db_mock):
        db_mock.createUser.return_value = {'success': 0, 'message': 'User already exists.'}
        response = client.post('/processsignup', data={
            'email': 'existing@example.com',
            'password': 'password123',
        })
        data = json.loads(response.data)
        assert data['success'] == 0
        assert 'already exists' in data['message']


# ──────────────────────────────────────────────────────────────────────────────
# Login
# ──────────────────────────────────────────────────────────────────────────────
class TestLogin:
    def test_login_success(self, client, db_mock):
        db_mock.authenticate.return_value = {'success': 1, 'message': 'Authentication success'}
        response = client.post('/processlogin', data={
            'email': 'test@example.com',
            'password': 'password123',
        })
        data = json.loads(response.data)
        assert data['success'] == 1

    def test_login_wrong_password(self, client, db_mock):
        db_mock.authenticate.return_value = {'success': 0, 'message': 'Incorrect Password'}
        response = client.post('/processlogin', data={
            'email': 'test@example.com',
            'password': 'wrongpassword',
        })
        data = json.loads(response.data)
        assert data['success'] == 0
        assert 'Incorrect' in data['message']

    def test_login_user_not_found(self, client, db_mock):
        db_mock.authenticate.return_value = {'success': 0, 'message': 'User not exists.'}
        response = client.post('/processlogin', data={
            'email': 'nobody@example.com',
            'password': 'password123',
        })
        data = json.loads(response.data)
        assert data['success'] == 0


# ──────────────────────────────────────────────────────────────────────────────
# Create Board
# ──────────────────────────────────────────────────────────────────────────────
class TestCreateBoard:
    def test_create_board_success(self, auth_client, db_mock):
        db_mock.createBoards.return_value = {
            'success': 1,
            'message': 'Board created successfully.',
            'board_id': 1,
        }
        response = auth_client.post('/create_board', data={
            'board_name': 'Test Board',
            'members': 'member@example.com',
        }, follow_redirects=False)
        assert response.status_code == 302
        assert '/home' in response.headers['Location']
        db_mock.createBoards.assert_called_once()

    def test_create_board_requires_login(self, client):
        response = client.post('/create_board', data={
            'board_name': 'Test Board',
            'members': 'member@example.com',
        }, follow_redirects=False)
        assert response.status_code == 302
        assert '/login' in response.headers['Location']


# ──────────────────────────────────────────────────────────────────────────────
# Create Card  (SocketIO)
# ──────────────────────────────────────────────────────────────────────────────
class TestCreateCard:
    def test_create_card_success(self, socket_client, db_mock):
        db_mock.createCard.return_value = {
            'success': 1,
            'card_id': 42,
            'message': 'Card created successfully.',
        }
        socket_client.emit('new_card', {
            'board_id': '1',
            'list_id': '1',
            'card_name': 'Test Card',
            'description': 'Test description',
        }, namespace='/board')

        received = socket_client.get_received(namespace='/board')
        card_events = [r for r in received if r['name'] == 'new_card']
        assert len(card_events) == 1
        assert card_events[0]['args'][0]['card_name'] == 'Test Card'
        assert card_events[0]['args'][0]['card_id'] == 42

    def test_create_card_missing_name(self, socket_client):
        socket_client.emit('new_card', {
            'board_id': '1',
            'list_id': '1',
            'card_name': '',
            'description': '',
        }, namespace='/board')

        received = socket_client.get_received(namespace='/board')
        error_events = [r for r in received if r['name'] == 'error']
        assert len(error_events) == 1


# ──────────────────────────────────────────────────────────────────────────────
# Delete Card  (SocketIO)
# ──────────────────────────────────────────────────────────────────────────────
class TestDeleteCard:
    def test_delete_card_success(self, socket_client, db_mock):
        db_mock.query.return_value = []
        socket_client.emit('delete_card', {
            'board_id': '1',
            'card_id': '42',
        }, namespace='/board')

        received = socket_client.get_received(namespace='/board')
        deleted_events = [r for r in received if r['name'] == 'card_deleted']
        assert len(deleted_events) == 1
        assert deleted_events[0]['args'][0]['card_id'] == '42'

    def test_delete_card_missing_id(self, socket_client):
        socket_client.emit('delete_card', {
            'board_id': '1',
        }, namespace='/board')

        received = socket_client.get_received(namespace='/board')
        error_events = [r for r in received if r['name'] == 'error']
        assert len(error_events) == 1
