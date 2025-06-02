/**
 * Système de chargement progressif côté client
 * Gère la pagination et le scroll infini
 */

class ProgressiveLoader {
    constructor(options = {}) {
        this.container = options.container || document.querySelector('[data-progressive-container]');
        this.loadMoreBtn = options.loadMoreBtn || document.querySelector('[data-load-more]');
        this.loadingIndicator = options.loadingIndicator || document.querySelector('[data-loading]');
        this.endpoint = options.endpoint || this.container?.dataset.endpoint;
        this.currentPage = parseInt(options.startPage) || 1;
        this.totalPages = parseInt(options.totalPages) || 1;
        this.perPage = parseInt(options.perPage) || 20;
        this.infiniteScroll = options.infiniteScroll || false;
        this.threshold = options.threshold || 200; // pixels from bottom
        
        this.isLoading = false;
        this.hasMore = this.currentPage < this.totalPages;
        
        this.init();
    }
    
    init() {
        if (!this.container || !this.endpoint) {
            console.warn('Progressive loader: Container ou endpoint manquant');
            return;
        }
        
        this.setupEventListeners();
        this.updateUI();
    }
    
    setupEventListeners() {
        // Bouton "Charger plus"
        if (this.loadMoreBtn) {
            this.loadMoreBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.loadMore();
            });
        }
        
        // Scroll infini
        if (this.infiniteScroll) {
            window.addEventListener('scroll', this.throttle(() => {
                this.checkScrollPosition();
            }, 200));
        }
        
        // Filtres et recherche
        const filterForm = document.querySelector('[data-filter-form]');
        if (filterForm) {
            filterForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.resetAndFilter();
            });
            
            // Auto-filter sur changement
            const autoFilterInputs = filterForm.querySelectorAll('[data-auto-filter]');
            autoFilterInputs.forEach(input => {
                input.addEventListener('change', () => {
                    this.debounce(() => this.resetAndFilter(), 500)();
                });
            });
        }
    }
    
    async loadMore() {
        if (this.isLoading || !this.hasMore) {
            return;
        }
        
        this.isLoading = true;
        this.showLoading();
        
        try {
            const nextPage = this.currentPage + 1;
            const response = await this.fetchPage(nextPage);
            
            if (response.success) {
                this.appendItems(response.items_html);
                this.currentPage = nextPage;
                this.hasMore = response.has_more;
                this.totalPages = response.total_pages || this.totalPages;
                
                // Émettre événement personnalisé
                this.container.dispatchEvent(new CustomEvent('itemsLoaded', {
                    detail: { page: nextPage, total: response.total_items }
                }));
            } else {
                this.showError(response.error || 'Erreur lors du chargement');
            }
        } catch (error) {
            console.error('Erreur chargement progressif:', error);
            this.showError('Erreur de connexion');
        } finally {
            this.isLoading = false;
            this.hideLoading();
            this.updateUI();
        }
    }
    
    async resetAndFilter() {
        this.currentPage = 1;
        this.isLoading = true;
        this.showLoading();
        
        try {
            const response = await this.fetchPage(1, true);
            
            if (response.success) {
                this.replaceItems(response.items_html);
                this.currentPage = 1;
                this.hasMore = response.has_more;
                this.totalPages = response.total_pages || 1;
                
                // Scroll vers le haut
                this.container.scrollIntoView({ behavior: 'smooth', block: 'start' });
            } else {
                this.showError(response.error || 'Erreur lors du filtrage');
            }
        } catch (error) {
            console.error('Erreur filtrage:', error);
            this.showError('Erreur de connexion');
        } finally {
            this.isLoading = false;
            this.hideLoading();
            this.updateUI();
        }
    }
    
    async fetchPage(page, reset = false) {
        const url = new URL(this.endpoint, window.location.origin);
        url.searchParams.set('page', page);
        url.searchParams.set('per_page', this.perPage);
        
        // Ajouter les paramètres de filtre
        const filterForm = document.querySelector('[data-filter-form]');
        if (filterForm) {
            const formData = new FormData(filterForm);
            for (let [key, value] of formData.entries()) {
                if (value.trim()) {
                    url.searchParams.set(key, value);
                }
            }
        }
        
        if (reset) {
            url.searchParams.set('reset', '1');
        }
        
        const response = await fetch(url, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': 'application/json'
            }
        });
        
        return await response.json();
    }
    
    appendItems(html) {
        if (!html) return;
        
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = html;
        
        const items = tempDiv.children;
        for (let item of items) {
            this.container.appendChild(item);
        }
        
        // Animation d'apparition
        this.animateNewItems();
    }
    
    replaceItems(html) {
        // Garder les éléments non-item (titre, filtres, etc.)
        const itemSelector = this.container.dataset.itemSelector || '.list-item';
        const existingItems = this.container.querySelectorAll(itemSelector);
        existingItems.forEach(item => item.remove());
        
        if (html) {
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = html;
            
            const items = tempDiv.children;
            for (let item of items) {
                this.container.appendChild(item);
            }
        }
        
        this.animateNewItems();
    }
    
    animateNewItems() {
        const itemSelector = this.container.dataset.itemSelector || '.list-item';
        const newItems = this.container.querySelectorAll(`${itemSelector}:not(.animated)`);
        
        newItems.forEach((item, index) => {
            item.classList.add('animated');
            item.style.opacity = '0';
            item.style.transform = 'translateY(20px)';
            
            setTimeout(() => {
                item.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
                item.style.opacity = '1';
                item.style.transform = 'translateY(0)';
            }, index * 50);
        });
    }
    
    checkScrollPosition() {
        if (this.isLoading || !this.hasMore) return;
        
        const scrollTop = window.pageYOffset;
        const windowHeight = window.innerHeight;
        const documentHeight = document.documentElement.scrollHeight;
        
        if (scrollTop + windowHeight >= documentHeight - this.threshold) {
            this.loadMore();
        }
    }
    
    showLoading() {
        if (this.loadingIndicator) {
            this.loadingIndicator.style.display = 'block';
        }
        
        if (this.loadMoreBtn) {
            this.loadMoreBtn.disabled = true;
            this.loadMoreBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Chargement...';
        }
    }
    
    hideLoading() {
        if (this.loadingIndicator) {
            this.loadingIndicator.style.display = 'none';
        }
    }
    
    updateUI() {
        if (this.loadMoreBtn) {
            if (this.hasMore && !this.isLoading) {
                this.loadMoreBtn.disabled = false;
                this.loadMoreBtn.innerHTML = 'Charger plus';
                this.loadMoreBtn.style.display = 'block';
            } else if (!this.hasMore) {
                this.loadMoreBtn.style.display = 'none';
            }
        }
        
        // Mettre à jour le compteur
        const counter = document.querySelector('[data-items-counter]');
        if (counter) {
            const currentItems = this.container.querySelectorAll(this.container.dataset.itemSelector || '.list-item').length;
            counter.textContent = `${currentItems} élément(s) affiché(s)`;
        }
    }
    
    showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'alert alert-danger alert-dismissible fade show';
        errorDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        this.container.insertBefore(errorDiv, this.container.firstChild);
        
        // Auto-dismiss après 5 secondes
        setTimeout(() => {
            if (errorDiv.parentNode) {
                errorDiv.remove();
            }
        }, 5000);
    }
    
    // Utilitaires
    throttle(func, delay) {
        let timeoutId;
        let lastExecTime = 0;
        return function (...args) {
            const currentTime = Date.now();
            
            if (currentTime - lastExecTime > delay) {
                func.apply(this, args);
                lastExecTime = currentTime;
            } else {
                clearTimeout(timeoutId);
                timeoutId = setTimeout(() => {
                    func.apply(this, args);
                    lastExecTime = Date.now();
                }, delay - (currentTime - lastExecTime));
            }
        };
    }
    
    debounce(func, delay) {
        let timeoutId;
        return function (...args) {
            clearTimeout(timeoutId);
            timeoutId = setTimeout(() => func.apply(this, args), delay);
        };
    }
}

// Auto-initialisation
document.addEventListener('DOMContentLoaded', () => {
    const containers = document.querySelectorAll('[data-progressive-container]');
    
    containers.forEach(container => {
        const options = {
            container: container,
            endpoint: container.dataset.endpoint,
            startPage: parseInt(container.dataset.currentPage) || 1,
            totalPages: parseInt(container.dataset.totalPages) || 1,
            perPage: parseInt(container.dataset.perPage) || 20,
            infiniteScroll: container.dataset.infiniteScroll === 'true'
        };
        
        new ProgressiveLoader(options);
    });
});

// Export pour utilisation en module
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ProgressiveLoader;
}