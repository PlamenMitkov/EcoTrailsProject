// app/ApplicationManager.js
import StateManager from './state/StateManager.js';
import ChatService from './services/ChatService.js';
import { APIService } from './services/APIService.js';
import ChatComponent from './components/ChatComponent.js';
import NavigationComponent from './components/NavigationComponent.js';
import NotificationService from './services/NotificationService.js';

class ApplicationManager {
    constructor() {
        this.stateManager = null;
        this.services = {};
        this.components = {};
        this.isInitialized = false;
    }

    async init() {
        try {
            console.log('🚀 Инициализация на EcoTrails приложението...');
            
            // Инициализация на State Manager
            this.stateManager = new StateManager();
            
            // Инициализация на услугите
            await this.initializeServices();
            
            // Инициализация на компонентите
            await this.initializeComponents();
            
            // Настройка на глобални event listeners
            this.setupGlobalEventListeners();
            
            // Зареждане на първоначални данни
            await this.loadInitialData();
            
            this.isInitialized = true;
            console.log('✅ Приложението е успешно инициализирано');
            
        } catch (error) {
            console.error('❌ Грешка при инициализация:', error);
            this.handleInitializationError(error);
        }
    }

    async initializeServices() {
        console.log('🔧 Инициализация на услугите...');
        
        // API Service
        this.services.apiService = new APIService();
        
        // Chat Service
        this.services.chatService = new ChatService();
        
        // Notification Service
        this.services.notificationService = new NotificationService();
        
        // Map Service (ще създадем по-късно)
        // this.services.mapService = new MapService();
        
        console.log('✅ Услугите са инициализирани');
    }

    async initializeComponents() {
        console.log('🧩 Инициализация на компонентите...');
        
        // Navigation Component
        const navContainer = document.querySelector('.circuit-navigation');
        if (navContainer) {
            this.components.navigation = new NavigationComponent(
                navContainer, 
                this.stateManager, 
                this.services
            );
        }
        
        // Chat Component
        const chatContainer = document.querySelector('#chat-slide .content-overlay');
        if (chatContainer) {
            this.components.chat = new ChatComponent(
                chatContainer, 
                this.stateManager, 
                this.services
            );
        }
        
        // Map Component (ще създадем по-късно)
        const mapContainer = document.querySelector('#map-slide .content-overlay');
        if (mapContainer) {
            // this.components.map = new MapComponent(mapContainer, this.stateManager, this.services);
        }
        
        console.log('✅ Компонентите са инициализирани');
    }

    setupGlobalEventListeners() {
        // Глобални keyboard shortcuts
        document.addEventListener('keydown', (event) => {
            this.handleGlobalKeydown(event);
        });
        
        // Window resize
        window.addEventListener('resize', () => {
            this.handleWindowResize();
        });
        
        // Before unload
        window.addEventListener('beforeunload', () => {
            this.cleanup();
        });
    }

    async loadInitialData() {
        console.log('📊 Зареждане на първоначални данни...');
        
        try {
            // Зареждане на trails данни
            const trails = await this.services.chatService.getTrails();
            this.stateManager.setState('data.trails', trails);
            
            // Добавяне на welcome съобщение в чата
            this.components.chat?.addWelcomeMessage();
            
        } catch (error) {
            console.error('Грешка при зареждане на данни:', error);
        }
    }

    handleGlobalKeydown(event) {
        // Escape key - затваряне на модали, връщане към home
        if (event.key === 'Escape') {
            this.stateManager.setState('ui.currentSlide', 'home');
        }
        
        // Ctrl/Cmd + K - фокус върху chat input
        if ((event.ctrlKey || event.metaKey) && event.key === 'k') {
            event.preventDefault();
            this.stateManager.setState('ui.currentSlide', 'chat');
            setTimeout(() => {
                this.components.chat?.focusInput();
            }, 300);
        }
    }

    handleWindowResize() {
        // Уведомяване на компонентите за resize
        if (this.components.map) {
            this.components.map.handleResize();
        }
    }

    handleInitializationError(error) {
        // Показване на fallback UI
        document.body.innerHTML = `
            <div style="
                display: flex; 
                align-items: center; 
                justify-content: center; 
                height: 100vh; 
                background: linear-gradient(135deg, #1e293b, #334155);
                color: white;
                font-family: system-ui;
                text-align: center;
                padding: 2rem;
            ">
                <div>
                    <h1>⚠️ Грешка при зареждане</h1>
                    <p>Възникна проблем при инициализацията на приложението.</p>
                    <button onclick="window.location.reload()" style="
                        background: #3b82f6;
                        color: white;
                        border: none;
                        padding: 0.75rem 1.5rem;
                        border-radius: 0.5rem;
                        cursor: pointer;
                        margin-top: 1rem;
                    ">
                        Опитай отново
                    </button>
                </div>
            </div>
        `;
    }

    cleanup() {
        console.log('🧹 Почистване на ресурсите...');
        
        // Унищожаване на компонентите
        Object.values(this.components).forEach(component => {
            if (component && typeof component.destroy === 'function') {
                component.destroy();
            }
        });
        
        // Изчистване на state manager
        if (this.stateManager) {
            this.stateManager.reset();
        }
    }

    // Публични методи за външно управление
    navigateToSlide(slideId) {
        this.stateManager.setState('ui.currentSlide', slideId);
    }

    showNotification(message, type = 'info', duration = 3000) {
        this.services.notificationService?.show(message, type, duration);
    }

    getState(path) {
        return this.stateManager?.getState(path);
    }

    setState(path, value) {
        return this.stateManager?.setState(path, value);
    }
}

export default ApplicationManager;
