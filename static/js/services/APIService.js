// services/APIService.js

class APIService {
    constructor(baseURL = '') {
        this.baseURL = baseURL;
        this.defaultHeaders = {
            'Content-Type': 'application/json'
        };
        this.timeout = 30000;
        this.requestInterceptors = [];
        this.responseInterceptors = [];
    }

    // Interceptor методи
    addRequestInterceptor(interceptor) {
        this.requestInterceptors.push(interceptor);
    }

    addResponseInterceptor(interceptor) {
        this.responseInterceptors.push(interceptor);
    }

    async applyRequestInterceptors(config) {
        let processedConfig = config;
        for (const interceptor of this.requestInterceptors) {
            processedConfig = await interceptor(processedConfig);
        }
        return processedConfig;
    }

    async applyResponseInterceptors(response) {
        let processedResponse = response;
        for (const interceptor of this.responseInterceptors) {
            processedResponse = await interceptor(processedResponse);
        }
        return processedResponse;
    }

    // Основен request метод с interceptors
    async request(endpoint, options = {}, retryCount = 0) {
        const maxRetries = options.maxRetries || 3;
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.timeout);

        try {
            // Прилагане на request interceptors
            const processedOptions = await this.applyRequestInterceptors({
                endpoint,
                options: { ...options },
                headers: { ...this.defaultHeaders, ...options.headers }
            });

            let requestUrl;
            if (endpoint.startsWith('http')) {
                requestUrl = endpoint;
            } else {
                requestUrl = this.baseURL ? `${this.baseURL}${endpoint}` : endpoint;
            }

            console.log(`🌐 API заявка към: ${requestUrl} (опит ${retryCount + 1})`);

            const response = await fetch(requestUrl, {
                headers: processedOptions.headers,
                signal: controller.signal,
                ...processedOptions.options
            });
            
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                throw new APIError(response.status, await response.text());
            }
            
            let data = await response.json();
            
            // Прилагане на response interceptors
            data = await this.applyResponseInterceptors(data);
            
            console.log('✅ API отговор получен');
            return data;
        } catch (error) {
            clearTimeout(timeoutId);
            
            // Retry логика за network грешки
            if (retryCount < maxRetries && this.shouldRetry(error)) {
                console.log(`🔄 Повторен опит ${retryCount + 1}/${maxRetries}`);
                await this.delay(1000 * (retryCount + 1));
                return this.request(endpoint, options, retryCount + 1);
            }
            
            throw this.handleError(error);
        }
    }

    // GET заявка
    async get(endpoint, params = {}) {
        try {
            let url;
            
            if (this.baseURL) {
                url = new URL(endpoint, this.baseURL);
            } else {
                url = new URL(endpoint, window.location.origin);
            }
            
            // Добавяне на параметри
            Object.keys(params).forEach(key => {
                if (params[key] !== null && params[key] !== undefined) {
                    url.searchParams.append(key, params[key]);
                }
            });
            
            return this.request(url.pathname + url.search, {
                method: 'GET'
            });
        } catch (error) {
            console.error('Грешка при конструиране на URL:', error);
            throw new APIError(400, 'Невалиден URL или параметри');
        }
    }

    // POST заявка
    async post(endpoint, data = {}) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    // PUT заявка
    async put(endpoint, data = {}) {
        return this.request(endpoint, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    // DELETE заявка
    async delete(endpoint) {
        return this.request(endpoint, {
            method: 'DELETE'
        });
    }

    // Помощни методи
    shouldRetry(error) {
        return error.name === 'AbortError' || 
               error.name === 'TypeError' || 
               (error.status >= 500 && error.status < 600);
    }

    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    handleError(error) {
        if (error.name === 'AbortError') {
            throw new TimeoutError('Заявката отне твърде много време');
        }
        
        if (error.name === 'TypeError' && error.message.includes('fetch')) {
            throw new NetworkError('Проблем с мрежовата връзка');
        }
        
        console.error('API Грешка:', error);
        throw error; // Re-throw вместо return
    }
}

// Специализирани грешки
class APIError extends Error {
    constructor(status, message) {
        super(message);
        this.name = 'APIError';
        this.status = status;
    }
}

class TimeoutError extends Error {
    constructor(message) {
        super(message);
        this.name = 'TimeoutError';
    }
}

class NetworkError extends Error {
    constructor(message) {
        super(message);
        this.name = 'NetworkError';
    }
}

export { APIService, APIError, TimeoutError, NetworkError };
export default APIService;
