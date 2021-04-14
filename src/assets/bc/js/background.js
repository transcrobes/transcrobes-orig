import * as utils from '../../js/lib.js';
import * as data from '../../js/data.js';
import { GRADE, CACHE_NAME } from '../../js/schemas.js';
import { getDb, createRxDBConfig } from '../../js/syncdb.js';
import dayjs from 'dayjs';

utils.setEventSource('chrome-extension');

var db;

let allCardWordGraphs;
let knownCardWordGraphs;
let knownWordIdsCounter;

let eventQueueTimer;

function stopEventsSender(timerId) {
  clearTimeout(timerId || eventQueueTimer);
}

function loadDb(callback, message) {
  if (!!db) {
    console.debug('DB loaded, using that', db)
    callback({ source: message.source, type: message.type, value: "success" });
    return Promise.resolve(db);
  }
  clearTimeout(timerId || eventQueueTimer);
  chrome.storage.local.get({ username: '', password: '', baseUrl: '', glossing: ''
      }, (items) => {
    console.debug('DB NOT loaded, (re)loading', db)
    utils.setUsername(items.username);
    utils.setPassword(items.password);
    const baseUrl = items.baseUrl + (items.baseUrl.endsWith('/') ? '' : '/')
    utils.setBaseUrl(baseUrl);
    utils.setGlossing(items.glossing);
    const recreate = false;

    const progressCallback = (progressMessage, isFinished) => {
      const progress = { message: progressMessage, isFinished };
      console.debug('Got the progress message in background.js', progress);
      // MUST NOT SEND A RESPONSE HERE!!!!!
      // sendResponse({source: message.source, type: message.type + "-progress", value: progress});
    };
    utils.fetchWithNewToken().then((tokens) => {
      console.debug('Returned with tokens', tokens)
      const dbConfig = createRxDBConfig(utils.baseUrl, utils.username, tokens.accessToken, tokens.refreshToken,
        CACHE_NAME, recreate);
      return getDb(dbConfig, progressCallback).then((dbHandle) => {
        db = dbHandle;
        console.debug('db object after getDb is', dbHandle)
        if (!eventQueueTimer) {
          eventQueueTimer = setInterval(() => data.sendUserEvents(db), utils.EVENT_QUEUE_PROCESS_FREQ);
        }
        callback({ source: message.source, type: message.type, value: "success" });
        return Promise.resolve(db);
      }).catch(err => {
        console.error('getDb() threw an error:', err);
      });
    });
  });
}

chrome.browserAction.onClicked.addListener(
  function(message, callback) {
    console.debug('Browser action triggered with message', message);
    chrome.tabs.executeScript({ file: 'webcomponents-sd-ce.js' });
    chrome.tabs.executeScript({ file: 'content-bundle.js' });
  }
);

chrome.runtime.onMessage.addListener(
  (request, _sender, sendResponse) => {
    const message = request;
    // TODO: decide whether to actually do in the worker with idb or localStorage in the proxy...
    if (message.type == "isDbInitialised") {
      console.debug('Checking whether the DB has been initialised');
      const result = !!(localStorage.getItem('isDbInitialised'));
      sendResponse({source: message.source, type: message.type, value: result});
    } else if (message.type === "syncDB") {
      console.log('Starting a background syncDB db load');
      loadDb(sendResponse, message);
    } else if (message.type === "heartbeat") {
      console.debug('got a heartbeat request in sw.js, replying with datetime');
      sendResponse({source: message.source, type: message.type, value: dayjs().format()});
    } else if (message.type === "getWordFromDBs") {
      loadDb(console.debug, message).then((ldb) => {
        console.debug('We have a loaded db in background, using that for getWordFromDBs', ldb)
        data.getWordFromDBs(ldb, message.value).then((values) => {
          console.debug('back from data.getWordFromDBs', values)
          sendResponse({ source: message.source, type: message.type, value: values.toJSON() });
        });
      });
    } else if (message.type === "getCardWords") {
      if (knownCardWordGraphs || allCardWordGraphs || knownWordIdsCounter) {
        sendResponse({
          source: message.source,
          type: message.type,
          value: [Array.from(knownCardWordGraphs), Array.from(allCardWordGraphs), knownWordIdsCounter]
        });
      } else {
        loadDb(console.debug, message).then((ldb) => {
          data.getCardWords(ldb).then((values) => {
            // convert to arrays or Set()s get silently purged... Because JS is sooooooo awesome!
            knownCardWordGraphs = values[0]
            allCardWordGraphs = values[1]
            knownWordIdsCounter = values[2]
            sendResponse({
              source: message.source, type: message.type,
              value: [Array.from(knownCardWordGraphs), Array.from(allCardWordGraphs),
                knownWordIdsCounter]
            });
          });
        });
      }
    } else if (message.type === "submitLookupEvents") {
      loadDb(console.debug, message).then((ldb) => {
        data.submitLookupEvents(ldb, message.value.lookupEvents, message.value.userStatsMode).then((values) => {
          console.debug('submitLookupEvents results in background.js', message, values);
          sendResponse({ source: message.source, type: message.type, value: 'Lookup Events submitted' });
        });
      });
    } else if (message.type === "submitUserEvents") {
      loadDb(console.debug, message).then((ldb) => {
        data.submitUserEvents(ldb, message.value).then((values) => {
          console.debug(message, values);
          sendResponse({ source: message.source, type: message.type, value: 'User Events submitted' });
        });
      });
    } else if (message.type === "practiceCardsForWord") {
      const practiceDetails = message.value;
      const { wordInfo, grade } = practiceDetails;
      loadDb(console.debug, message).then((ldb) => {
        data.practiceCardsForWord(ldb, practiceDetails).then((values) => {
          allCardWordGraphs.add(wordInfo.graph)
          if (grade > GRADE.UNKNOWN) {
            knownCardWordGraphs.add(wordInfo.graph)
            knownWordIdsCounter[wordInfo.wordId] = (knownWordIdsCounter[wordInfo.wordId] ? knownWordIdsCounter[wordInfo.wordId] + 1 : 1)
          }
          console.debug("Practiced", message, values);
          sendResponse({ source: message.source, type: message.type, value: 'Cards Practiced' });
        });
      });
    }
    return true;
  }
);
