// components/NavigationComponent.js
import BaseComponent from './BaseComponent.js';

class NavigationComponent extends BaseComponent {
    constructor(container, stateManager, services) {
        super(container, stateManager, services);
        this.slides = ['home', 'about', 'instructions', 'chat', 'map'];
        this.currentSlideIndex = 0;
    }

    render() {
        // Navigation е вече в HTML, само добавяме функционалност
        this.navButtons = this.container.querySelectorAll('.nav-btn');
        this.slideBg = this.container.querySelector('.nav-slide-bg');
    }

    bindEvents() {
        this.navButtons.forEach((button, index) => {
            this.addEventListener(button, 'click', (e) => {
                e.preventDefault();
                const slideId = button.getAttribute('data-slide');
                this.navigateToSlide(slideId, index);
            });

            this.addEventListener(button, 'keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    const slideId = button.getAttribute('data-slide');
                    this.navigateToSlide(slideId, index);
                }
            });
        });

        // Keyboard navigation
        this.addEventListener(document, 'keydown', (e) => {
            this.handleKeyboardNavigation(e);
        });
    }

    subscribeToState() {
        this.subscribe('ui.currentSlide', (slideId) => {
            this.updateActiveSlide(slideId);
        });
    }

    navigateToSlide(slideId, index) {
        if (!slideId || !this.slides.includes(slideId)) {
            console.warn('Невалиден слайд:', slideId);
            return;
        }

        console.log(`🧭 Навигация към слайд: ${slideId}`);
        this.stateManager.setState('ui.currentSlide', slideId);
        this.currentSlideIndex = index !== undefined ? index : this.slides.indexOf(slideId);
    }

    updateActiveSlide(slideId) {
        // Актуализиране на слайдовете
        const slides = document.querySelectorAll('.slide');
        slides.forEach(slide => {
            slide.classList.remove('active');
            slide.setAttribute('aria-hidden', 'true');
        });

        const targetSlide = document.getElementById(`${slideId}-slide`);
        if (targetSlide) {
            targetSlide.classList.add('active');
            targetSlide.setAttribute('aria-hidden', 'false');
        }

        // Актуализиране на навигационните бутони
        this.navButtons.forEach(button => {
            button.classList.remove('active');
            button.setAttribute('aria-pressed', 'false');
        });

        const activeButton = this.container.querySelector(`[data-slide="${slideId}"]`);
        if (activeButton) {
            activeButton.classList.add('active');
            activeButton.setAttribute('aria-pressed', 'true');
        }

        // Актуализиране на sliding background
        const slideIndex = this.slides.indexOf(slideId);
        if (this.slideBg && slideIndex !== -1) {
            this.slideBg.classList.remove('slide-0', 'slide-1', 'slide-2', 'slide-3', 'slide-4');
            this.slideBg.classList.add(`slide-${slideIndex}`);
        }

        // Специфични действия за слайдовете
        this.handleSlideSpecificActions(slideId);
    }

    handleSlideSpecificActions(slideId) {
        switch (slideId) {
            case 'map':
                setTimeout(() => {
                    // Trigger map resize
                    window.dispatchEvent(new Event('resize'));
                }, 500);
                break;
            case 'chat':
                setTimeout(() => {
                    // Focus chat input
                    const chatInput = document.getElementById('user-input');
                    if (chatInput) {
                        chatInput.focus();
                    }
                }, 500);
                break;
        }
    }

    handleKeyboardNavigation(event) {
        // Arrow keys за навигация
        if (event.altKey) {
            switch (event.key) {
                case 'ArrowUp':
                    event.preventDefault();
                    this.navigateToPrevious();
                    break;
                case 'ArrowDown':
                    event.preventDefault();
                    this.navigateToNext();
                    break;
            }
        }

        // Number keys за директна навигация
        if (event.altKey && event.key >= '1' && event.key <= '5') {
            event.preventDefault();
            const index = parseInt(event.key) - 1;
            this.navigateToSlide(this.slides[index], index);
        }
    }

    navigateToPrevious() {
        const newIndex = this.currentSlideIndex > 0 ? this.currentSlideIndex - 1 : this.slides.length - 1;
        this.navigateToSlide(this.slides[newIndex], newIndex);
    }

    navigateToNext() {
        const newIndex = this.currentSlideIndex < this.slides.length - 1 ? this.currentSlideIndex + 1 : 0;
        this.navigateToSlide(this.slides[newIndex], newIndex);
    }
}

export default NavigationComponent;
