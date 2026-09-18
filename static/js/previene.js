// Previene+ JavaScript Interactions

document.addEventListener('DOMContentLoaded', () => {
    // 1. Auto-scroll chat container to bottom
    const chatBox = document.getElementById('chatContainer');
    if (chatBox) {
        chatBox.scrollTop = chatBox.scrollHeight;
        window.scrollTo(0, 0);
    }

    // 2. Chat Form Handling
    const chatForm = document.getElementById('chatForm');
    const chatInput = document.getElementById('chatInput');
    const chatTypingIndicator = document.getElementById('chatTypingIndicator');
    const sendBtn = document.getElementById('sendBtn');
    const userMessageCountBadge = document.getElementById('userMsgCountBadge');

    if (chatForm && chatInput) {
        chatForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const message = chatInput.value.trim();
            if (!message) return;

            // Append user message immediately to UI
            appendUserMessage(message);
            chatInput.value = '';
            chatInput.disabled = true;
            sendBtn.disabled = true;

            // Show typing indicator
            if (chatTypingIndicator) {
                chatTypingIndicator.classList.remove('d-none');
                chatBox.scrollTop = chatBox.scrollHeight;
            }

            try {
                const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
                const response = await fetch('/chatbot/api/send/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken,
                    },
                    body: JSON.stringify({ message: message })
                });

                const data = await response.json();

                if (response.ok && data.success) {
                    appendAssistantMessage(data.assistant_message);
                    if (userMessageCountBadge && data.total_user_messages !== undefined) {
                        userMessageCountBadge.textContent = data.total_user_messages;
                    }
                } else {
                    appendAssistantMessage({
                        content: data.error || "Ocurrió un inconveniente al procesar tu consulta. Por favor, intenta de nuevo.",
                        sources: [],
                        topics: [],
                        created_at: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                    });
                }
            } catch (err) {
                console.error("Chat error:", err);
                appendAssistantMessage({
                    content: "No se pudo establecer conexión con el servidor. Revisa tu conexión a internet o intenta en unos momentos.",
                    sources: [],
                    topics: [],
                    created_at: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                });
            } finally {
                if (chatTypingIndicator) {
                    chatTypingIndicator.classList.add('d-none');
                }
                chatInput.disabled = false;
                sendBtn.disabled = false;
                chatInput.focus();
                chatBox.scrollTop = chatBox.scrollHeight;
            }
        });
    }

    function appendUserMessage(text) {
        if (!chatBox) return;
        const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        const div = document.createElement('div');
        div.className = 'd-flex justify-content-end mb-3';
        div.innerHTML = `
            <div class="chat-bubble chat-bubble-user">
                <div>${escapeHTML(text)}</div>
                <div class="text-end text-white-50 mt-1" style="font-size: 0.72rem;">${timeStr}</div>
            </div>
        `;
        chatBox.appendChild(div);
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    function appendAssistantMessage(msg) {
        if (!chatBox) return;
        const div = document.createElement('div');
        div.className = 'd-flex justify-content-start mb-3';

        let sourcesHtml = '';
        if (msg.sources && msg.sources.length > 0) {
            sourcesHtml = `
                <div class="chat-sources-pill mt-2">
                    <i class="bi bi-shield-check text-primary me-1"></i>
                    <strong>Fuentes validadas:</strong> ${escapeHTML(msg.sources.join(', '))}
                </div>
            `;
        }

        // Format markdown bold & list bullets
        let formattedContent = formatSimpleMarkdown(msg.content);

        div.innerHTML = `
            <div class="chat-bubble chat-bubble-assistant">
                <div class="d-flex align-items-center mb-1 text-primary fw-bold" style="font-size: 0.85rem;">
                    <i class="bi bi-robot me-1"></i> Previene+ (Asistente Educativo)
                </div>
                <div>${formattedContent}</div>
                ${sourcesHtml}
                <div class="text-muted text-end mt-1" style="font-size: 0.72rem;">${msg.created_at || ''}</div>
            </div>
        `;
        chatBox.appendChild(div);
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    function escapeHTML(str) {
        return str.replace(/[&<>'"]/g, 
            tag => ({
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                "'": '&#39;',
                '"': '&quot;'
            }[tag] || tag)
        );
    }

    function formatSimpleMarkdown(text) {
        let escaped = escapeHTML(text);
        // Replace bold **text**
        escaped = escaped.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        // Replace italic *text*
        escaped = escaped.replace(/\*(.*?)\*/g, '<em>$1</em>');
        // Replace newlines
        escaped = escaped.replace(/\n/g, '<br>');
        return escaped;
    }

    // 3. Quick Chips helper
    window.insertQuickPrompt = function(promptText) {
        if (chatInput) {
            chatInput.value = promptText;
            chatInput.focus();
        }
    };
});
