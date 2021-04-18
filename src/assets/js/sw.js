
import { getDb, createRxDBConfig } from './syncdb.js';
import { GRADE } from './schemas.js';
import * as data from './data.js';
import * as utils from './lib.js';
import dayjs from 'dayjs';

const CACHE_VERSION = 'v1';
let db;
let allCardWordGraphs;
let knownCardWordGraphs;
let knownWordIdsCounter;
let eventQueueTimer;  // FIXME: find some way to be able to stop the timer if required/desired

// NOTES:
// - there is a loadDb in every call with a db, because the file can be unloaded from memory, and
// so loses all object refs (and timers?)

self.addEventListener('install', function(event) {
  // FIXME: for some reason getting with the potentially hundreds (thousands?) of content files
  // doesn't appear to work currently. This may not be absolutely necessary to do *here*, so
  // could have a button in settings or something to "make all content available offline" or whatever
  // return ;
  const static_files = ['/offline/', '/static/data/r2d2/reader.js.map', '/static/data/r2d2/injectables/click/click.js.map', '/static/data/r2d2/injectables/click/click.js', '/static/data/r2d2/injectables/style/style.css', '/static/data/r2d2/injectables/glossary/glossary.js.map', '/static/data/r2d2/injectables/glossary/glossary.js', '/static/data/r2d2/injectables/footnotes/footnotes.js', '/static/data/r2d2/injectables/footnotes/footnotes.js.map', '/static/data/r2d2/injectables/footnotes/footnotes.css', '/static/data/r2d2/injectables/pagebreak/pagebreak.css', '/static/data/r2d2/reader.css', '/static/data/r2d2/reader.js', '/static/data/r2d2/reader.css.map', '/static/data/r2d2/fonts/opendyslexic/opendyslexic-regular-webfont.woff', '/static/data/r2d2/fonts/opendyslexic/OFL.txt', '/static/data/r2d2/fonts/opendyslexic/opendyslexic-regular-webfont.woff2', '/static/data/r2d2/fonts/opendyslexic/opendyslexic.css', '/static/data/r2d2/material.css', '/static/data/r2d2/readium-css/LICENSE', '/static/data/r2d2/readium-css/ReadiumCSS-before.css', '/static/data/r2d2/readium-css/ReadiumCSS-default.css', '/static/data/r2d2/readium-css/ReadiumCSS-after.css', '/static/data/css/sb-admin-2.min.css', '/static/data/css/player.css', '/static/data/css/media-themes.css', '/static/data/css/transcrobes.css', '/static/data/css/all.min.css', '/static/data/webfonts/fa-solid-900.woff2', '/static/data/js/jquery.mousewheel.min.js', '/static/data/js/Chart.min.js', '/static/data/js/jquery.min.js', '/static/data/js/jquery.easing.min.js', '/static/data/js/bootstrap.bundle.min.js', '/static/data/js/sb-admin-2.min.js', '/static/data/img/tc32.png', '/static/data/img/undraw_customer_survey_f9ur.svg', '/static/data/img/tc128.png', '/static/data/img/ajax-loader.gif', '/static/data/img/favicon.ico', '/static/data/img/tc64.png', '/static/data/img/tc16.png']
  console.debug('static files to cache', static_files)
  let options = {
    method: "GET",
    cache: "no-store",
    headers: {
      "Accept": "application/json",
      "Content-Type": "application/json"
    },
  };
  event.waitUntil(
    fetch(event.target.location.origin + "/precache_urls/", options).then(res => {
      console.debug('I am back from the fetch and the fetch was Ok?', res.ok);
      if (res.ok) {
        return res.json();
      } else {
        console.error(`failure inside fetch res is ${JSON.stringify(res)}`);
        throw 'bad error'
      }
    }).then((json) => {
      console.debug('trying to precache the urls:', json)
      caches.open(CACHE_VERSION).then(function(cache) {
        return cache.addAll(static_files.concat(json));
      })
    })
  );
  console.log("The wonderfulest sw has been installed");
});

self.addEventListener('fetch', function(event) {
  const REFRESHABLES = ["", "import", 'list', 'goal', 'webpub', 'video', 'coming_soon', 'settings'];

  const url = new URL(event.request.url);
  // TODO: this was added to avoid chrome extension fetch caching, though maybe some others like ftp
  // should be allowed?
  if (!["http:", "https:"].includes(url.protocol)) { return; }

  if (self.origin != url.origin) {
    console.debug('matched external offline first then network if not present', url.href);
    event.respondWith(
      caches.open(CACHE_VERSION).then(function (cache) {
        return cache.match(event.request).then(function (response) {
          return (
            response ||
            fetch(event.request).then(function (response) {
              cache.put(event.request, response.clone());
              return response;
            })
          );
        });
      }),
    );
  } else if (REFRESHABLES.includes(url.pathname.split('/')[1])) {
    console.debug('matched, doin da magic', url);
    event.respondWith(caches.match(event.request).then(function (response) {
      const newQuery = fetch(event.request).then(function (response) {
        console.debug('i am back from the new fetch with a new page')
        if (response.ok){
          let responseClone = response.clone();
          caches.open(CACHE_VERSION).then(function (cache) {
            cache.put(event.request, responseClone);
          });
        }
        return response;
      }).catch(function () {
        return caches.match('/offline/');
      });
      return response !== undefined ? response : newQuery;
    })
    )
  } else if (url.pathname.split('/')[1] === "static") {
    console.debug('matched static, caching normally with offline first then network if not present', url.href);
    // FIXME: probably the same as for external, merge!!!
    event.respondWith(
      caches.open(CACHE_VERSION).then(function (cache) {
        return cache.match(event.request).then(function (response) {
          return (
            response ||
            fetch(event.request).then(function (response) {
              cache.put(event.request, response.clone());
              return response;
            })
          );
        });
      }),
    );
  } else {
    console.debug("Got a url that didn't match sw rules", url.href);
  }
});

self.addEventListener('activate', (event) => {
  console.log(`cleaning up in activate with event: ${event}`);
  var cacheKeeplist = [CACHE_VERSION];
  event.waitUntil(
    caches.keys().then((keyList) => {
      return Promise.all(keyList.map((key) => {
        if (cacheKeeplist.indexOf(key) === -1) {
          return caches.delete(key);
        }
      }));
    })
  );
});

function loadDb(message, event) {
  if (!!db) {
    console.debug('DB loaded, using that', db)
    if (!!event) {
      event.source.postMessage({ source: message.source, type: message.type, value: "success" });
    }
    return Promise.resolve(db);
  }
  console.debug('Setting up the db in the service worker');

  if (eventQueueTimer) { clearInterval(eventQueueTimer) };
  // FIXME: there should be a proper way to manage this!!!
  // FIXME: maybe do some validation on the event.data.val?
  const localBaseUrl = new URL(message.value.syncURL).origin;
  utils.setBaseUrl(localBaseUrl);
  utils.setLangPair(message.value.langPair);
  utils.setAccessToken(message.value.jwt_access);
  utils.setRefreshToken(message.value.jwt_refresh);
  utils.setUsername(message.value.username);

  const dbConfig = createRxDBConfig(message.value.syncURL, message.value.username, message.value.jwt_access,
    message.value.jwt_refresh, CACHE_VERSION, !!message.value.reinitialise);
  console.debug(`dbConfig`, dbConfig);

  const progressCallback = (progressMessage, isFinished) => {
    const progress = { message: progressMessage, isFinished };
    console.debug('got the progress message in sw.js', progress);
    if (!!event) {
      event.source.postMessage({ source: message.source, type: message.type + "-progress", value: progress });
    }
  };
  return getDb(dbConfig, progressCallback).then((dbObj) => {
    db = dbObj;
    if (!eventQueueTimer) {
      eventQueueTimer = setInterval(() => data.sendUserEvents(db), utils.EVENT_QUEUE_PROCESS_FREQ);
    }
    console.debug('got the db in getDb in sw.js, replying with ok');
    if (!!event) {
      event.source.postMessage({ source: message.source, type: message.type, value: "success" });
    }
    return Promise.resolve(db);
  });
}

self.addEventListener('message', event => {
  const message = event.data;
  console.debug(`The client sent me a message:`, message);
  // TODO: decide whether to actually do in the worker with idb or localStorage in the proxy...
  // if (message.type == "isDbInitialised") {
  //   console.debug('Checking whether the DB has been initialised');

  //   isDbInitialised().then((result) => {
  //     event.source.postMessage({source: message.source, type: message.type, value: result});
  //   })
  // } else

  if (message.type == "syncDB") {
    loadDb(message, event);
  } else if (message.type === "heartbeat") {
    console.debug('got a heartbeat request in sw.js, replying with datetime');
    event.source.postMessage({source: message.source, type: message.type, value: dayjs().format()});
  } else if (message.type === "getWordFromDBs") {
    loadDb(message).then((ldb) => {
      data.getWordFromDBs(ldb, message.value).then((values) => {
        console.debug('back from data.getWordFromDBs', values)
        event.source.postMessage({ source: message.source, type: message.type, value: (values ? values.toJSON() : null) });
      });
    });
  } else if (message.type === "getCardWords") {
    if (knownCardWordGraphs || allCardWordGraphs || knownWordIdsCounter) {
      console.debug('Returning pre-loaded user card words in sw.js');
      event.source.postMessage({
        source: message.source,
        type: message.type,
        value: [Array.from(knownCardWordGraphs), Array.from(allCardWordGraphs), knownWordIdsCounter]
      });
    } else {
      loadDb(message).then((ldb) => {
        data.getCardWords(ldb).then((values) => {
          console.debug('Loaded user card words from sw.js', values);
          // convert to arrays or Set()s get silently purged in chrome extensions, so
          // need to mirror here for the same return types... Because JS is sooooooo awesome!
          knownCardWordGraphs = values[0]
          allCardWordGraphs = values[1]
          knownWordIdsCounter = values[2]
          event.source.postMessage({
            source: message.source, type: message.type,
            value: [Array.from(knownCardWordGraphs), Array.from(allCardWordGraphs),
              knownWordIdsCounter]
          });
        });
      });
    }
  } else if (message.type === "submitLookupEvents") {
    loadDb(message).then((ldb) => {
      data.submitLookupEvents(ldb, message.value.lookupEvents, message.value.userStatsMode).then((values) => {
        console.debug('submitLookupEvents results in sw.js', message, values);
        event.source.postMessage({ source: message.source, type: message.type, value: 'Lookup Events submitted' });
      });
    });
  } else if (message.type === "getUserListWords") {
    loadDb(message).then((ldb) => {
      data.getUserListWords(ldb).then((values) => {
        console.debug('getUserListWords results in sw.js', message, values);
        event.source.postMessage({ source: message.source, type: message.type, value: values });
      });
    });
  } else if (message.type === "getDefaultWordLists") {
    loadDb(message).then((ldb) => {
      data.getDefaultWordLists(ldb).then((values) => {
        console.debug('getDefaultWordLists results in sw.js', message, values);
        event.source.postMessage({ source: message.source, type: message.type, value: values });
      });
    });
  } else if (message.type === "createCards") {
    loadDb(message).then((ldb) => {
      data.createCards(ldb, message.value).then((values) => {
        console.debug('createCards results in sw.js', message, values);
        const success = values.success.map(x => x.toJSON());
        event.source.postMessage({ source: message.source, type: message.type, value: { error: values.error, success } });
      });
    });
  } else if (message.type === "setContentConfigToStore") {
    loadDb(message).then((ldb) => {
      data.setContentConfigToStore(ldb, message.value).then((values) => {
        console.debug('setContentConfigToStore results in sw.js', message, values);
        event.source.postMessage({ source: message.source, type: message.type, value: 'Content config saved' });
      });
    });
  } else if (message.type === "getCharacterDetails") {
    loadDb(message).then((ldb) => {
      data.getCharacterDetails(ldb, message.value).then((values) => {
        console.debug('getCharacterDetails results in sw.js', message, values);
        event.source.postMessage({ source: message.source, type: message.type, value: values });
      });
    });
  } else if (message.type === "getContentConfigFromStore") {
    loadDb(message).then((ldb) => {
      data.getContentConfigFromStore(ldb, message.value).then((values) => {
        console.debug('getContentConfigFromStore results in sw.js', message, values);
        event.source.postMessage({ source: message.source, type: message.type, value: values });
      });
    });
  } else if (message.type === "getVocabReviews") {
    loadDb(message).then((ldb) => {
      data.getVocabReviews(ldb, message.value).then((values) => {
        console.debug('getVocabReviews results in sw.js', message, values);
        event.source.postMessage({ source: message.source, type: message.type, value: values });
      });
    });
  } else if (message.type === "getSRSReviews") {
    loadDb(message).then((ldb) => {
      data.getSRSReviews(ldb, message.value).then((values) => {
        console.debug('getSRSReviews results in sw.js', message, values);
        // todaysWordIds,  // Set of words reviewed today already: string ids
        // allNonReviewedWordsMap,  // Map of words in selected lists not already reviewed today: RxDocument
        // existingCards,  // Map of all cards reviewed at least once: RxDocument
        // existingWords,  // Map of all words which have had at least one card reviewed at least once: RxDocument
        // potentialWords,  // Array of words that can be "new" words today: RxDocument
        const allNonReviewedWordsMap = new Map();
        for (const [k, v] of values.allNonReviewedWordsMap) { allNonReviewedWordsMap.set(k, v.toJSON()); }
        const existingCards = new Map();
        for (const [k, v] of values.existingCards) { existingCards.set(k, v.toJSON()); }
        const existingWords = new Map();
        for (const [k, v] of values.existingWords) { existingWords.set(k, v.toJSON()); }
        const potentialWords = [];
        for (const pw of values.potentialWords) { potentialWords.push(pw.toJSON()); }
        const allPotentialCharacters = new Map();
        for (const [k, v] of values.allPotentialCharacters) { allPotentialCharacters.set(k, v.toJSON()); }
        const sanitised = {
          todaysWordIds: values.todaysWordIds,
          allNonReviewedWordsMap,
          existingCards,
          existingWords,
          potentialWords,
          allPotentialCharacters,
        }
        event.source.postMessage({ source: message.source, type: message.type, value: sanitised });
      });
    });
  } else if (message.type === "submitUserEvents") {
    loadDb(message).then((ldb) => {
      data.submitUserEvents(ldb, message.value).then((values) => {
        console.debug('submitUserEvents results in sw.js', message, values);
        event.source.postMessage({ source: message.source, type: message.type, value: 'User Events submitted' });
      });
    });
  } else if (message.type === "practiceCard") {
    const { currentCard, grade, badReviewWaitSecs } = message.value;
    loadDb(message).then((ldb) => {
      data.practiceCard(ldb, currentCard, grade, badReviewWaitSecs).then((values) => {
        console.debug("practiceCard in sw.js", message, values);
        event.source.postMessage({ source: message.source, type: message.type, value: (values ? values.toJSON() : null) });
      });
    });
  } else if (message.type === "practiceCardsForWord") {
    const practiceDetails = message.value;
    const { wordInfo, grade } = practiceDetails;
    loadDb(message).then((ldb) => {
      data.practiceCardsForWord(ldb, practiceDetails).then((values) => {
        allCardWordGraphs.add(wordInfo.graph)
        if (grade > GRADE.UNKNOWN) {
          knownCardWordGraphs.add(wordInfo.graph)
          knownWordIdsCounter[wordInfo.wordId] = (knownWordIdsCounter[wordInfo.wordId] ? knownWordIdsCounter[wordInfo.wordId] + 1 : 1)
        }
        console.debug("Practiced in sw.js", message, values);
        event.source.postMessage({ source: message.source, type: message.type, value: 'Cards Practiced' });
      });
    });
  } else if (message.type === "addOrUpdateCards") {
    const { wordId, grade } = message.value;
    loadDb(message).then((ldb) => {
      data.addOrUpdateCards(ldb, wordId, grade).then((cards) => {
        console.debug("addOrUpdateCards in sw.js", cards);
        event.source.postMessage({ source: message.source, type: message.type, value: cards.map(x => x.toJSON()) });
      });
    });
  } else if (message.type === "getWordDetails") {
    const { graph } = message.value;
    loadDb(message).then((ldb) => {
      data.getWordDetails(ldb, graph).then((details) => {
        console.debug("getWordDetails in sw.js", details);
        const safe = {
          word: details.word ? details.word.toJSON() : null,
          cards: [...details.cards.values()].map(x => x.toJSON()),
          characters: [...details.characters.values()].map(x => x.toJSON()),
          wordModelStats: details.wordModelStats ? details.wordModelStats.toJSON() : null,
        }
        console.debug("safe getWordDetails in sw.js", safe);
        event.source.postMessage({ source: message.source, type: message.type, value: safe });
      });
    });
  } else {
    console.warn('Service Worker received a message event that I had no manager for', event)
  }
});
