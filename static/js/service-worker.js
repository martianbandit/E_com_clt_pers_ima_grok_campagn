/**
 * Service Worker pour NinjaLead.ai
 * Gestion du cache offline et optimisation des performances
 */

const CACHE_NAME = 'ninjalead-v1.2.0';
const STATIC_CACHE = `${CACHE_NAME}-static`;
const DYNAMIC_CACHE = `${CACHE_NAME}-dynamic`;
const API_CACHE = `${CACHE_NAME}-api`;

// Assets statiques à mettre en cache immédiatement
const STATIC_ASSETS = [
    '/',
    '/static/css/style.css',
    '/static/css/bootstrap.min.css',
    '/static/js/app.js',
    '/static/js/bootstrap.bundle.min.js',
    '/static/images/logo.png',
    '/static/images/ninja-avatar.png',
    '/offline.html'
];

// URLs d'API à mettre en cache
const API_ROUTES = [
    '/api/dashboard-stats',
    '/api/campaigns',
    '/api/boutiques',
    '/health'
];

// Stratégies de cache
const CACHE_STRATEGIES = {
    // Cache First pour les assets statiques
    'cache-first': [
        /\.(?:css|js|png|jpg|jpeg|svg|gif|woff|woff2|ttf|eot|ico)$/,
        /^\/static\//,
        /^\/assets\//,
        /^\/optimized-images\//
    ],
    
    // Network First pour les pages HTML
    'network-first': [
        /\.html$/,
        /^\/dashboard/,
        /^\/campaigns/,
        /^\/boutiques/,
        /^\/admin/
    ],
    
    // Stale While Revalidate pour l'API
    'stale-while-revalidate': [
        /^\/api\//,
        /^\/health/
    ]
};

/**
 * Installation du Service Worker
 */
self.addEventListener('install', event => {
    console.log('[SW] Installation du Service Worker v1.2.0');
    
    event.waitUntil(
        Promise.all([
            // Cache des assets statiques
            caches.open(STATIC_CACHE).then(cache => {
                console.log('[SW] Mise en cache des assets statiques');
                return cache.addAll(STATIC_ASSETS);
            }),
            
            // Cache des données API critiques
            cacheAPIData()
        ]).then(() => {
            console.log('[SW] Installation terminée');
            return self.skipWaiting();
        }).catch(error => {
            console.error('[SW] Erreur lors de l\'installation:', error);
        })
    );
});

/**
 * Activation du Service Worker
 */
self.addEventListener('activate', event => {
    console.log('[SW] Activation du Service Worker');
    
    event.waitUntil(
        Promise.all([
            // Nettoyage des anciens caches
            cleanupOldCaches(),
            
            // Prise de contrôle immédiate
            self.clients.claim()
        ]).then(() => {
            console.log('[SW] Activation terminée');
        })
    );
});

/**
 * Interception des requêtes réseau
 */
self.addEventListener('fetch', event => {
    const { request } = event;
    const url = new URL(request.url);
    
    // Ignorer les requêtes non-HTTP
    if (!request.url.startsWith('http')) {
        return;
    }
    
    // Déterminer la stratégie de cache
    const strategy = getCacheStrategy(request.url);
    
    switch (strategy) {
        case 'cache-first':
            event.respondWith(cacheFirstStrategy(request));
            break;
        case 'network-first':
            event.respondWith(networkFirstStrategy(request));
            break;
        case 'stale-while-revalidate':
            event.respondWith(staleWhileRevalidateStrategy(request));
            break;
        default:
            event.respondWith(networkOnlyStrategy(request));
    }
});

/**
 * Stratégie Cache First
 */
async function cacheFirstStrategy(request) {
    try {
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }
        
        const networkResponse = await fetch(request);
        if (networkResponse.ok) {
            const cache = await caches.open(STATIC_CACHE);
            cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
    } catch (error) {
        console.error('[SW] Cache First failed:', error);
        return getCachedFallback(request);
    }
}

/**
 * Stratégie Network First
 */
async function networkFirstStrategy(request) {
    try {
        const networkResponse = await fetch(request);
        
        if (networkResponse.ok) {
            const cache = await caches.open(DYNAMIC_CACHE);
            cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
    } catch (error) {
        console.log('[SW] Network failed, trying cache:', request.url);
        
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }
        
        // Page offline pour les navigations
        if (request.mode === 'navigate') {
            return caches.match('/offline.html');
        }
        
        return new Response('Contenu non disponible hors ligne', {
            status: 503,
            statusText: 'Service Unavailable'
        });
    }
}

/**
 * Stratégie Stale While Revalidate
 */
async function staleWhileRevalidateStrategy(request) {
    const cache = await caches.open(API_CACHE);
    const cachedResponse = await cache.match(request);
    
    // Requête réseau en arrière-plan pour mettre à jour le cache
    const networkResponsePromise = fetch(request).then(response => {
        if (response.ok) {
            cache.put(request, response.clone());
        }
        return response;
    }).catch(error => {
        console.log('[SW] Network update failed:', error);
        return null;
    });
    
    // Retourner immédiatement la version cachée si disponible
    return cachedResponse || networkResponsePromise;
}

/**
 * Stratégie Network Only
 */
async function networkOnlyStrategy(request) {
    return fetch(request);
}

/**
 * Détermine la stratégie de cache pour une URL
 */
function getCacheStrategy(url) {
    for (const [strategy, patterns] of Object.entries(CACHE_STRATEGIES)) {
        if (patterns.some(pattern => pattern.test(url))) {
            return strategy;
        }
    }
    return 'network-only';
}

/**
 * Cache les données API critiques
 */
async function cacheAPIData() {
    const cache = await caches.open(API_CACHE);
    
    for (const route of API_ROUTES) {
        try {
            const response = await fetch(route);
            if (response.ok) {
                await cache.put(route, response);
                console.log(`[SW] API cached: ${route}`);
            }
        } catch (error) {
            console.log(`[SW] Failed to cache API: ${route}`, error);
        }
    }
}

/**
 * Nettoie les anciens caches
 */
async function cleanupOldCaches() {
    const cacheNames = await caches.keys();
    const currentCaches = [STATIC_CACHE, DYNAMIC_CACHE, API_CACHE];
    
    const deletionPromises = cacheNames
        .filter(name => !currentCaches.includes(name))
        .map(name => {
            console.log(`[SW] Suppression ancien cache: ${name}`);
            return caches.delete(name);
        });
    
    return Promise.all(deletionPromises);
}

/**
 * Fallback pour les requêtes qui échouent
 */
async function getCachedFallback(request) {
    const url = new URL(request.url);
    
    // Fallback pour les images
    if (request.destination === 'image') {
        return caches.match('/static/images/placeholder.png');
    }
    
    // Fallback pour les pages
    if (request.mode === 'navigate') {
        return caches.match('/offline.html');
    }
    
    return new Response('Ressource non disponible', {
        status: 503,
        statusText: 'Service Unavailable'
    });
}

/**
 * Messages depuis l'application principale
 */
self.addEventListener('message', event => {
    const { type, payload } = event.data;
    
    switch (type) {
        case 'CACHE_UPDATE':
            updateCache(payload);
            break;
        case 'CLEAR_CACHE':
            clearAllCaches();
            break;
        case 'GET_CACHE_STATUS':
            getCacheStatus().then(status => {
                event.ports[0].postMessage(status);
            });
            break;
    }
});

/**
 * Met à jour le cache avec de nouvelles données
 */
async function updateCache(payload) {
    const { url, data } = payload;
    const cache = await caches.open(DYNAMIC_CACHE);
    
    const response = new Response(JSON.stringify(data), {
        headers: { 'Content-Type': 'application/json' }
    });
    
    await cache.put(url, response);
    console.log(`[SW] Cache updated for: ${url}`);
}

/**
 * Vide tous les caches
 */
async function clearAllCaches() {
    const cacheNames = await caches.keys();
    const deletionPromises = cacheNames.map(name => caches.delete(name));
    await Promise.all(deletionPromises);
    console.log('[SW] Tous les caches vidés');
}

/**
 * Retourne le statut du cache
 */
async function getCacheStatus() {
    const cacheNames = await caches.keys();
    const status = {};
    
    for (const name of cacheNames) {
        const cache = await caches.open(name);
        const keys = await cache.keys();
        status[name] = keys.length;
    }
    
    return {
        caches: status,
        totalCaches: cacheNames.length,
        version: CACHE_NAME
    };
}

/**
 * Gestion des notifications push (future extension)
 */
self.addEventListener('push', event => {
    if (!event.data) return;
    
    const data = event.data.json();
    const options = {
        body: data.body,
        icon: '/static/images/ninja-avatar.png',
        badge: '/static/images/logo.png',
        tag: 'ninjalead-notification',
        requireInteraction: true,
        actions: [
            {
                action: 'view',
                title: 'Voir'
            },
            {
                action: 'dismiss',
                title: 'Ignorer'
            }
        ]
    };
    
    event.waitUntil(
        self.registration.showNotification(data.title, options)
    );
});

/**
 * Gestion des clics sur notifications
 */
self.addEventListener('notificationclick', event => {
    event.notification.close();
    
    if (event.action === 'view') {
        event.waitUntil(
            clients.openWindow('/dashboard')
        );
    }
});

console.log('[SW] Service Worker NinjaLead.ai v1.2.0 chargé');