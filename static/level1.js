document.addEventListener('DOMContentLoaded', function() {
    const sendButton = document.getElementById('send-button');
    const micButton = document.getElementById('mic-button');
    const userInput = document.getElementById('user_input');
    const chatContainer = document.getElementById('chat-container');
    const currentLevel = document.getElementById('current-level').value;


    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();

    recognition.lang = 'id-ID'; 
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    sendButton.addEventListener('click', function() {
        const userMessage = userInput.value;
        if (userMessage.trim() !== '') {
            addMessageToChat(userMessage, 'user');
            userInput.value = '';

            fetch(`/chat/${currentLevel}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: `user_input=${encodeURIComponent(userMessage)}&input_method=typing`
            })
            .then(response => response.json())
            .then(data => {
                const assistantMessage = data.assistant_response;
                addMessageToChat(assistantMessage, 'assistant');
            })
            .catch(error => {
                console.error('Error:', error);
            });
        }
    });

    micButton.addEventListener('click', function() {
        recognition.start();

        recognition.onresult = function(event) {
            const voiceInput = event.results[0][0].transcript;
            addMessageToChat(voiceInput, 'user');

            fetch(`/chat/${currentLevel}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: `user_input=${encodeURIComponent(voiceInput)}&input_method=speaking`
            })
            .then(response => response.json())
            .then(data => {
                const assistantMessage = data.assistant_response;
                addMessageToChat(assistantMessage, 'assistant');
            })
            .catch(error => {
                console.error('Error:', error);
            });
        };

        recognition.onerror = function(event) {
            console.error('Speech recognition error detected: ' + event.error);
            addMessageToChat('Error: ' + event.error, 'assistant');
        };
    });

    function scrollToBottom() {
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    // Call the scroll function after the content is loaded
    scrollToBottom();

    // Add message and update the chat
    function addMessageToChat(message, role) {
        const messageContainer = document.createElement('div');
        messageContainer.classList.add('message-container', role);

        const messageText = document.createElement('div');
        messageText.classList.add('message-text');
        messageText.textContent = message;

        messageContainer.appendChild(messageText);

        if (role === 'assistant') {
            const ttsIcon = document.createElement('img');
            ttsIcon.src = 'https://cdn.prod.website-files.com/66c82c1989379c3c6bec8b31/66ceafe488e2211d3fb0ff7e_volume-loud-svgrepo-com.png';
            ttsIcon.alt = 'Play';
            ttsIcon.classList.add('tts-icon');

            ttsIcon.addEventListener('click', function() {
                speakText(message);
            });

            messageContainer.appendChild(ttsIcon);
        }

        chatContainer.appendChild(messageContainer);
        scrollToBottom();
    }

    function speakText(text) {
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = 'en-US';
        speechSynthesis.speak(utterance);
    }

});
