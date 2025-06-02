/**
 * Service Worker pour NinjaLead.ai
 * Gère le cache offline et améliore les performances
 */

const CACHE_NAME = 'ninjalead-cache-v1';
const OFFLINE_PAGE = '/offline';

// Ressources à mettre en cache immédiatement
const STATIC_CACHE_URLS = [
    '/',
    '/static/css/custom.css',
    '/static/js/loading.js',
    '/static/js/progressive-loading.js',
    '/static/images/ninja-logo.png',
    '/static/images/ninja-meditation.png',
    '/offline'
];

// Ressources dynamiques à mettre en cache lors de l'accès
const DYNAMIC_CACHE_PATTERNS = [
    /^\/dashboard/,
    /^\/customers/,
    /^\/campaigns/,
    /^\/products/,
    /^\/static\//,
    /^\/images\//
];

// Installation du Service Worker
self.addEventListener('install', event => {
    console.log('Service Worker: Installation en cours...');
    
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                console.log('Service Worker: Mise en cache des ressources statiques');
                return cache.addAll(STATIC_CACHE_URLS);
            })
            .then(() => {
                console.log('Service Worker: Installation terminée');
                return self.skipWaiting();
            })
            .catch(err => {
                console.error('Service Worker: Erreur d\'installation', err);
            })
    );
});

// Activation du Service Worker
self.addEventListener('activate', event => {
    console.log('Service Worker: Activation en cours...');
    
    event.waitUntil(
        caches.keys()
            .then(cacheNames => {
                return Promise.all(
                    cacheNames.map(cacheName => {
                        if (cacheName !== CACHE_NAME) {
                            console.log('Service Worker: Suppression ancien cache', cacheName);
                            return caches.delete(cacheName);
                        }
                    })
                );
            })
            .then(() => {
                console.log('Service Worker: Activation terminée');
                return self.clients.claim();
            })
    );
});

// Interception des requêtes réseau
self.addEventListener('fetch', event => {
    const request = event.request;
    const url = new URL(request.url);
    
    // Ignorer les requêtes non-HTTP
    if (!request.url.startsWith('http')) {
        return;
    }
    
    // Stratégie Cache First pour les ressources statiques
    if (request.method === 'GET' && isStaticResource(url.pathname)) {
        event.respondWith(cacheFirstStrategy(request));
        return;
    }
    
    // Stratégie Network First pour les pages dynamiques
    if (request.method === 'GET' && isDynamicPage(url.pathname)) {
        event.respondWith(networkFirstStrategy(request));
        return;
    }
    
    // Stratégie Network Only pour les API et POST/PUT/DELETE
    if (request.method !== 'GET' || url.pathname.startsWith('/api/')) {
        event.respondWith(networkOnlyStrategy(request));
        return;
    }
    
    // Par défaut, essayer le réseau puis le cache
    event.respondWith(networkFirstStrategy(request));
});

/**
 * Vérifie si une URL correspond à une ressource statique
 */
function isStaticResource(pathname) {
    return pathname.startsWith('/static/') || 
           pathname.startsWith('/images/') ||
           pathname.endsWith('.js') ||
           pathname.endsWith('.css') ||
           pathname.endsWith('.png') ||
           pathname.endsWith('.jpg') ||
           pathname.endsWith('.jpeg') ||
           pathname.endsWith('.webp') ||
           pathname.endsWith('.svg');
}

/**
 * Vérifie si une URL correspond à une page dynamique cacheable
 */
function isDynamicPage(pathname) {
    return DYNAMIC_CACHE_PATTERNS.some(pattern => pattern.test(pathname));
}

/**
 * Stratégie Cache First: cache d'abord, réseau en fallback
 */
async function cacheFirstStrategy(request) {
    try {
        // Chercher dans le cache
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }
        
        // Si pas en cache, aller sur le réseau
        const networkResponse = await fetch(request);
        
        // Mettre en cache si succès
        if (networkResponse.ok) {
            const cache = await caches.open(CACHE_NAME);
            cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
        
    } catch (error) {
        console.error('Service Worker: Erreur Cache First', error);
        return caches.match('/offline') || new Response('Hors ligne', { status: 503 });
    }
}

/**
 * Stratégie Network First: réseau d'abord, cache en fallback
 */
async function networkFirstStrategy(request) {
    try {
        // Essayer le réseau d'abord
        const networkResponse = await fetch(request);
        
        // Mettre en cache si succès et méthode GET
        if (networkResponse.ok && request.method === 'GET') {
            const cache = await caches.open(CACHE_NAME);
            cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
        
    } catch (error) {
        console.log('Service Worker: Réseau indisponible, recherche en cache');
        
        // Chercher dans le cache
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }
        
        // Page offline par défaut
        return caches.match('/offline') || new Response('Hors ligne', { status: 503 });
    }
}

/**
 * Stratégie Network Only: réseau uniquement
 */
async function networkOnlyStrategy(request) {
    try {
        return await fetch(request);
    } catch (error) {
        console.error('Service Worker: Erreur Network Only', error);
        
        if (request.method === 'GET') {
            return caches.match('/offline') || new Response('Hors ligne', { status: 503 });
        }
        
        return new Response('Erreur réseau', { status: 503 });
    }
}

// Gestion des messages depuis la page principale
self.addEventListener('message', event => {
    const { type, data } = event.data;
    
    switch (type) {
        case 'SKIP_WAITING':
            self.skipWaiting();
            break;
            
        case 'CACHE_URLS':
            cacheUrls(data.urls);
            break;
            
        case 'CLEAR_CACHE':
            clearCache();
            break;
            
        case 'GET_CACHE_STATUS':
            getCacheStatus().then(status => {
                event.ports[0].postMessage(status);
            });
            break;
    }
});

/**
 * Met en cache une liste d'URLs
 */
async function cacheUrls(urls) {
    try {
        const cache = await caches.open(CACHE_NAME);
        await cache.addAll(urls);
        console.log('Service Worker: URLs mises en cache', urls);
    } catch (error) {
        console.error('Service Worker: Erreur mise en cache URLs', error);
    }
}

/**
 * Vide le cache
 */
async function clearCache() {
    try {
        const cacheNames = await caches.keys();
        await Promise.all(cacheNames.map(name => caches.delete(name)));
        console.log('Service Worker: Cache vidé');
    } catch (error) {
        console.error('Service Worker: Erreur vidage cache', error);
    }
}

/**
 * Retourne le statut du cache
 */
async function getCacheStatus() {
    try {
        const cache = await caches.open(CACHE_NAME);
        const requests = await cache.keys();
        
        let totalSize = 0;
        for (const request of requests) {
            const response = await cache.match(request);
            if (response) {
                const blob = await response.blob();
                totalSize += blob.size;
            }
        }
        
        return {
            totalFiles: requests.length,
            totalSize: totalSize,
            totalSizeMB: (totalSize / (1024 * 1024)).toFixed(2)
        };
    } catch (error) {
        console.error('Service Worker: Erreur statut cache', error);
        return { totalFiles: 0, totalSize: 0, totalSizeMB: '0' };
    }
}