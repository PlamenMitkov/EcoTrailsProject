// services/ChatService.js
import APIService from './APIService.js';

class ChatService extends APIService {
    constructor() {
        super(window.location.origin);
        
        // ВАЖНО: Инициализирайте conversationHistory ПЪРВО
        this.conversationHistory = [];
        this.maxHistorySize = 50;
        this.conversationId = null;
        
        // След това добавете interceptors
        this.addRequestInterceptor(async (config) => {
            console.log('🔐 Request interceptor:', config);
            
            const token = localStorage.getItem('auth_token');
            if (token) {
                config.headers.Authorization = `Bearer ${token}`;
            }
            
            return config;
        });
        
        this.addResponseInterceptor(async (response) => {
            console.log('📥 Response interceptor:', response);
            
            if (response && typeof response === 'object') {
                response.receivedAt = new Date().toISOString();
                response.conversationId = this.conversationId;
            }
            
            return response;
        });
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

            // Добавяне към историята
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
        if (!Array.isArray(this.conversationHistory)) {
            console.warn('🔧 Принудителна инициализация на conversationHistory');
            this.conversationHistory = [];
        }

        const entry = {
            type,
            content,
            timestamp: new Date().toISOString(),
            ...metadata
        };

        this.conversationHistory.push(entry);

        // Ограничаване на размера на историята
        if (this.conversationHistory.length > this.maxHistorySize) {
            this.conversationHistory = this.conversationHistory.slice(-this.maxHistorySize);
        }
    }

    getConversationHistory() {
        if (!Array.isArray(this.conversationHistory)) {
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
}

export default ChatService;
