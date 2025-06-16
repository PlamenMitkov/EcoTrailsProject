import BaseComponent from './BaseComponent.js';

class ChatComponent extends BaseComponent {
    constructor(container, stateManager, services) {
        super(container, stateManager, services);
        this.messageContainer = null;
        this.inputElement = null;
        this.sendButton = null;
        this.loadingIndicator = null;
        this.charCounter = null;
        this.form = null;
    }

    async sendMessage(message, context = {}) {
        try {
            console.log('📤 Изпращане на съобщение:', message);
            
            const response = await this.post('/querydata', {
                message: message,
                context: context,
                conversation_id: this.getConversationId()
            });

            console.log('📥 Получен отговор:', response);

            // Добавяне към историята - сега ще работи правилно
            this.addToHistory('user', message);
            this.addToHistory('ai', response.response, response);

            return response;
        } catch (error) {
            console.error('❌ Грешка при изпращане на съобщение:', error);
            throw error;
        }
    }

    addToHistory(type, content, metadata = {}) {
    // Безопасна проверка
    if (!this.conversationHistory) {
        this.conversationHistory = [];
    }
    
    const entry = {
        type,
        content,
        timestamp: new Date().toISOString(),
        ...metadata
    };

    this.conversationHistory.push(entry); // Сега ще работи
        // Ограничаване на размера на историята
        if (this.conversationHistory.length > this.maxHistorySize) {
            this.conversationHistory = this.conversationHistory.slice(-this.maxHistorySize);
        }
    }

    getConversationHistory() {
        // Безопасна проверка
        if (!this.conversationHistory) {
            this.conversationHistory = [];
        }
        return [...this.conversationHistory];
    }

    clearHistory() {
        this.conversationHistory = [];
    }

    getConversationId() {
        if (!this.conversationId) {
            this.conversationId = `conv_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        }
        return this.conversationId;
    }

    async getTrails(filters = {}) {
        return this.get('/trails/all', filters);
    }

    async getTrailById(id) {
        return this.get(`/trails/by_id/${id}`);
    }

    async advancedSearch(criteria) {
        return this.post('/trails/advanced_search', criteria);
    }

    async calculateRoute(startPoint, endPoint) {
        return this.post('/route/calculate', {
            start: startPoint,
            end: endPoint
        });
    }

    render() {
        // Първо опитваме да намерим съществуващи елементи
        this.findExistingElements();
        
        // Ако не намерим елементите, създаваме ги
        if (!this.inputElement || !this.sendButton) {
            this.createChatInterface();
        }

        console.log('Chat elements found:', {
            container: !!this.container,
            messageContainer: !!this.messageContainer,
            inputElement: !!this.inputElement,
            sendButton: !!this.sendButton,
            form: !!this.form
        });
    }

    findExistingElements() {
        // Търсим с множество селектори за максимална съвместимост
        this.messageContainer = this.container.querySelector('.chat-messages') || 
                               this.container.querySelector('#chat-messages') ||
                               this.container.querySelector('.messages') ||
                               this.container.querySelector('[class*="message"]');
        
        this.inputElement = this.container.querySelector('textarea') || 
                           this.container.querySelector('input[type="text"]') ||
                           this.container.querySelector('#user-input') ||
                           this.container.querySelector('[placeholder*="въпрос"]') ||
                           this.container.querySelector('[placeholder*="съобщение"]') ||
                           this.container.querySelector('[placeholder*="chat"]') ||
                           this.container.querySelector('input') ||
                           document.querySelector('textarea') ||
                           document.querySelector('#user-input');
        
        this.sendButton = this.container.querySelector('button[type="submit"]') || 
                         this.container.querySelector('#send-btn') ||
                         this.container.querySelector('.send-btn') ||
                         this.container.querySelector('button') ||
                         document.querySelector('#send-btn') ||
                         document.querySelector('button[type="submit"]');
        
        this.form = this.container.querySelector('form') || 
                   this.container.querySelector('#chat-form') ||
                   document.querySelector('form');

        // Ако все още няма input, опитваме се да го създадем в контейнера
        if (!this.inputElement && this.container) {
            console.log('🔍 Опит за намиране на input в цялата страница...');
            this.inputElement = document.querySelector('textarea') ||
                               document.querySelector('input[type="text"]') ||
                               document.querySelector('#user-input');
        }
    }

    createChatInterface() {
        console.log('🔧 Създаване на chat интерфейс...');
        
        this.container.innerHTML = `
            <div class="chat-container">
                <div class="chat-header">
                    <h2 class="chat-title">EcoTrails AI Асистент</h2>
                    <p class="chat-subtitle">Попитайте ме за екопътеки в България</p>
                </div>
                
                <div class="chat-messages" id="chat-messages">
                    <!-- Съобщенията ще бъдат добавени тук -->
                </div>
                
                <div class="loading-indicator" id="loading-indicator" style="display: none;">
                    <span>AI пише</span>
                    <div class="loading-dots">
                        <div class="dot"></div>
                        <div class="dot"></div>
                        <div class="dot"></div>
                    </div>
                </div>
                
                <form class="chat-input-form" id="chat-form">
                    <div class="input-container">
                        <textarea 
                            id="user-input" 
                            placeholder="Напишете вашия въпрос за екопътеки..."
                            rows="1"
                            maxlength="500"
                        ></textarea>
                        <button type="submit" id="send-btn" class="send-btn">
                            <span>Изпрати</span>
                            <span class="send-icon">📤</span>
                        </button>
                    </div>
                    <div class="input-actions">
                        <span class="char-counter" id="char-counter">0/500</span>
                    </div>
                </form>
            </div>
        `;

        // Повторно намиране на елементите
        this.findExistingElements();
    }

    bindEvents() {
        // Безопасни проверки преди binding
        if (!this.inputElement || !this.sendButton) {
            console.error('❌ Chat елементи не са намерени за binding!');
            console.log('Опит за повторно намиране...');
            
            // Последен опит за намиране
            this.inputElement = this.inputElement || 
                               document.querySelector('textarea') || 
                               document.querySelector('input[type="text"]');
            
            this.sendButton = this.sendButton || 
                             document.querySelector('button[type="submit"]') ||
                             document.querySelector('button');
            
            if (!this.inputElement || !this.sendButton) {
                console.error('❌ Все още няма намерени елементи!');
                return;
            }
        }

        // Form submit event
        if (this.form) {
            this.addEventListener(this.form, 'submit', (e) => {
                e.preventDefault();
                console.log('📝 Form submit triggered');
                this.handleSendMessage();
            });
        }

        // Директен click event на бутона
        this.addEventListener(this.sendButton, 'click', (e) => {
            e.preventDefault();
            console.log('🔘 Send button clicked');
            this.handleSendMessage();
        });

        // Input events
        this.addEventListener(this.inputElement, 'input', (e) => {
            this.handleInputChange(e);
        });

        this.addEventListener(this.inputElement, 'keydown', (e) => {
            this.handleKeyDown(e);
        });

        console.log('✅ Chat events bound successfully');
    }

    async handleSendMessage() {
        if (this.checkDestroyed()) return;

        // КРИТИЧНО: Винаги търси елемента наново
        this.refreshInputElement();

        if (!this.inputElement) {
            console.error('❌ Input element не е намерен!');
            this.showError('Проблем с интерфейса на чата. Моля, презаредете страницата.');
            return;
        }

        const message = this.inputElement.value.trim();
        
        if (!message) {
            this.showWarning('Моля, въведете съобщение');
            return;
        }

        if (message.length > 500) {
            this.showError('Съобщението е твърде дълго');
            return;
        }

        console.log('💬 Потребителско съобщение:', message);

        try {
            // Добавяне на потребителското съобщение
            this.addUserMessage(message);
            
            // Почистване на input
            this.inputElement.value = '';
            this.updateCharCounter();
            
            // Показване на typing индикатор
            this.stateManager.setState('chat.isTyping', true);
            
            console.log('🤖 Изпращане към AI...');
            
            // Изпращане на съобщението
            const response = await this.services.chatService.sendMessage(message);
            
            console.log('🎯 AI отговор получен:', response);
            
            // Добавяне на AI отговора
            this.addAIMessage(response);
            
            // Обработка на координати
            if (response.coords && response.coords.length > 0) {
                this.stateManager.setState('chat.lastCoordinates', response.coords);
            }
            
        } catch (error) {
            console.error('💥 Грешка при изпращане на съобщение:', error);
            this.addErrorMessage('Възникна грешка при обработката на съобщението. Моля, опитайте отново.');
            this.showError('Грешка при свързване със сървъра');
        } finally {
            this.stateManager.setState('chat.isTyping', false);
        }
    }

    // НОВА ФУНКЦИЯ: Обновява референцията към input елемента
    refreshInputElement() {
        // Опитваме се да намерим input елемента с различни методи
        const selectors = [
            '#user-input',
            'textarea',
            'input[type="text"]',
            '[placeholder*="въпрос"]',
            '[placeholder*="съобщение"]',
            'input'
        ];

        for (const selector of selectors) {
            // Първо в контейнера
            let element = this.container.querySelector(selector);
            if (element) {
                this.inputElement = element;
                console.log(`🔄 Input element намерен с селектор: ${selector} (в контейнера)`);
                return;
            }

            // След това в цялата страница
            element = document.querySelector(selector);
            if (element) {
                this.inputElement = element;
                console.log(`🔄 Input element намерен с селектор: ${selector} (в документа)`);
                return;
            }
        }
        
        console.log('🔄 Input element refresh: не е намерен');
    }

    // Останалите методи остават същите...
    subscribeToState() {
        this.subscribe('chat.messages', (messages) => {
            this.renderMessages(messages);
        });

        this.subscribe('chat.isTyping', (isTyping) => {
            this.toggleTypingIndicator(isTyping);
        });

        this.subscribe('chat.lastCoordinates', (coords) => {
            if (coords) {
                this.handleNewCoordinates(coords);
            }
        });
    }

    handleInputChange(event) {
        this.updateCharCounter();
        this.autoResizeTextarea();
    }

    updateCharCounter() {
        if (!this.inputElement) {
            this.refreshInputElement();
        }
        
        if (!this.inputElement) return;
        
        const length = this.inputElement.value.length;
        
        if (!this.charCounter) {
            this.charCounter = this.container.querySelector('.char-counter') ||
                              this.container.querySelector('#char-counter');
            if (!this.charCounter) {
                const inputActions = this.container.querySelector('.input-actions');
                if (inputActions) {
                    this.charCounter = document.createElement('span');
                    this.charCounter.className = 'char-counter';
                    this.charCounter.id = 'char-counter';
                    inputActions.appendChild(this.charCounter);
                }
            }
        }
        
        if (this.charCounter) {
            this.charCounter.textContent = `${length}/500`;
            this.charCounter.className = length > 500 ? 'char-counter error' : 'char-counter';
        }
    }

    autoResizeTextarea() {
        if (!this.inputElement) return;
        
        this.inputElement.style.height = 'auto';
        this.inputElement.style.height = Math.min(this.inputElement.scrollHeight, 120) + 'px';
    }

    handleKeyDown(event) {
        if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
            event.preventDefault();
            this.handleSendMessage();
        }
    }

    toggleTypingIndicator(isTyping) {
        if (this.loadingIndicator) {
            this.loadingIndicator.style.display = isTyping ? 'flex' : 'none';
        }
        
        if (this.sendButton) {
            this.sendButton.disabled = isTyping;
        }
    }

    addUserMessage(content) {
        const messages = this.stateManager.getState('chat.messages') || [];
        const newMessage = {
            id: this.generateMessageId(),
            type: 'user',
            content,
            timestamp: new Date().toISOString()
        };
        
        this.stateManager.setState('chat.messages', [...messages, newMessage]);
    }

    addAIMessage(response) {
    const messages = this.stateManager.getState('chat.messages') || [];
    
    // Опит за извличане на координати от текста ако липсват
    let coords = response.coords || [];
    
    if (!coords.length && response.response) {
        const coordsMatch = response.response.match(/"coords":\s*\[(.*?)\]/s);
        if (coordsMatch) {
            try {
                coords = JSON.parse('[' + coordsMatch[1] + ']');
            } catch (e) {
                console.warn('Не може да парсира координати от текста');
            }
        }
    }
    
    const newMessage = {
        id: this.generateMessageId(),
        type: 'ai',
        content: response.response || response.message,
        coordinates: coords,
        source: response.source || 'AI Assistant',
        timestamp: new Date().toISOString(),
        metadata: {
            trailsFound: response.trails_found,
            conversationStage: response.conversation_stage
        }
    };
    
    this.stateManager.setState('chat.messages', [...messages, newMessage]);
}

    addErrorMessage(content) {
        const messages = this.stateManager.getState('chat.messages') || [];
        const newMessage = {
            id: this.generateMessageId(),
            type: 'error',
            content,
            timestamp: new Date().toISOString()
        };
        
        this.stateManager.setState('chat.messages', [...messages, newMessage]);
    }

    renderMessages(messages) {
        if (!this.messageContainer) {
            this.messageContainer = this.container.querySelector('.chat-messages') ||
                                  this.container.querySelector('#chat-messages');
        }
        
        if (!this.messageContainer) return;

        this.messageContainer.innerHTML = '';
        
        messages.forEach(message => {
            const messageElement = this.createMessageElement(message);
            this.messageContainer.appendChild(messageElement);
        });

        this.scrollToBottom();
    }

    createMessageElement(message) {
        const messageDiv = this.createElement('div', {
            className: `message ${message.type}-message`,
            'data-message-id': message.id
        });

        const contentDiv = this.createElement('div', {
            className: 'message-content',
            textContent: message.content
        });
        messageDiv.appendChild(contentDiv);

        if (message.type === 'ai' && message.source) {
            const metaDiv = this.createElement('div', {
                className: 'message-meta'
            });

            const sourceSpan = this.createElement('span', {
                className: 'source-badge',
                textContent: message.source
            });

            const timestampSpan = this.createElement('span', {
                className: 'message-timestamp',
                textContent: this.formatTimestamp(message.timestamp)
            });

            metaDiv.appendChild(sourceSpan);
            metaDiv.appendChild(timestampSpan);
            messageDiv.appendChild(metaDiv);
        }

        if (message.coordinates && message.coordinates.length > 0) {
            const mapButtonContainer = this.createElement('div', {
                className: 'map-visualization-container'
            });

            const mapButton = this.createElement('button', {
                className: 'map-visualization-button',
                innerHTML: `📍 Покажи ${message.coordinates.length} местоположения на картата`
            });

            this.addEventListener(mapButton, 'click', () => {
                this.showCoordinatesOnMap(message.coordinates);
            });

            mapButtonContainer.appendChild(mapButton);
            messageDiv.appendChild(mapButtonContainer);
        }

        return messageDiv;
    }

    // В ChatComponent.js - подобрете showCoordinatesOnMap
showCoordinatesOnMap(coordinates) {
    console.log('📍 ChatComponent: Показване на координати:', coordinates);
    
    // Преминаване към map слайда
    this.stateManager.setState('ui.currentSlide', 'map');
    
    // Изчакване да се зареди картата
    setTimeout(() => {
        // Извикване на функцията за показване на маркери
        if (window.EcoTrailsApp && window.EcoTrailsApp.showMultipleLocationsOnMap) {
            window.EcoTrailsApp.showMultipleLocationsOnMap(coordinates);
        } else {
            console.error('❌ showMultipleLocationsOnMap функцията не е достъпна');
        }
    }, 500);
    
    this.showSuccess('Преминаване към картата...');
}

    scrollToBottom() {
        if (this.messageContainer) {
            this.messageContainer.scrollTop = this.messageContainer.scrollHeight;
        }
    }

    handleNewCoordinates(coordinates) {
        this.showMapNavigationOption(coordinates);
    }

    showMapNavigationOption(coordinates) {
        if (!this.messageContainer) return;

        const notification = this.createElement('div', {
            className: 'chat-info-message',
            innerHTML: `
                <p>📍 Намерени са ${coordinates.length} местоположения</p>
                <button class="map-navigation-btn">Покажи на картата</button>
            `
        });

        const button = notification.querySelector('.map-navigation-btn');
        this.addEventListener(button, 'click', () => {
            this.showCoordinatesOnMap(coordinates);
            notification.remove();
        });

        this.messageContainer.appendChild(notification);
        this.scrollToBottom();

        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 10000);
    }

    generateMessageId() {
        return `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    formatTimestamp(timestamp) {
        const date = new Date(timestamp);
        return date.toLocaleTimeString('bg-BG', {
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    addWelcomeMessage() {
        this.addAIMessage({
            response: 'Здравейте! 👋 Аз съм вашият интелигентен туристически асистент за екопътеки в България. Как мога да ви помогна днес?',
            source: 'EcoTrails Assistant'
        });
    }

    clearChat() {
        this.stateManager.setState('chat.messages', []);
        this.addWelcomeMessage();
    }

    focusInput() {
        this.refreshInputElement();
        if (this.inputElement) {
            this.inputElement.focus();
        }
    }
}

export default ChatComponent;

