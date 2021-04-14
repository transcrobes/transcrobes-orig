import * as components from '../../js/components.js';
import { BackgroundWorkerProxy } from '../../js/proxies.js';

window.transcrobesModel = {};
let transcroberObserver;

// let readObserver = new IntersectionObserver(components.onScreen, {
//   threshold: [1.0],
//   // FIXME: decide whether it is worth trying to use V2 of the IntersectionObserver API
//   // Track the actual visibility of the element
//   // trackVisibility: true,
//   // Set a minimum delay between notifications
//   // delay: 1000,  //at 1sec, we are conservative and shouldn't cause huge load
// });

// the callback function that will be fired when the element apears in the viewport

function onEntryId(entry) {
  entry.forEach((change) => {
    if (!change.isIntersecting) return;
    if (change.target.dataset && change.target.dataset.tced) return;
      change.target.childNodes.forEach((item) => {
        if (item.nodeType == 3) {
          console.log('trying to get' + item.nodeValue);
          components.fetchPlus(components.baseUrl + 'enrich/aenrich_json', {
            data: item.nodeValue,
          }, components.DEFAULT_RETRIES)
            .then(data => {
              let etf = document.createElement('enriched-text-fragment');
              // FIXME: this appears not to be usable on the other side in chrome extensions
              // etf.setAttribute('data-model', JSON.stringify(data));
              transcrobesModel[data["id"]] = data;
              etf.setAttribute('id', data["id"]);
              // FIXME: this appears not to be usable on the other side in chrome extensions so not setting here
              // etf.appendChild(document.createTextNode(item.nodeValue));
              item.replaceWith(etf);
              change.target.dataset.tced = true;
            }).catch((err) => {
              console.log(err);
            });
        }
      });
  });
}

function enrichDocument() {
  components.textNodes(document.body).forEach((textNode) => {
    if (!components.toEnrich(textNode.nodeValue)) {
      console.log("Not enriching: " + textNode.nodeValue);
      return;
    }
    transcroberObserver.observe(textNode.parentElement);
  });

  document.addEventListener('click', () => {
    document.querySelectorAll("token-details").forEach(el => el.remove());
  });
}

transcroberObserver = new IntersectionObserver(onEntryId, { threshold: [0.9] });
const platformHelper = new BackgroundWorkerProxy()
components.setPlatformHelper(platformHelper);
components.defineElements();

chrome.storage.local.get({
  username: '',
  password: '',
  baseUrl: '',
  glossing: ''
}, function (items) {
  components.setUsername(items.username);
  components.setPassword(items.password);
  components.setBaseUrl(items.baseUrl + (items.baseUrl.endsWith('/') ? '' : '/'));
  components.setGlossing(items.glossing);

  components.fetchWithNewToken().then(() => {
    if (!(components.accessToken)) {
      alert('Something is wrong, we could not authenticate. ' +
        'Please refresh the page before attempting this action again');
      return;  // TODO: offer to reload from here
    } else {
      platformHelper.init({
        jwt_access: components.accessToken,
        jwt_refresh: components.refreshToken,
        lang_pair: components.langPair,
        username: components.username,
      },
        (message) => {
          console.debug('In the init callback, starting to enrich the document', message)
          enrichDocument()
        },
        (progress) => {
          console.debug('Init progressCallback', progress)
        }
      )
    }
  });
  return Promise.resolve({ response: 'Running enrich' });
});
