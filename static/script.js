document.addEventListener('DOMContentLoaded', function() {
  const sendButton = document.getElementById('send-button');
  const micButton = document.getElementById('mic-button');
  const userInput = document.getElementById('user_input');
  const chatContainer = document.getElementById('chat-container');
  const newSessionButton = document.getElementById('new-session-button');

  // Check for browser support of the Web Speech API
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const recognition = new SpeechRecognition();

  // Configure the Speech Recognition
  recognition.lang = 'id-ID';  // Set the language to Indonesian ('id-ID'), or change to 'en-US' for English
  recognition.interimResults = false; // We only want final results
  recognition.maxAlternatives = 1;

  // Send Button Event Listener
  sendButton.addEventListener('click', function() {
      const userMessage = userInput.value;
      if (userMessage.trim() !== '') {
          addMessageToChat(userMessage, 'user');
          userInput.value = '';

          // Send the message to the server for processing
          fetch('/chat', {
              method: 'POST',
              headers: {
                  'Content-Type': 'application/x-www-form-urlencoded',
              },
              body: `user_input=${encodeURIComponent(userMessage)}&input_method=typing`
          })
          .then(response => response.json())
          .then(data => {
              const assistantMessage = data.assistant_response;

              // Add AI response to the chat
              addMessageToChat(assistantMessage, 'assistant');

              // Speak the AI response using Text-to-Speech
              speakText(assistantMessage);
          })
          .catch(error => {
              console.error('Error:', error);
          });
      }
  });

  // Mic Button Event Listener for Voice Input
  micButton.addEventListener('click', function() {
      recognition.start();  // Start voice recognition

      recognition.onresult = function(event) {
          const voiceInput = event.results[0][0].transcript;
          addMessageToChat(voiceInput, 'user');

          // Send the voice input to the server for processing
          fetch('/', {
              method: 'POST',
              headers: {
                  'Content-Type': 'application/x-www-form-urlencoded',
              },
              body: `user_input=${encodeURIComponent(voiceInput)}&input_method=speaking`
          })
          .then(response => response.json())
          .then(data => {
              const assistantMessage = data.assistant_response;

              // Add AI response to the chat
              addMessageToChat(assistantMessage, 'assistant');

              // Speak the AI response using Text-to-Speech
              speakText(assistantMessage);
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

  // New Session Button Event Listener
  newSessionButton.addEventListener('click', function() {
      // Send a request to start a new session
      fetch('/new_session', {
          method: 'POST'
      })
      .then(response => {
          if (response.ok) {
              // Clear chat container
              chatContainer.innerHTML = '';
              addMessageToChat('Hello, what\'s your name?', 'assistant');
          }
      })
      .catch(error => {
          console.error('Error:', error);
          addMessageToChat('Error starting a new session.', 'assistant');
      });
  });

  function addMessageToChat(message, role) {
    const messageContainer = document.createElement('div');
    messageContainer.classList.add('message-container', role);

    const messageText = document.createElement('div');
    messageText.classList.add('message-text');
    messageText.textContent = message;

    messageContainer.appendChild(messageText);

    // If the message is from the assistant, add the TTS icon
    if (role === 'assistant') {
        const ttsIcon = document.createElement('img');
        ttsIcon.src = 'https://cdn.prod.website-files.com/66c82c1989379c3c6bec8b31/66ceafe488e2211d3fb0ff7e_volume-loud-svgrepo-com.png'; // Example TTS icon
        ttsIcon.alt = 'Play';
        ttsIcon.classList.add('tts-icon');

        // Add an event listener to play the TTS when the icon is clicked
        ttsIcon.addEventListener('click', function() {
            speakText(message);
        });

        messageContainer.appendChild(ttsIcon);
    }

    chatContainer.appendChild(messageContainer);
    chatContainer.scrollTop = chatContainer.scrollHeight; // Auto scroll to the bottom
  }

  // Function to speak text using the SpeechSynthesis API
  function speakText(text) {
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = 'en-US';  // Set the language for TTS; change to 'id-ID' for Indonesian
      speechSynthesis.speak(utterance);
  }
});
