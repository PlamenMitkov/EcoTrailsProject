// app.js
import StateManager from './state/StateManager.js';
import { APIService } from './services/APIService.js';
import ChatService from './services/ChatService.js';
import NotificationService from './services/NotificationService.js';
import BaseComponent from './components/BaseComponent.js';
import ChatComponent from './components/ChatComponent.js';

console.log('BaseComponent loaded:', BaseComponent.name);
let appStateManager = new StateManager();
// ============================================================================
// APPLICATION MANAGER - Главен клас за управление
// ============================================================================
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
            
            // 1. Инициализация на State Manager
            this.stateManager = new StateManager();
            
            // 2. Инициализация на услугите
            await this.initializeServices();
            
            // 3. Инициализация на компонентите
            await this.initializeComponents();
            
            // 4. Настройка на глобални event listeners
            this.setupGlobalEventListeners();
            
            // 5. Зареждане на първоначални данни
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
        
        console.log('✅ Услугите са инициализирани');
    }

    async initializeComponents() {
        console.log('🧩 Инициализация на компонентите...');
        
        // Navigation Component (използваме legacy функциите засега)
        this.initializeLegacyNavigation();
        
        // Chat Component
        const chatContainer = document.querySelector('#chat-slide .content-overlay');
        if (chatContainer) {
            this.components.chat = new ChatComponent(
                chatContainer, 
                this.stateManager, 
                this.services
            );
        }
        
        // Map Component (засега използваме legacy)
        this.initializeLegacyMap();
        
        console.log('✅ Компонентите са инициализирани');
    }

    initializeLegacyNavigation() {
        // Запазваме съществуващата навигационна логика
        const navigationButtons = document.querySelectorAll('.nav-btn');
        const slides = document.querySelectorAll('.slide');

        if (navigationButtons.length === 0 || slides.length === 0) {
            console.warn('⚠️ Липсват навигационни елементи');
            return;
        }

        navigationButtons.forEach(button => {
            button.addEventListener('click', (event) => {
                event.preventDefault();
                const targetSlide = button.getAttribute('data-slide');
                if (targetSlide) {
                    this.navigateToSlide(targetSlide);
                }
            });

            button.addEventListener('keydown', (event) => {
                if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault();
                    const targetSlide = button.getAttribute('data-slide');
                    if (targetSlide) {
                        this.navigateToSlide(targetSlide);
                    }
                }
            });
        });

        // Задаване на първоначален слайд
        this.navigateToSlide('home');
    }

    // В app.js - подобрете initializeLegacyMap функцията
initializeLegacyMap() {
    if (typeof L !== 'undefined') {
        const mapContainer = document.getElementById('map-container');
        if (mapContainer) {
            // Инициализация на картата
            const map = L.map('map-container', {
                center: [42.7339, 25.4858],
                zoom: 7,
                minZoom: 6,
                maxZoom: 18
            });

            // ВАЖНО: Използвайте CDN за tile layer
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '© OpenStreetMap contributors',
                maxZoom: 18
            }).addTo(map);

            // Запазване в state
            this.stateManager.setState('map.instance', map);
            this.stateManager.setState('map.markers', []);
            
            console.log('✅ Карта инициализирана успешно');
            
            // Настройка на map контролите
            this.setupMapControls();
        } else {
            console.error('❌ Map container не е намерен');
        }
    } else {
        console.error('❌ Leaflet не е зареден');
    }
}

    setupMapControls() {
        // Бутон за показване на всички маршрути
        const showAllTrailsBtn = document.getElementById('show-all-trails');
        if (showAllTrailsBtn) {
            showAllTrailsBtn.addEventListener('click', () => {
                this.handleShowAllTrails();
            });
        }

        // Бутон за намиране на потребителското местоположение
        const locateUserBtn = document.getElementById('locate-user');
        if (locateUserBtn) {
            locateUserBtn.addEventListener('click', () => {
                this.handleLocateUser();
            });
        }

        // Бутон за показване на координати от чата
        const showChatLocationsBtn = document.getElementById('show-chat-locations');
        if (showChatLocationsBtn) {
            showChatLocationsBtn.addEventListener('click', () => {
                this.handleShowChatLocations();
            });
        }
    }

    navigateToSlide(slideId) {
        const slides = document.querySelectorAll('.slide');
        const navButtons = document.querySelectorAll('.nav-btn');

        if (!slideId || typeof slideId !== 'string') {
            console.error('❌ Невалиден ID на слайд:', slideId);
            return;
        }

        const targetSlide = document.getElementById(`${slideId}-slide`);
        if (!targetSlide) {
            console.error(`❌ Слайд с ID "${slideId}-slide" не е намерен`);
            return;
        }

        console.log(`🎬 Активиране на слайд: ${slideId}`);

        // Деактивиране на всички слайдове
        slides.forEach(slide => {
            slide.classList.remove('active');
            slide.setAttribute('aria-hidden', 'true');
        });

        // Деактивиране на всички навигационни бутони
        navButtons.forEach(button => {
            button.classList.remove('active');
            button.setAttribute('aria-pressed', 'false');
        });

        // Активиране на целевия слайд
        targetSlide.classList.add('active');
        targetSlide.setAttribute('aria-hidden', 'false');

        // Активиране на съответния навигационен бутон
        const activeButton = document.querySelector(`[data-slide="${slideId}"]`);
        if (activeButton) {
            activeButton.classList.add('active');
            activeButton.setAttribute('aria-pressed', 'true');
        }

        // Sliding background логика
        const slideBg = document.querySelector('.nav-slide-bg');
        const slideNames = ['home', 'about', 'instructions', 'chat', 'map'];
        const slideIndex = slideNames.indexOf(slideId);
        if (slideBg && slideIndex !== -1) {
            slideBg.classList.remove('slide-0', 'slide-1', 'slide-2', 'slide-3', 'slide-4');
            slideBg.classList.add(`slide-${slideIndex}`);
        }

        // Актуализиране на състоянието
        this.stateManager.setState('ui.currentSlide', slideId);

        // Специфични действия за различните слайдове
        this.handleSlideSpecificActions(slideId);
    }

    handleSlideSpecificActions(slideId) {
        switch (slideId) {
            case 'map':
                setTimeout(() => {
                    const map = this.stateManager.getState('map.instance');
                    if (map) {
                        map.invalidateSize();
                    }
                }, 500);
                break;
            case 'chat':
                setTimeout(() => {
                    if (this.components.chat) {
                        this.components.chat.focusInput();
                    }
                }, 500);
                break;
        }
    }

    setupGlobalEventListeners() {
        // Глобални keyboard shortcuts
        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape') {
                this.navigateToSlide('home');
            }
            
            if ((event.ctrlKey || event.metaKey) && event.key === 'k') {
                event.preventDefault();
                this.navigateToSlide('chat');
                setTimeout(() => {
                    this.components.chat?.focusInput();
                }, 300);
            }
        });

        // Window resize
        window.addEventListener('resize', () => {
            const map = this.stateManager.getState('map.instance');
            if (map) {
                map.invalidateSize();
            }
        });
    }

    async loadInitialData() {
        console.log('📊 Зареждане на първоначални данни...');
        
        try {
            // Зареждане на trails данни
            const trails = await this.services.chatService.getTrails();
            this.stateManager.setState('data.trails', trails);
            
            // Добавяне на welcome съобщение в чата
            setTimeout(() => {
                this.components.chat?.addWelcomeMessage();
            }, 1000);
            
        } catch (error) {
            console.error('Грешка при зареждане на данни:', error);
        }
    }

    // Legacy функции за обратна съвместимост
    handleShowAllTrails() {
        console.log('🗺️ Показване на всички маршрути...');
        // Тук ще добавим логиката по-късно
    }

    handleLocateUser() {
        console.log('📍 Намиране на потребителското местоположение...');
        // Тук ще добавим логиката по-късно
    }

    handleShowChatLocations() {
        const coords = this.stateManager.getState('chat.lastCoordinates');
        if (coords && coords.length > 0) {
            this.navigateToSlide('map');
            // Показване на координатите на картата
            this.showMultipleLocationsOnMap(coords);
        } else {
            this.services.notificationService?.show('Няма координати от чата за показване', 'warning');
        }
    }

    // В app.js - поправете тази функция
showMultipleLocationsOnMap(coords) {
    console.log('🗺️ Показване на множество местоположения:', coords);
    
    const map = this.stateManager.getState('map.instance');
    if (!map) {
        console.error('❌ Картата не е инициализирана');
        return;
    }

    // Почистване на съществуващите маркери
    const currentMarkers = this.stateManager.getState('map.markers') || [];
    currentMarkers.forEach(marker => {
        map.removeLayer(marker);
    });

    const bounds = L.latLngBounds();
    const newMarkers = [];

    // ПОПРАВКА: Обработка на координатите
    coords.forEach((locationGroup) => {
        console.log('Обработка на locationGroup:', locationGroup);
        
        if (typeof locationGroup === 'object' && locationGroup !== null) {
            Object.entries(locationGroup).forEach(([name, coord]) => {
                console.log(`Обработка на ${name}:`, coord);
                
                if (coord && coord.lat && coord.lng) {
                    const lat = parseFloat(coord.lat);
                    const lng = parseFloat(coord.lng);
                    
                    if (!isNaN(lat) && !isNaN(lng)) {
                        console.log(`✅ Добавяне на маркер: ${name} at ${lat}, ${lng}`);
                        
                        // ВАЖНО: Създаване на маркер с правилни икони
                        const marker = L.marker([lat, lng], {
                            icon: L.icon({
                                iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
                                shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
                                iconSize: [25, 41],
                                iconAnchor: [12, 41],
                                popupAnchor: [1, -34],
                                shadowSize: [41, 41]
                            })
                        })
                        .bindPopup(`<strong>${name}</strong><br>Координати: ${lat.toFixed(4)}, ${lng.toFixed(4)}`)
                        .addTo(map);
                        
                        newMarkers.push(marker);
                        bounds.extend([lat, lng]);
                        
                        console.log(`✅ Маркер добавен успешно за ${name}`);
                    } else {
                        console.warn(`⚠️ Невалидни координати за ${name}: lat=${lat}, lng=${lng}`);
                    }
                } else {
                    console.warn(`⚠️ Липсват координати за ${name}:`, coord);
                }
            });
        }
    });

    // Запазване на новите маркери
    this.stateManager.setState('map.markers', newMarkers);

    // Центриране на картата
    if (bounds.isValid() && newMarkers.length > 0) {
        map.fitBounds(bounds, { padding: [20, 20] });
        console.log(`✅ Карта центрирана с ${newMarkers.length} маркера`);
    } else if (newMarkers.length === 1) {
        // При един маркер, центрирай директно
        const marker = newMarkers[0];
        map.setView(marker.getLatLng(), 12);
        console.log('✅ Карта центрирана на единичен маркер');
    } else {
        console.warn('⚠️ Няма валидни маркери за показване');
    }

    this.services.notificationService?.show(
        `Показани ${newMarkers.length} местоположения на картата`, 
        'success'
    );
}

    handleInitializationError(error) {
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

    // Публични методи
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

appStateManager.subscribe('chat.lastCoordinates', (coords) => {
    const btn = document.getElementById('show-chat-locations');
    if (btn) {
        if (coords && coords.length > 0) {
            btn.style.display = '';
        } else {
            btn.style.display = 'none';
        }
    }
});

document.getElementById('show-chat-locations')?.addEventListener('click', () => {
    const coords = stateManager.getState('chat.lastCoordinates');
    if (coords && coords.length > 0) {
        // Извикване на функцията за показване на маркери на картата
        if (window.EcoTrailsApp && window.EcoTrailsApp.showMultipleLocationsOnMap) {
            window.EcoTrailsApp.showMultipleLocationsOnMap(coords);
        }
    }
});

// ============================================================================
// ИНИЦИАЛИЗАЦИЯ
// ============================================================================
let app = null;

document.addEventListener('DOMContentLoaded', async function() {
    try {
        app = new ApplicationManager();
        await app.init();
        
        // Експортиране на app за debugging
        window.EcoTrailsApp = app;
        
        // Legacy глобални функции за обратна съвместимост
        window.showMultipleLocationsOnMap = function(coords) {
            app.showMultipleLocationsOnMap(coords);
        };
        
    } catch (error) {
        console.error('Критична грешка при стартиране:', error);
    }
});

// Експортиране за използване в други модули
export { app };
