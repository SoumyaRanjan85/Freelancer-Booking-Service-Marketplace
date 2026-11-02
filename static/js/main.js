/**
 * FreelanceConnect - Main JavaScript & 3D Center-Stage Carousel Controller
 */

document.addEventListener('DOMContentLoaded', function () {
    // Enable Bootstrap tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Auto-dismiss standard alerts after 5 seconds
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert-dismissible');
        alerts.forEach(function(alert) {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            bsAlert.close();
        });
    }, 5000);

    // Initialize all 3D Center-Stage Carousels across the landing page
    initCenterStageCarousels();

    // Initialize live search filter for Mega Skills Modal
    initSkillsModalSearch();
});

// Helper for Demo Login Quick Autofill
function fillDemoCredentials(email, password) {
    const emailField = document.getElementById('email');
    const passwordField = document.getElementById('password');
    if (emailField && passwordField) {
        emailField.value = email;
        passwordField.value = password;
        emailField.classList.add('is-valid');
        passwordField.classList.add('is-valid');
    }
}

// Generic JSON fetch helper
async function postJSON(url, data) {
    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify(data)
        });
        const result = await response.json();
        return { ok: response.ok, status: response.status, data: result };
    } catch (err) {
        console.error('API Error:', err);
        return { ok: false, error: err.message };
    }
}

// Display dynamic toast
function showToast(message, type = 'success') {
    const toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
        alert(message);
        return;
    }
    const toastEl = document.createElement('div');
    toastEl.className = `toast align-items-center text-white bg-${type === 'error' ? 'danger' : type} border-0 show`;
    toastEl.setAttribute('role', 'alert');
    toastEl.setAttribute('aria-live', 'assertive');
    toastEl.setAttribute('aria-atomic', 'true');
    toastEl.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    toastContainer.appendChild(toastEl);
    setTimeout(() => {
        toastEl.remove();
    }, 4000);
}

// -------------------------------------------------------------
// 3D Center-Stage Infinite Carousel Controller
// Holds active item at center for 10 seconds, highlights it,
// and repeats infinitely with forward/backward arrow navigation.
// -------------------------------------------------------------
class CenterStageCarousel {
    constructor(containerEl, options = {}) {
        this.container = containerEl;
        this.track = containerEl.querySelector('.carousel-stage-track');
        this.cards = Array.from(this.track.querySelectorAll('.carousel-stage-card'));
        this.prevBtn = containerEl.querySelector('.carousel-nav-btn.prev-btn');
        this.nextBtn = containerEl.querySelector('.carousel-nav-btn.next-btn');
        this.dotsContainer = containerEl.querySelector('.carousel-indicators-bar');
        this.progressBar = containerEl.querySelector('.carousel-timer-progress');
        
        // 10-second hold time configuration
        this.holdDuration = options.holdDuration || 10000;
        this.currentIndex = 0;
        this.total = this.cards.length;
        this.timer = null;
        this.progressInterval = null;
        this.elapsed = 0;
        this.isPaused = false;

        if (this.total === 0) return;

        this.init();
    }

    init() {
        this.buildIndicators();
        this.bindEvents();
        this.updatePosition();
        this.startTimer();
    }

    buildIndicators() {
        if (!this.dotsContainer) return;
        this.dotsContainer.innerHTML = '';
        this.dots = [];
        this.cards.forEach((card, idx) => {
            const dot = document.createElement('span');
            dot.className = `carousel-dot ${idx === 0 ? 'active' : ''}`;
            dot.dataset.index = idx;
            dot.addEventListener('click', (e) => {
                e.stopPropagation();
                this.goTo(idx);
            });
            this.dotsContainer.appendChild(dot);
            this.dots.push(dot);
        });
    }

    bindEvents() {
        if (this.prevBtn) {
            this.prevBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.prev();
            });
        }

        if (this.nextBtn) {
            this.nextBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.next();
            });
        }

        // Clicking a card directly centers it
        this.cards.forEach((card, idx) => {
            card.addEventListener('click', () => {
                if (idx !== this.currentIndex) {
                    this.goTo(idx);
                }
            });
        });

        // Pause countdown on mouse hover so client can read card or click links
        this.container.addEventListener('mouseenter', () => {
            this.isPaused = true;
        });

        this.container.addEventListener('mouseleave', () => {
            this.isPaused = false;
        });

        // Recalculate on window resize
        window.addEventListener('resize', () => {
            this.updatePosition();
        });
    }

    startTimer() {
        this.clearTimer();
        this.elapsed = 0;
        const tickMs = 100;

        this.progressInterval = setInterval(() => {
            if (!this.isPaused) {
                this.elapsed += tickMs;
                if (this.progressBar) {
                    const percent = Math.min(100, (this.elapsed / this.holdDuration) * 100);
                    this.progressBar.style.width = `${percent}%`;
                }

                if (this.elapsed >= this.holdDuration) {
                    this.next();
                }
            }
        }, tickMs);
    }

    clearTimer() {
        if (this.progressInterval) {
            clearInterval(this.progressInterval);
            this.progressInterval = null;
        }
        if (this.progressBar) {
            this.progressBar.style.width = '0%';
        }
    }

    prev() {
        // Infinite backward loop
        this.currentIndex = (this.currentIndex - 1 + this.total) % this.total;
        this.updatePosition();
        this.startTimer();
    }

    next() {
        // Infinite forward loop
        this.currentIndex = (this.currentIndex + 1) % this.total;
        this.updatePosition();
        this.startTimer();
    }

    goTo(index) {
        this.currentIndex = ((index % this.total) + this.total) % this.total;
        this.updatePosition();
        this.startTimer();
    }

    updatePosition() {
        if (!this.cards[this.currentIndex]) return;

        const activeCard = this.cards[this.currentIndex];
        const containerWidth = this.container.offsetWidth;
        const cardWidth = activeCard.offsetWidth;
        const cardLeft = activeCard.offsetLeft;

        // Calculate translation so active card is exactly centered in viewport
        const targetOffset = (containerWidth / 2) - (cardLeft + cardWidth / 2);
        this.track.style.transform = `translateX(${targetOffset}px)`;

        // Highlight center focal card and remove from peers
        this.cards.forEach((card, idx) => {
            if (idx === this.currentIndex) {
                card.classList.add('focal-center');
                card.setAttribute('aria-current', 'true');
            } else {
                card.classList.remove('focal-center');
                card.removeAttribute('aria-current');
            }
        });

        // Update dots indicator
        if (this.dots) {
            this.dots.forEach((dot, idx) => {
                dot.classList.toggle('active', idx === this.currentIndex);
            });
        }
    }
}

function initCenterStageCarousels() {
    const containers = document.querySelectorAll('[data-carousel="center-stage"]');
    containers.forEach(container => {
        // Minimum 10 seconds hold time as required
        new CenterStageCarousel(container, { holdDuration: 10000 });
    });
}

// Live search in Mega Skills Modal
function initSkillsModalSearch() {
    const searchInput = document.getElementById('skillsModalSearch');
    if (!searchInput) return;

    searchInput.addEventListener('input', function() {
        const query = this.value.toLowerCase().trim();
        const skillBadges = document.querySelectorAll('.taxonomy-skill-item');
        const categorySections = document.querySelectorAll('.taxonomy-category-block');

        skillBadges.forEach(badge => {
            const text = badge.textContent.toLowerCase();
            if (!query || text.includes(query)) {
                badge.style.display = 'inline-block';
            } else {
                badge.style.display = 'none';
            }
        });

        categorySections.forEach(sec => {
            const visiblePills = sec.querySelectorAll('.taxonomy-skill-item:not([style*="display: none"])');
            sec.style.display = visiblePills.length > 0 ? 'block' : 'none';
        });
    });
}
