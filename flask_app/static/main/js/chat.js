$(document).ready(function () {
    const socket = io.connect('/board');

    const pathParts = window.location.pathname.split('/');
    const boardId = pathParts[pathParts.length - 1];
    const currentUser = document.getElementById('user').value;

    // ── Active users ──────────────────────────────────
    window.renderActiveUsers = function () {
        const container = document.getElementById('active-users');
        if (!container) return;
        container.innerHTML = '';
        (window.activeUsers || new Set()).forEach(function (name) {
            const el = document.createElement('div');
            el.className = 'active-user';
            el.innerHTML = '<span class="active-dot"></span>' + name;
            container.appendChild(el);
        });
    };

    // ── Incoming messages ─────────────────────────────
    socket.on('message', function (data) {
        const chat = document.getElementById('chat');
        const p = document.createElement('p');
        const span = document.createElement('span');
        const username = data.msg.split(':')[0];
        const text = data.msg.slice(username.length + 1);
        span.textContent = text;
        p.appendChild(span);
        p.className = data.sender === currentUser ? 'my-message' : 'others-message';
        chat.appendChild(p);
        $('#chat').scrollTop($('#chat')[0].scrollHeight);
    });

    // ── Join / leave notifications ────────────────────
    socket.on('user_joined', function (data) {
        appendStatus(data.user + ' joined');
    });

    socket.on('user_left', function (data) {
        appendStatus(data.user + ' left');
    });

    socket.on('active_users', function (data) {
        window.activeUsers = new Set(data.users);
        window.renderActiveUsers();
    });

    function appendStatus(msg) {
        const chat = document.getElementById('chat');
        const p = document.createElement('p');
        p.className = 'status-msg';
        p.textContent = msg;
        chat.appendChild(p);
        $('#chat').scrollTop($('#chat')[0].scrollHeight);
    }

    // ── Send message on Enter ─────────────────────────
    $('#message-input').on('keypress', function (event) {
        if (event.which === 13) {
            const message = $(this).val().trim();
            if (message) {
                socket.emit('send_message', { msg: message, board_id: boardId });
                $(this).val('');
            }
        }
    });

    // ── Leave button ──────────────────────────────────
    $('.close-chat-btn').on('click', function () {
        socket.emit('left', { board_id: boardId });
        document.getElementById('chat-click').checked = false;
    });

    // ── Chat window open/close ────────────────────────
    $('#chat-click').on('change', function () {
        if ($(this).is(':checked')) {
            window.renderActiveUsers();
        } else {
            socket.emit('left', { board_id: boardId });
        }
    });
});
