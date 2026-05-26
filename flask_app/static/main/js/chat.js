$(document).ready(function(){
    const socket = io.connect('/board');

    const pathParts = window.location.pathname.split('/'); // Split the URL path by "/"
    const boardId = pathParts[pathParts.length - 1];
    console.log('Board ID sent:', boardId);


    // Handle incoming status updates
    socket.on('status', function(data) {
        let tag = document.createElement("p");
        let text = document.createTextNode(data.msg);
        let element = document.getElementById("chat");
        tag.appendChild(text);
        tag.className = "status-msg";
        element.appendChild(tag);
        $('#chat').scrollTop($('#chat')[0].scrollHeight);
    });

    var currentUser = document.getElementById('user').value;
    // Handle incoming chat messages
    socket.on('message', function(data) {
        let tag = document.createElement("p");
        let text = document.createTextNode(data.msg);
        let element = document.getElementById("chat");
        tag.appendChild(text);
        // Determine the message class based on the sender
        if (data.sender === currentUser) {
            tag.className = "my-message";
        } else {
            tag.className = "others-message";
        }
        element.appendChild(tag);
        $('#chat').scrollTop($('#chat')[0].scrollHeight);
    });

    // Send messages to the server
    $('#message-input').bind('keypress', function(event) {
        if (event.which === 13) { // Enter key
            let message = $(this).val();
            if (message) { // Ensure the message is not empty
                socket.emit('send_message', {'msg': message, board_id: boardId });
                $(this).val(''); // Clear the input field
            }
        }
    });

    // Leave the chat room
    $('.close-chat-btn').bind('click', function() {
        socket.emit('left', { board_id: boardId });
        document.getElementById('chat-click').checked = false;
    });

    $('#chat-click').change(function () {
        if (!$(this).is(':checked')) {
            socket.emit('left', { board_id: boardId });
        }
    });
});

