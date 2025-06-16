// state/StateManager.js
class StateManager {
    constructor() {
        this.state = this.getInitialState();
        this.listeners = new Map();
        this.middleware = [];
        this.history = [];
        this.maxHistorySize = 50;
    }

    getInitialState() {
        return {
            ui: {
                currentSlide: 'home',
                isLoading: false,
                notifications: [],
                theme: 'light'
            },
            chat: {
                messages: [],
                isTyping: false,
                lastCoordinates: null,
                conversationId: null
            },
            map: {
                center: [42.7339, 25.4858],
                zoom: 7,
                markers: [],
                selectedTrail: null,
                userLocation: null,
                activeFilters: {}
            },
            data: {
                trails: [],
                searchResults: [],
                cache: new Map(),
                lastFetch: null
            },
            user: {
                preferences: {},
                location: null,
                favoriteTrails: []
            }
        };
    }

    // Абониране за промени в състоянието
    subscribe(path, callback) {
        if (!this.listeners.has(path)) {
            this.listeners.set(path, new Set());
        }
        this.listeners.get(path).add(callback);

        // Връщане на функция за отписване
        return () => {
            const pathListeners = this.listeners.get(path);
            if (pathListeners) {
                pathListeners.delete(callback);
                if (pathListeners.size === 0) {
                    this.listeners.delete(path);
                }
            }
        };
    }

    // Задаване на стойност в състоянието
    setState(path, value, options = {}) {
        const oldValue = this.getState(path);
        
        // Запазване в историята
        if (!options.skipHistory) {
            this.addToHistory({
                type: 'SET_STATE',
                path,
                oldValue,
                newValue: value,
                timestamp: new Date().toISOString()
            });
        }

        // Прилагане на middleware
        const processedValue = this.applyMiddleware('setState', {
            path,
            value,
            oldValue,
            options
        });

        // Задаване на стойността
        this.setNestedProperty(this.state, path, processedValue.value);

        // Известяване на слушателите
        this.notifyListeners(path, processedValue.value, oldValue);

        return processedValue.value;
    }

    // Получаване на стойност от състоянието
    getState(path) {
        if (!path) return this.state;
        return this.getNestedProperty(this.state, path);
    }

    // Актуализиране на състоянието (merge)
    updateState(path, updates) {
        const currentValue = this.getState(path);
        const newValue = { ...currentValue, ...updates };
        return this.setState(path, newValue);
    }

    // Добавяне към масив в състоянието
    pushToState(path, item) {
        const currentArray = this.getState(path) || [];
        const newArray = [...currentArray, item];
        return this.setState(path, newArray);
    }

    // Премахване от масив в състоянието
    removeFromState(path, predicate) {
        const currentArray = this.getState(path) || [];
        const newArray = currentArray.filter(item => !predicate(item));
        return this.setState(path, newArray);
    }

    // Помощни методи за работа с nested properties
    setNestedProperty(obj, path, value) {
        const keys = path.split('.');
        let current = obj;
        
        for (let i = 0; i < keys.length - 1; i++) {
            const key = keys[i];
            if (!(key in current) || typeof current[key] !== 'object') {
                current[key] = {};
            }
            current = current[key];
        }
        
        current[keys[keys.length - 1]] = value;
    }

    getNestedProperty(obj, path) {
        return path.split('.').reduce((current, key) => {
            return current && current[key] !== undefined ? current[key] : undefined;
        }, obj);
    }

    // Известяване на слушателите
    notifyListeners(path, newValue, oldValue) {
        // Известяване на точния път
        const exactListeners = this.listeners.get(path);
        if (exactListeners) {
            exactListeners.forEach(callback => {
                try {
                    callback(newValue, oldValue, path);
                } catch (error) {
                    console.error(`Грешка в listener за ${path}:`, error);
                }
            });
        }

        // Известяване на parent paths
        const pathParts = path.split('.');
        for (let i = pathParts.length - 1; i > 0; i--) {
            const parentPath = pathParts.slice(0, i).join('.');
            const parentListeners = this.listeners.get(parentPath);
            if (parentListeners) {
                const parentValue = this.getState(parentPath);
                parentListeners.forEach(callback => {
                    try {
                        callback(parentValue, undefined, parentPath);
                    } catch (error) {
                        console.error(`Грешка в parent listener за ${parentPath}:`, error);
                    }
                });
            }
        }
    }

    // Middleware система
    addMiddleware(middleware) {
        this.middleware.push(middleware);
    }

    applyMiddleware(action, data) {
        return this.middleware.reduce((result, middleware) => {
            return middleware(action, result);
        }, data);
    }

    // История на промените
    addToHistory(entry) {
        this.history.push(entry);
        if (this.history.length > this.maxHistorySize) {
            this.history = this.history.slice(-this.maxHistorySize);
        }
    }

    getHistory() {
        return [...this.history];
    }

    // Debugging методи
    debug() {
        console.group('StateManager Debug');
        console.log('Current State:', this.state);
        console.log('Active Listeners:', Array.from(this.listeners.keys()));
        console.log('History:', this.history.slice(-10));
        console.groupEnd();
    }

    // Сериализация за запазване
    serialize() {
        return JSON.stringify({
            state: this.state,
            timestamp: new Date().toISOString()
        });
    }

    // Десериализация за възстановяване
    deserialize(serializedState) {
        try {
            const { state } = JSON.parse(serializedState);
            this.state = { ...this.getInitialState(), ...state };
            this.notifyAllListeners();
        } catch (error) {
            console.error('Грешка при десериализация:', error);
        }
    }

    notifyAllListeners() {
        this.listeners.forEach((listeners, path) => {
            const value = this.getState(path);
            listeners.forEach(callback => callback(value, undefined, path));
        });
    }

    // Изчистване на състоянието
    reset() {
        this.state = this.getInitialState();
        this.history = [];
        this.notifyAllListeners();
    }
}

export default StateManager;
