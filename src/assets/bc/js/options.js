import * as utils from '../../js/lib.js';
import * as syncdb from '../../js/syncdb.js';
import { CACHE_NAME } from '../../js/schemas.js';
// const CACHE_NAME = "v1";

// Saves options to chrome.storage
function saveOptions(recreate) {
  utils.setUsername(document.getElementById("username").value);
  utils.setPassword(document.getElementById("password").value);
  let baseUrl = document.getElementById("base-url").value;
  utils.setBaseUrl(baseUrl.endsWith('/') ? baseUrl : baseUrl + '/');
  utils.setGlossing(document.getElementById("glossing").value);

  chrome.storage.local.set({
    username: utils.username,
    password: utils.password,
    baseUrl: utils.baseUrl,
    glossing: utils.glossing
  }, () => {
    // Update status to let user know options were saved.
    const status = document.getElementById('status');
    status.textContent = 'Options saved.';

    utils.fetchWithNewToken().then(() => {
      if (!(utils.accessToken)) {
        status.textContent = 'There was an error starting the initial synchronisation. Please try again in a short while.';
        utils.onError('Something bad happened, couldnt get an accessToken to start a syncDB()');
      } else {
        status.textContent = "";

        document.querySelector("#intro").classList.add('hidden');
        document.querySelector("#initialisation").classList.remove('hidden');
        document.querySelector("#save").disabled = true;
        document.querySelector("#reinitialise").disabled = true;

        const dbConfig = syncdb.createRxDBConfig(utils.baseUrl, utils.username, utils.accessToken, utils.refreshToken,
          CACHE_NAME, recreate);
        console.debug(`dbConfig in options.js`, dbConfig);

        let finished = false;
        const progressCallback = (message) => {
          console.debug("progressCallback in options.js", message);
          document.querySelector("#initialisationMessages").innerText = message;
        }
        syncdb.getDb(dbConfig, progressCallback).then((db) => {
            window.transcrobesDb = db;
            document.querySelector("#loading").classList.add('hidden');
            document.querySelector("#initialisationMessages").innerText = "Initialisation Complete!";
            console.debug("Synchronisation finished!");
            document.querySelector("#save").disabled = false;
            document.querySelector("#reinitialise").disabled = false;
            chrome.storage.local.set({ isDbInitialised: 'true'}, () => {
              console.debug('Set isDbInitialised to true');
            });
            finished = true;
          }).catch(err => {
            document.querySelector("#initialisationMessages").innerHTML = `There was an error setting up Transcrobes.
              Please try again in a little while, or contact Transcrobes support (<a href="https://transcrob.es/page/contact/">here</a>)`;
            console.log('getDb() threw an error in options.js');
            console.dir(err);
            console.error(err);
        });
      }
    });
  });
}

// Restores select box and checkbox state using the preferences
// stored in chrome.storage.
function restoreOptions() {
  chrome.storage.local.get({
    username: '',
    password: '',
    baseUrl: '',
    glossing: ''
  }, (items) => {
    document.getElementById('username').value = items.username;
    document.getElementById('password').value = items.password;
    document.getElementById('base-url').value = items.baseUrl;
    document.getElementById('glossing').value = items.glossing;
  });
}

document.addEventListener('DOMContentLoaded', restoreOptions);
document.getElementById('save').addEventListener('click', () => saveOptions(false));
document.getElementById('reinitialise').addEventListener('click', () => saveOptions(true));

chrome.storage.local.get(['isDbInitialised'], (result) => {
  console.log('resutl', result);
  if (result.isDbInitialised) {
    document.getElementById('reinitialise').classList.remove('hidden');
  }
})
