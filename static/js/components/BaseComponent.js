// components/BaseComponent.js
class BaseComponent {
    constructor(container, stateManager, services = {}) {
        this.container = container;
        this.stateManager = stateManager;
        this.services = services;
        this.subscriptions = [];
        this.eventListeners = [];
        this.isDestroyed = false;
        
        this.init();
    }

    init() {
        this.render();
        this.bindEvents();
        this.subscribeToState();
    }

    render() {
        // Трябва да бъде имплементиран от наследниците
        throw new Error('render() метод трябва да бъде имплементиран');
    }

    bindEvents() {
        // Опционален - за специфични event listeners
    }

    subscribeToState() {
        // Опционален - за абониране за промени в състоянието
    }

    // Помощен метод за абониране с автоматично почистване
    subscribe(path, callback) {
        const unsubscribe = this.stateManager.subscribe(path, callback);
        this.subscriptions.push(unsubscribe);
        return unsubscribe;
    }

    // Помощен метод за добавяне на event listeners с автоматично почистване
    addEventListener(element, event, handler, options = {}) {
        element.addEventListener(event, handler, options);
        this.eventListeners.push({ element, event, handler, options });
    }

    // Създаване на DOM елемент
    createElement(tag, attributes = {}, children = []) {
        const element = document.createElement(tag);
        
        Object.entries(attributes).forEach(([key, value]) => {
            if (key === 'className') {
                element.className = value;
            } else if (key === 'innerHTML') {
                element.innerHTML = value;
            } else if (key === 'textContent') {
                element.textContent = value;
            } else if (key.startsWith('data-')) {
                element.setAttribute(key, value);
            } else {
                element[key] = value;
            }
        });

        children.forEach(child => {
            if (typeof child === 'string') {
                element.appendChild(document.createTextNode(child));
            } else if (child instanceof Node) {
                element.appendChild(child);
            }
        });

        return element;
    }

    // Намиране на елемент в контейнера
    find(selector) {
        return this.container.querySelector(selector);
    }

    findAll(selector) {
        return this.container.querySelectorAll(selector);
    }

    // Показване на грешка
    showError(message, duration = 5000) {
        this.services.notificationService?.show(message, 'error', duration);
    }

    // Показване на успех
    showSuccess(message, duration = 3000) {
        this.services.notificationService?.show(message, 'success', duration);
    }

    // Показване на предупреждение
    showWarning(message, duration = 4000) {
        this.services.notificationService?.show(message, 'warning', duration);
    }

    // Унищожаване на компонента
    destroy() {
        if (this.isDestroyed) return;

        // Почистване на subscriptions
        this.subscriptions.forEach(unsubscribe => unsubscribe());
        this.subscriptions = [];

        // Почистване на event listeners
        this.eventListeners.forEach(({ element, event, handler, options }) => {
            element.removeEventListener(event, handler, options);
        });
        this.eventListeners = [];

        // Почистване на DOM
        if (this.container && this.container.parentNode) {
            this.container.innerHTML = '';
        }

        this.isDestroyed = true;
    }

    // Проверка дали компонентът е унищожен
    checkDestroyed() {
        if (this.isDestroyed) {
            console.warn('Опит за използване на унищожен компонент');
            return true;
        }
        return false;
    }
}

export default BaseComponent;
