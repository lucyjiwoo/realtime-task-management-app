import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture(scope='session')
def db_mock():
    mock = MagicMock()
    mock.createTables.return_value = None
    mock.reversibleEncrypt.side_effect = lambda action, data: (
        b'mock_token' if action == 'encrypt' else 'test@example.com'
    )
    return mock


@pytest.fixture(scope='session')
def flask_app(db_mock):
    with patch('flask_app.utils.database.database.database', return_value=db_mock):
        from flask_app import create_app, socketio as sio
        app = create_app(debug=False)
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret-key'
        yield app, sio


@pytest.fixture
def client(flask_app):
    app, _ = flask_app
    with app.test_client() as c:
        yield c


@pytest.fixture
def auth_client(flask_app):
    """Test client with an active login session."""
    app, _ = flask_app
    with app.test_client() as c:
        with c.session_transaction() as sess:
            sess['email'] = b'mock_token'
        yield c


@pytest.fixture
def socket_client(flask_app, auth_client, db_mock):
    """SocketIO test client joined to board room 1."""
    app, sio = flask_app
    sc = sio.test_client(app, flask_test_client=auth_client)
    sc.connect(namespace='/board')
    sc.emit('joined', {'board_id': '1'}, namespace='/board')
    sc.get_received(namespace='/board')  # discard the join status message
    yield sc
    sc.disconnect(namespace='/board')
