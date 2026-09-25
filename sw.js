const CACHE_NAME = 'whats-4-dinner-v1.2.2';
self.addEventListener('install', e => self.skipWaiting());
self.addEventListener('activate', e => self.clients.claim());
