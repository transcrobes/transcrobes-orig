// register service worker

// this is just nasty but I have no idea how to do it properly...
import { ServiceWorkerProxy } from './proxies.js';
import { CACHE_NAME, INITIALISATION_CACHE_NAME } from './schemas.js';
import NoSleep from 'nosleep.js';
import dayjs from 'dayjs';

window.wproxy = new ServiceWorkerProxy();
window.noSleep = new NoSleep();
window.dayjs = dayjs;
window.CACHE_NAME = CACHE_NAME;
window.INITIALISATION_CACHE_NAME = INITIALISATION_CACHE_NAME;
