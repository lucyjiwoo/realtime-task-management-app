
document.addEventListener('DOMContentLoaded', () => {
    let draggedCard = null;
    const socket = io.connect('/board');
    const pathParts = window.location.pathname.split('/');
    const boardId = pathParts[pathParts.length - 1];

    window.activeUsers = new Set();
    window.boardSocket = socket;

    socket.emit('joined', { board_id: boardId });

    socket.on('active_users', function(data) {
        window.activeUsers = new Set(data.users);
        if (typeof window.renderActiveUsers === 'function') {
            window.renderActiveUsers();
        }
    });

    socket.on('user_joined', function(data) {
        window.activeUsers.add(data.user);
        if (typeof window.renderActiveUsers === 'function') {
            window.renderActiveUsers();
        }
    });

    socket.on('user_left', function(data) {
        window.activeUsers.delete(data.user);
        if (typeof window.renderActiveUsers === 'function') {
            window.renderActiveUsers();
        }
    });

    // Drag and drop
    document.addEventListener('dragstart', (e) => {
        if (e.target.classList.contains('card')) {
            if (e.target.classList.contains('locked')) {
                // Prevent dragging
                e.preventDefault();
                return;
            }

            draggedCard = e.target;
            e.dataTransfer.setData('text/plain', draggedCard.dataset.cardId);
            draggedCard.classList.add('dragging');
        }
    });

    document.addEventListener('dragend', (e) => {
        if (e.target.classList.contains('card')) {
            e.target.classList.remove('dragging');
            draggedCard = null;
        }
    });

    document.addEventListener('dragover', (e) => {
        if (e.target.classList.contains('list-section') || e.target.closest('.list-section')) {
            e.preventDefault(); // Allow drop
            e.dataTransfer.dropEffect = 'move';
        }
    });

    document.addEventListener('drop', (e) => {
        if (e.target.classList.contains('list-section') || e.target.closest('.list-section')) {
            e.preventDefault();

            if (!draggedCard) return;

            const listSection = e.target.closest('.list-section');
            const cardsContainer = listSection.querySelector('.cards');

            if (cardsContainer) {
                // Move card visually
                cardsContainer.appendChild(draggedCard);

                // Emit move_card event to server
                const listId = listSection.dataset.listId;
                socket.emit('move_card', {
                    board_id: boardId,
                    card_id: draggedCard.dataset.cardId,
                    list_id: listId,
                });
            }
        }
    });


    // Create a new card
    document.querySelectorAll('.create-card').forEach(form => {
        form.addEventListener('submit', (e) => {
            e.preventDefault();
            const formData = new FormData(form);
            const listId = form.querySelector('input[name="list_id"]').value;

            socket.emit('new_card', {
                board_id: boardId,
                list_id: listId,
                card_name: formData.get('card_name'),
                description: formData.get('description'),
            });

            form.reset(); // Reset form after submission
        });
    });


    // Handle real-time card creation

    socket.on('new_card', function(data) {
        console.log('New card event received:', data);

        const list = document.querySelector(`[data-list-id='${data.list_id}'] .cards`);
        if (list) {
            const card = document.createElement('div');
            card.className = 'card';
            card.draggable = true;
            card.dataset.cardId = data.card_id;
            card.innerHTML = `
                <p class="card-name">${data.card_name}</p>
                <textarea class="card-description" disabled>${data.description}</textarea>
                <div class="btns">
                    <button class="edit-btn">Edit</button>
                    <button class="delete-btn">Delete</button>
                </div>
            `;
            list.appendChild(card);
        }
    });

    // Handle real-time card movement
    socket.on('card_moved', function(data) {
        const card = document.querySelector(`.card[data-card-id='${data.card_id}']`);
        const newList = document.querySelector(`[data-list-id='${data.list_id}'] .cards`);
        if (card && newList) {
            newList.appendChild(card); // Move card visually
        }
    });

    // Handle real-time card deletion
    document.addEventListener('click', (e) => {
        if (e.target.classList.contains('delete-btn')) {
            const card = e.target.closest('.card');
            const cardId = card.dataset.cardId;

            socket.emit('delete_card', {
                board_id: boardId,
                card_id: cardId,
            });
        }
    });

    socket.on('card_deleted', function(data) {
        const card = document.querySelector(`.card[data-card-id='${data.card_id}']`);
        if (card) {
            card.remove(); // Remove card
        }
    });

    // Handle real-time card editing
    document.addEventListener('click', (e) => {
        if (e.target.classList.contains('edit-btn')) {
            const card = e.target.closest('.card');
            const descriptionBox = card.querySelector('.card-description');
            const editBtn = e.target;
            const cardId = card.dataset.cardId;

            if (editBtn.textContent === 'Edit') {
                socket.emit('lock_card', { card_id: cardId, board_id: boardId });
                card.classList.add('locked');
                descriptionBox.disabled = false;
                descriptionBox.focus();
                editBtn.textContent = 'Save';
            } else if (editBtn.textContent === 'Save') {
                socket.emit('unlock_card', { card_id: cardId, board_id: boardId });
                card.classList.remove('locked');
                const updatedDescription = descriptionBox.value;

                socket.emit('update_card_description', {
                    card_id: cardId,
                    board_id: boardId,
                    description: updatedDescription,
                });

                descriptionBox.disabled = true;
                editBtn.textContent = 'Edit';
            }
        }
    });

    // Handle real-time card description updates
    socket.on('card_updated', function(data){
        const card = document.querySelector(`.card[data-card-id='${data.card_id}']`);
        if (card) {
            const descriptionBox = card.querySelector('.card-description');
            descriptionBox.value = data.description; // Update description visually
        }
    });

    // Handle card lock/unlock
    
    socket.on('lock_card', function(data) {
        const card = document.querySelector(`.card[data-card-id='${data.card_id}']`);
        if (card) {
            card.classList.add('locked');
            card.querySelector('.card-description').disabled = true;
            card.querySelector('.edit-btn').disabled = true;
        }
    });

    socket.on('unlock_card', function(data) {
        const card = document.querySelector(`.card[data-card-id='${data.card_id}']`);
        if (card) {
            card.classList.remove('locked');
            card.querySelector('.edit-btn').disabled = false;
        }
    });
});