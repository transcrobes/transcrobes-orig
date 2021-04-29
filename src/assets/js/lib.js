// I am genuinely not intelligent enough to code like a proper human being in js
// It is a horrible language, written by horrible people, for horrible people
// ¯_(ツ)_/¯

const EVENT_QUEUE_PROCESS_FREQ = 5000; //milliseconds
const ONSCREEN_DELAY_IS_CONSIDERED_READ = 5000; // milliseconds

const REFRESH_TOKEN_PATH = 'api/token/refresh/';
const ACCESS_TOKEN_PATH = 'api/token/';

const DEFAULT_RETRIES = 3;

const USER_STATS_MODE = {
  IGNORE: -1,
  UNMODIFIED: 0,
  NO_GLOSS: 2,  // segmented
  L2_SIMPLIFIED: 4,  // e.g, using "simple" Chinese characters
  TRANSLITERATION: 6,  // e.g, pinyin
  L1: 8  // e.g, English
}

const ZH_TB_POS_TO_SIMPLE_POS = {
  // see src/enrichers/zhhans/__init__.py for more details, if that is updated, then this should be too
  // TODO: consider getting/updating this via the API, to guarantee python and js always agree
  "AD": "ADV",  // adverb
  "AS": "OTHER",  // aspect marker
  "BA": "OTHER",  // in ba-construction ,
  "CC": "CONJ",  // coordinating conjunction
  "CD": "DET",  // cardinal number
  "CS": "CONJ",  // subordinating conjunction
  "DEC": "OTHER",  // in a relative-clause
  "DEG": "OTHER",  // associative
  "DER": "OTHER",  // in V-de const. and V-de-R
  "DEV": "OTHER",  // before VP
  "DT": "DET",  // determiner
  "ETC": "OTHER",  // for words , ,
  "FW": "OTHER",  // foreign words
  "IJ": "OTHER",  // interjection
  "JJ": "ADJ",  // other noun-modifier ,
  "LB": "OTHER",  // in long bei-const ,
  "LC": "OTHER",  // localizer
  "M": "OTHER",  // measure word
  "MSP": "OTHER",  // other particle
  "NN": "NOUN",  // common noun
  "NR": "NOUN",  // proper noun
  "NT": "NOUN",  // temporal noun
  "OD": "DET",  // ordinal number
  "ON": "OTHER",  // onomatopoeia ,
  "P": "PREP",  // preposition excl. and
  "PN": "PRON",  // pronoun
  "PU": "OTHER",  // punctuation
  "SB": "OTHER",  // in short bei-const ,
  "SP": "OTHER",  // sentence-final particle
  "VA": "ADJ",  // predicative adjective
  "VC": "VERB",
  "VE": "VERB",  // as the main verb
  "VV": "VERB",  // other verb
  // Others added since then
  "URL": "OTHER",
}

let accessToken = '';
let refreshToken = '';

let langPair = '';
let username = '';
let password = '';
let baseUrl = '';
let glossing = -1;
let fontSize = 100;
let segmentation = true;
let themeName = 'dark';
let eventSource = 'lib.js';
var parseModels = {};
var l1Models = {};
var glossNumberNouns = false;
var onScreenDelayIsConsideredRead = ONSCREEN_DELAY_IS_CONSIDERED_READ;

function setAccessToken(value) { accessToken = value; }
function setRefreshToken(value) { refreshToken = value; }
function setUsername(value) { username = value; }
function setLangPair(value) { langPair = value; }
function setPassword(value) { password = value; }
function setBaseUrl(value) { baseUrl = (new URL(value)).origin + '/'; }
function setGlossing(value) { glossing = value; }
function setGlossNumberNouns(value) { glossNumberNouns = value; }
function setOnScreenDelayIsConsideredRead(value) { onScreenDelayIsConsideredRead = value; }
function setFontSize(value) { fontSize = value; }
function setSegmentation(value) { segmentation = value; }
function setThemeName(value) { themeName = value; }
function setEventSource(value) { eventSource = value; }

function fromLang() {
  return langPair.split(':')[0];
}

function toSimplePos(complexPos){
  if (fromLang() == 'zh-Hans'){
    return ZH_TB_POS_TO_SIMPLE_POS[complexPos];
  }
  throw `Unknown from language "${fromLang()}", can\'t find standard/simple POS`;
}

function UUID() {
  return Date.now().toString(36) + Math.random().toString(36).substring(2);
};

function sortByWcpm(a, b) {
  const aa = parseFloat(a.frequency.wcpm);
  const bb = parseFloat(b.frequency.wcpm);
  if (isNaN(bb)) { return -1 };
  if (isNaN(aa)) { return 1 };
  return bb - aa;
}

function shortMeaning(providerTranslations){
  for (const provTranslation of providerTranslations) {
    if (provTranslation.posTranslations.length > 0) {
      let meaning = '';
      for (const posTranslation of provTranslation.posTranslations) {
        meaning += `${posTranslation.posTag}: ${posTranslation.values.join(', ')}; `;
      }
      return meaning;
    }
  }
  return "";
}

function apiUnavailable(message, doc=document) {
  // close the popup if it's open
  doc.querySelectorAll(".tcrobe-def-popup").forEach(el => el.remove());

  const error = doc.createElement('div');
  error.appendChild(doc.createTextNode(`Transcrobes Server ${baseUrl} Unavailable. ${message}`));
  error.style.position = "fixed";
  error.style.width = "100%";
  error.style.height = "60px";
  error.style.top = "0";
  error.style.backgroundColor = "red";
  error.style.fontSize = "large";
  error.style.textAlign = "center";
  error.style.zIndex = 1000000;
  doc.body.prepend(error);
}

function dbSynchingOverlay(element, message) {
  element.id = "db-synching-overlay";
  element.style.display = "block";
  element.style.position = "fixed";
  element.style.width = "100%";
  element.style.height = "100%";
  element.style.top = "0px";
  element.style.left = "0px";
  element.style.opacity = "0.9";
  element.style.backgroundColor = "#ccc";
  element.style.color = "#000";
  element.style.fontSize = "large";
  element.style.textAlign = "center";
  element.style.zIndex = 100000;
}

function toggleFullscreen(doc, videoWrapper) {
  console.log('running toggleFullscreen');
  if (doc.fullscreenElement)
    { exitFullscreen(doc) }  //
  else
    { launchFullscreen(videoWrapper); }
}

// Find the right method, call on correct element
function launchFullscreen(element) {
  if(element.requestFullscreen) {
    element.requestFullscreen();
  } else if(element.mozRequestFullScreen) {
    element.mozRequestFullScreen();
  } else if(element.webkitRequestFullscreen) {
    element.webkitRequestFullscreen();
  } else if(element.msRequestFullscreen) {
    element.msRequestFullscreen();
  }
}

function exitFullscreen(doc) {
  if(doc.exitFullscreen) {
    doc.exitFullscreen();
  } else if(doc.mozCancelFullScreen) {
    doc.mozCancelFullScreen();
  } else if(doc.webkitExitFullscreen) {
    doc.webkitExitFullscreen();
  }
}

function filterKnown(knownNoteBases, knownNotes, words, minMorphemeKnownCount=2, preferWholeKnownWords=true) {
  if (words.length == 0) { return []; } // or null?

  const known = [];
  const wholeKnownWords = [];
  for (const word of words) {
    if (knownNotes.has(word)) {
      if (preferWholeKnownWords) {
        wholeKnownWords.push(word);
      } else {
        known.push(word);
      }
    }
    else if (minMorphemeKnownCount > 0) {
      let good = true;
      for (const character of Array.from(word)) {
        if (!(character in knownNoteBases) || knownNoteBases[character] < minMorphemeKnownCount) {
          good = false;
          break;
        }
      }
      if (good) {
        known.push(word);
      }
    }
  }
  return wholeKnownWords.concat(known);
}

function pythonCounter(value) {
  const array = Array.isArray(value) ? value : Array.from(value);
  const count = {};
  array.forEach(val => count[val] = (count[val] || 0) + 1);
  return count;
}

function toEnrich(charstr, fromLanguage) {
  // TODO: find out why the results are different if these consts are global...
  const zhReg = /[\u4e00-\u9fff]+/gi;
  const enReg = /[[A-z]+/gi;
  switch (fromLanguage || fromLang()) {
    case 'en':
      return enReg.test(charstr);
    case 'zh-Hans':
      return zhReg.test(charstr);
    default:
      return false;
  }
};

function simpOnly(query) {
  return (toEnrich(query, 'zh-Hans') && (query === query.replace(/[\x00-\x7F]/g, "")))
}

function parseJwt(token) {
    // TODO: this will apparently not do unicode properly. For the moment we don't care.
    var base64Url = token.split('.')[1];
    var base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    return JSON.parse(atob(base64));
};

function textNodes(node) {
  return walkNodeTree(node, {
    inspect: n => !['STYLE', 'SCRIPT'].includes(n.nodeName),
    collect: n => (n.nodeType === 3) && n.nodeValue && n.nodeValue.match(/\S/),
    //callback: n => console.log(n.nodeName, n),
  });
}

function walkNodeTree(root, options) {
  options = options || {};
  const inspect = options.inspect || (n => true),
    collect = options.collect || (n => true);
  const walker = root.ownerDocument.createTreeWalker(
    root,
    NodeFilter.SHOW_ALL,
    {
      acceptNode: function (node) {
        if (!inspect(node)) { return NodeFilter.FILTER_REJECT; }
        if (!collect(node)) { return NodeFilter.FILTER_SKIP; }
        return NodeFilter.FILTER_ACCEPT;
      }
    }
  );

  const nodes = []; let n;
  while (n = walker.nextNode()) {
    options.callback && options.callback(n);
    nodes.push(n);
  }

  return nodes;
}

function onError(e) {
    console.error(e);
};

function fetchWithNewToken(url, body = {}, retries, apiUnavailableCallback) {
  console.debug(`Doing a fetchWithNewToken to ${url}`);
  let fetchInfo;
  let reAuthUrl;
  if (refreshToken) {  //
    fetchInfo = {
      method: "POST",
      cache: "no-store",
      body: JSON.stringify({ refresh: refreshToken }),
      headers: { "Accept": "application/json", "Content-Type": "application/json" },
    };
    reAuthUrl = baseUrl + REFRESH_TOKEN_PATH;
  } else if (password) {
    fetchInfo = {
      method: "POST",
      cache: "no-store",
      body: JSON.stringify({ username: username, password: password }),
      headers: { "Accept": "application/json", "Content-Type": "application/json" },
    };
    reAuthUrl = baseUrl + ACCESS_TOKEN_PATH;
  } else {
    throw "I have neither a refreshToken nor a password, and I want a new token. That's problematic..."
  }
  console.debug(`Doing a token refresh/get to ${reAuthUrl} with fetchInfo`, fetchInfo);
  return fetch(reAuthUrl, fetchInfo)
    .then(res => {
      if (res.ok) {
        return res.json();
      }
      throw new Error(res.status);
    })
    .then(data => {
      console.debug(`The token refresh/get went Ok, I got back`, data);
      if (data.access) {
        accessToken = data.access;
        if (!!data.refresh) {
          refreshToken = data.refresh;
        }
        langPair = parseJwt(accessToken)['lang_pair'];
        if (Object.keys(body).length === 0 && body.constructor === Object) {
          // we just wanted to get the tokens
          return Promise.resolve({ accessToken, refreshToken, langPair, });
        } else {
          return fetchPlus(url, body, retries, apiUnavailableCallback);
        }
      }
    }).catch(error => {
      let errorMessage = `${url}: ${JSON.stringify(fetchInfo)}: ${error.message}`
      console.log(errorMessage);
    });
}

function addAuthHeader(options) {
  if (typeof csrftoken !== 'undefined') {
    // the variable is defined
    options.headers["X-CSRFToken"] = csrftoken;
  } else if (!!accessToken) {
    options.headers["Authorization"] = "Bearer " + accessToken;
  } else if (!!username && !!password) {
    options.headers["Authorization"] = "Basic "  + btoa(username + ":" + password);
  } else {
    console.warn("addAuthHeader has no auth type available")
  }
  return options;
}

function fetchPlus(url, body, retries, apiUnavailableCallback, doc, accept_type='json') {
  let options = {
    method: "POST",
    cache: "no-store",
    body: !!body ? JSON.stringify(body) : null,
    headers: { "Accept": (accept_type === 'json') ? "application/json" : "text/html",
      "Content-Type": "application/json" }, };
  options = addAuthHeader(options);
  console.debug(`trying to send to ${url} with options`, options);

  return fetch(url, options)
    .then(res => {
      if (res.ok) {
        return (accept_type === 'json') ? res.json() : res.text();
      } else { console.warn(`Failure inside fetch res is`, res); }

      if (retries > 0 && res.status == 401) {
        return fetchWithNewToken(url, JSON.parse(options.body), retries - 1, apiUnavailableCallback, doc);
      }
      if (retries > 0) { return fetchPlus(url, JSON.parse(options.body), retries - 1, apiUnavailableCallback, doc) }

      if (apiUnavailableCallback) {
        if (res.status == 401)
          apiUnavailableCallback("Please make sure your username and password are correct", doc);
        else
          apiUnavailableCallback("Please make sure you have the latest browser extension, or try again later", doc);
      }
      throw new Error(res.status)
    }).catch(error => {
      console.error('Fetch failed hard', url, options, error);
      throw new Error(error);
    });
}

const getVoices = () => {
  return new Promise(resolve => {
    let voices = speechSynthesis.getVoices()
    if (voices.length) {
      resolve(voices)
      return;
    }
    speechSynthesis.onvoiceschanged = () => {
      voices = speechSynthesis.getVoices()
      resolve(voices)
    }
  })
}

function say(text, voice, lang='zh-CN') {
  const synth = window.speechSynthesis;
  console.debug(`I've been asked to say`, text)
  if (voice && voice.lang !== lang) {
    throw "The language of the voice and lang must be the same"
  }
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = lang;
  if (voice)  {
    console.debug('Given a voice, saying directly');
    utterance.voice = voice;
    synth.speak(utterance);
  } else {
    console.debug('getting voices then saying');
    getVoices().then((voices) => {
      console.debug('Got voices', voices);
      utterance.voice = voices.filter(x => x.lang == lang && !x.localService)[0]
        || voices.filter(x => x.lang == lang)[0];
      console.debug(`using voice`, utterance.voice)
      synth.speak(utterance);
    })
  }
}

export {
  // constants and variables
  DEFAULT_RETRIES,
  EVENT_QUEUE_PROCESS_FREQ,
  ONSCREEN_DELAY_IS_CONSIDERED_READ,
  USER_STATS_MODE,

  accessToken,
  refreshToken,
  username,
  langPair,
  password,
  baseUrl,
  glossing,
  fontSize,
  segmentation,
  onScreenDelayIsConsideredRead,
  themeName,
  parseModels,
  l1Models,
  glossNumberNouns,

  // property setters
  setAccessToken,
  setRefreshToken,
  setUsername,
  setPassword,
  setLangPair,
  setBaseUrl,
  setGlossing,
  setGlossNumberNouns,
  setFontSize,
  setSegmentation,
  setOnScreenDelayIsConsideredRead,
  setThemeName,
  setEventSource,

  // functions
  addAuthHeader,
  fetchPlus,
  toEnrich,
  simpOnly,
  parseJwt,
  onError,
  textNodes,
  fetchWithNewToken,
  filterKnown,
  toggleFullscreen,
  toSimplePos,
  say,
  pythonCounter,
  sortByWcpm,
  shortMeaning,
  UUID,
}
