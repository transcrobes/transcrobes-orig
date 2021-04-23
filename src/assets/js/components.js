import * as utils from './lib.js';
export * from './lib.js';
import HTMLParsedElement from 'html-parsed-element';
import { GRADE } from './schemas.js';

const SEGMENTED_BASE_PADDING = 6;
const EVENT_SOURCE = "components.js";
const DATA_SOURCE = EVENT_SOURCE;

let userCardWords;
const timeouts = {};
let readObserver = new IntersectionObserver(onScreen, {
  threshold: [1.0],
  // FIXME: decide whether it is worth trying to use V2 of the IntersectionObserver API
  // Track the actual visibility of the element
  // trackVisibility: true,
  // Set a minimum delay between notifications
  // delay: 1000,  //at 1sec, we are conservative and shouldn't cause huge load
});


// FIXME: don't do here?
// utils.setEventSource('components-js');

// default to being the current document, but allow setting for cases where we have iframes, fullscreen elements, etc
let popupParent = document.body;
function setPopupParent(value) { popupParent = value}

let platformHelper;
function setPlatformHelper(value) { platformHelper = value }

const SVG_SOLID_PLUS = {
  viewBox: "0 0 448 512",
  d: "M416 208H272V64c0-17.67-14.33-32-32-32h-32c-17.67 0-32 14.33-32 32v144H32c-17.67 0-32 14.33-32 32v32c0 17.67 14.33 32 32 32h144v144c0 17.67 14.33 32 32 32h32c17.67 0 32-14.33 32-32V304h144c17.67 0 32-14.33 32-32v-32c0-17.67-14.33-32-32-32z",
}
const SVG_SOLID_CHECK = {
  viewBox: "0 0 512 512",
  d: "M173.898 439.404l-166.4-166.4c-9.997-9.997-9.997-26.206 0-36.204l36.203-36.204c9.997-9.998 26.207-9.998 36.204 0L192 312.69 432.095 72.596c9.997-9.997 26.207-9.997 36.204 0l36.203 36.204c9.997 9.997 9.997 26.206 0 36.204l-294.4 294.401c-9.998 9.997-26.207 9.997-36.204-.001z",
}
const SVG_SOLID_EXPAND = {
  viewBox: "0 0 448 512",
  d: "M0 180V56c0-13.3 10.7-24 24-24h124c6.6 0 12 5.4 12 12v40c0 6.6-5.4 12-12 12H64v84c0 6.6-5.4 12-12 12H12c-6.6 0-12-5.4-12-12zM288 44v40c0 6.6 5.4 12 12 12h84v84c0 6.6 5.4 12 12 12h40c6.6 0 12-5.4 12-12V56c0-13.3-10.7-24-24-24H300c-6.6 0-12 5.4-12 12zm148 276h-40c-6.6 0-12 5.4-12 12v84h-84c-6.6 0-12 5.4-12 12v40c0 6.6 5.4 12 12 12h124c13.3 0 24-10.7 24-24V332c0-6.6-5.4-12-12-12zM160 468v-40c0-6.6-5.4-12-12-12H64v-84c0-6.6-5.4-12-12-12H12c-6.6 0-12 5.4-12 12v124c0 13.3 10.7 24 24 24h124c6.6 0 12-5.4 12-12z",
}
const SVG_SOLID_COMPRESS = {
  viewBox: "0 0 448 512",
  d: "M436 192H312c-13.3 0-24-10.7-24-24V44c0-6.6 5.4-12 12-12h40c6.6 0 12 5.4 12 12v84h84c6.6 0 12 5.4 12 12v40c0 6.6-5.4 12-12 12zm-276-24V44c0-6.6-5.4-12-12-12h-40c-6.6 0-12 5.4-12 12v84H12c-6.6 0-12 5.4-12 12v40c0 6.6 5.4 12 12 12h124c13.3 0 24-10.7 24-24zm0 300V344c0-13.3-10.7-24-24-24H12c-6.6 0-12 5.4-12 12v40c0 6.6 5.4 12 12 12h84v84c0 6.6 5.4 12 12 12h40c6.6 0 12-5.4 12-12zm192 0v-84h84c6.6 0 12-5.4 12-12v-40c0-6.6-5.4-12-12-12H312c-13.3 0-24 10.7-24 24v124c0 6.6 5.4 12 12 12h40c6.6 0 12-5.4 12-12z",
}

// <div>Icons made by <a href="https://www.flaticon.com/authors/alfredo-hernandez" title="Alfredo Hernandez">Alfredo Hernandez</a> from <a href="https://www.flaticon.com/" title="Flaticon">www.flaticon.com</a></div>
const SVG_HAPPY_4 = {
  viewBox: "0 0 490 490",
  d: "M69.086,490h351.829C459.001,490,490,459.001,490,420.914V69.086C490,30.991,459.001,0,420.914,0H69.086 C30.999,0,0,30.991,0,69.086v351.829C0,459.001,30.999,490,69.086,490z M332.349,132.647c23.551,0,42.642,19.091,42.642,42.641 c0,23.551-19.091,42.642-42.642,42.642c-23.55,0-42.641-19.091-42.641-42.642C289.708,151.738,308.799,132.647,332.349,132.647z M352.292,300.927l18.303,24.554c-41.676,31.089-83.486,41.452-120.691,41.452c-73.886,0-129.693-40.853-130.53-41.466 l18.333-24.539C142.104,304.186,246.436,379.882,352.292,300.927z M157.651,132.647c23.55,0,42.641,19.091,42.641,42.641 c0,23.551-19.091,42.642-42.641,42.642c-23.551,0-42.642-19.091-42.642-42.642C115.009,151.738,134.1,132.647,157.651,132.647z",
}

const SVG_SAD = {
  viewBox: "0 0 490 490",
  d: "M69.086,490h351.829C459.001,490,490,459.001,490,420.914V69.086C490,30.991,459.001,0,420.914,0H69.086 C30.991,0,0,30.991,0,69.086v351.829C0,459.001,30.991,490,69.086,490z M336.875,348.06h-183.75v-30.625h183.75V348.06z M332.349,132.647c23.551,0,42.642,19.091,42.642,42.641c0,23.551-19.091,42.642-42.642,42.642 c-23.55,0-42.641-19.091-42.641-42.642C289.708,151.738,308.799,132.647,332.349,132.647z M157.651,132.647 c23.55,0,42.641,19.091,42.641,42.641c0,23.551-19.091,42.642-42.641,42.642c-23.551,0-42.642-19.091-42.642-42.642 C115.009,151.738,134.1,132.647,157.651,132.647z",
}

const SVG_SAD_7 = {
  viewBox: "0 0 490 490",
  d: "M69.086,490h351.829C459.001,490,490,459.001,490,420.914V69.086C490,30.991,459.001,0,420.914,0H69.086 C30.999,0,0,30.991,0,69.086v351.829C0,459.001,30.999,490,69.086,490z M332.349,132.647c23.551,0,42.642,19.091,42.642,42.641 c0,23.551-19.091,42.642-42.642,42.642c-23.55,0-42.641-19.091-42.641-42.642C289.708,151.738,308.799,132.647,332.349,132.647z M370.61,339.597l-18.303,24.554c-105.797-78.91-210.188-3.26-214.584,0l-18.333-24.539 C120.646,338.684,246.196,246.787,370.61,339.597z M157.651,132.647c23.55,0,42.641,19.091,42.641,42.641 c0,23.551-19.091,42.642-42.641,42.642c-23.551,0-42.642-19.091-42.642-42.642C115.009,151.738,134.1,132.647,157.651,132.647z",
}

const GRADE_SVGS = {
  [GRADE.UNKNOWN]: SVG_SAD_7,
  [GRADE.HARD]: SVG_SAD,
  [GRADE.GOOD]: SVG_HAPPY_4,
  [GRADE.KNOWN]: SVG_SOLID_CHECK,
}

function createSVG(template, elClass, elAttrs, elParent){
  const el = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  if (!!(elClass)) {
    let arr = Array.isArray(elClass) ? elClass : elClass.split(' ');
    arr.forEach(cssClass => el.classList.add(cssClass));
  }
  if (!!(elAttrs)) {
    for (let attr of elAttrs) {
      el.setAttribute(attr[0], attr[1]);
    }
  }
  if (!!(elParent)) {
    elParent.appendChild(el);
  }
  el.setAttribute('viewBox', template.viewBox);
  const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  path.setAttribute('d', template.d);
  el.appendChild(path);
  return el;
}

async function vocabCountersFromETF(model, glossing) {
  return getUserCardWords().then((uCardWords) => {
    const counter = {};
    // FIXME: reduce will be faster
    for (const sentence of model.s){
      for (const token of (sentence.t || sentence.tokens)) {
        // it needs to have a pos for us to be interested, though maybe "bg" would be better
        if (token['np'] || utils.toSimplePos(token['pos'])) {
          const lemma = token.l || token.lemma;
          const lookedUp = glossing > utils.USER_STATS_MODE.NO_GLOSS && !uCardWords.known.has(lemma)
          counter[lemma] = counter[lemma]
            ? [counter[lemma][0] + 1, lookedUp ? counter[lemma][1] + 1 : 0]
            : [1, lookedUp ? 1 : 0];
        }
      }
    }
    return counter;
  })
}

// the callback function that will be fired when the enriched-text-fragment element apears in the viewport
function onScreen(entries, ob) {
  const tcModel = window.transcrobesModel;  // FIXME: this is not beautiful
  for (const entry of entries) {
    if (typeof entry.isVisible === 'undefined') { entry.isVisible = true; }  // Feature detection for Intersection V2

    // if (entry.isIntersecting && entry.isVisible) {  // FIXME: exchange for the following for V2 onscreen detection
    if (entry.isIntersecting) {
      console.debug(`entry.target.id isVisible and intersecting`, entry.target.id, entry.time)
      timeouts[entry.target.id] = setTimeout(() => {
        ob.unobserve(entry.target)
        console.debug(`entry.target isVisible has expired from the intersecting`, entry.target, entry.time)

        vocabCountersFromETF(tcModel[entry.target.id], utils.glossing).then(tstats => {
          if (Object.entries(tstats).length == 0) {
            console.debug('An empty model - how can this happen?', entry.target.id, tcModel[entry.target.id])
          } else {
            const userEvent = {
              type: 'bulk_vocab',
              source: EVENT_SOURCE,
              data: tstats,  // WARNING!!! the tstats consider that if it has been glossed, it has been looked up!!!
              userStatsMode: utils.glossing,
            };

            platformHelper.sendMessage({ source: DATA_SOURCE, type: "submitUserEvents", value: userEvent }, (response) => {
              console.debug(response);
            });
          }
        })
      }, utils.onScreenDelayIsConsideredRead)
    } else {
      console.debug(`entry.target.id is no longer intersecting`, entry.target.id, entry.time)
      clearTimeout(timeouts[entry.target.id])
    }
  }
}

function getUserCardWords() {
  if (userCardWords == null) {
    console.debug('userCardWords is null, getting from the database');
    return new Promise((resolve, _reject) => {
      platformHelper.sendMessage({ source: DATA_SOURCE, type: 'getCardWords', value: "" }, (value) => {
        userCardWords = {
          known: new Set(value[0]),
          all: new Set(value[1]),
          bases: value[2],
        }
        resolve(userCardWords);
      });
    });
  } else {
    return Promise.resolve(userCardWords);
  }
}

async function addOrUpdateCards(event, wordInfo, token, grade, originElement) {
  // buttons for SRS
  // don't know : hard : good
  // postpone : suspend : set known

  const doc = originElement.ownerDocument;
  const popupDoc = event.target.getRootNode();

  const fixedTarget = event.target;
  for (const icon of fixedTarget.closest('.tcrobe-def-actions').querySelectorAll('svg')) {
    icon.classList.add('hidden');
  }
  fixedTarget.closest('.tcrobe-def-actions').classList.add('loader');

  const practiceDetails = {
    wordInfo: wordInfo,
    grade: grade,
  }
  platformHelper.sendMessage({source: DATA_SOURCE, type: "practiceCardsForWord", value: practiceDetails }, (response) => {
    console.debug("Sent practiceCardsForWord", response);
  });

  const userEvent = {
    type: 'token_details_card',
    data: { wordId: wordInfo.wordId, grade: grade, pos: token["pos"], sourceSentence: '' },  // FIXME: sourceSentence
  };

  platformHelper.sendMessage({source: DATA_SOURCE, type: "submitUserEvents", value: userEvent }, (response) => {
    const msg = popupDoc.querySelector('.tcrobe-def-messages');
    msg.classList.remove('hidden');
    msg.innerHTML = "Update submitted";
    setTimeout(() => {
      msg.classList.add('hidden');
      for (const icon of fixedTarget.closest('.tcrobe-def-actions').querySelectorAll('svg')) {
        icon.classList.remove('hidden');
      }
      fixedTarget.closest('.tcrobe-def-actions').classList.remove('loader');
    }, 2000);
    cleanupAfterCardsUpdate(doc, grade, wordInfo);
  });
  event.stopPropagation();
}

function cleanupAfterCardsUpdate(doc, grade, wordInfo) {
  //remove existing defs if we are setting knowledge level > UNKNOWN
  if (grade > GRADE.UNKNOWN) {
    for (const wordEl of doc.querySelectorAll(".tcrobe-gloss")) {
      if (wordEl.textContent == wordInfo.graph) {
        wordEl.classList.remove('tcrobe-gloss');
      }
    }
    // we MUST set userCardWords to null after a potential modification. the worker also has a cache but one that is up-to-date
    // so next time we need this an updated version will get re-pulled from the worker
    console.debug('Setting userCardWords for a refresh after word update');
    userCardWords = null;
  };
  // This will remove addition after an add, but what if you chose wrong and want to update?
  // the only option left will be to set to "known", which is not necessarily true
  // const plusImgs = doc.getElementsByClassName("tcrobe-def-plus");
  // while (plusImgs.length > 0) plusImgs[0].remove();
}

function printInfosRx(doc, wordInfo, parentDiv) {
  console.debug('printInfosRx wordInfo', wordInfo)

  // FIXME: this is no longer generic, and will need rewriting... later
  const infoDiv = doCreateElement(doc, 'div', 'tc-stats', null, null, parentDiv);
  let meta = 'HSK';
  if (wordInfo.hsk.levels && wordInfo.hsk.levels.length > 0) {
    const infoElem = doCreateElement(doc, 'div', 'tc-' + meta + 's', null, null, infoDiv);
    doCreateElement(doc, 'div', 'tc-' + meta, `HSK: ${wordInfo.hsk.levels.join(', ')}`, null, infoElem);
  } else {
    doCreateElement(doc, 'div', 'tc-' + meta, 'No ' + meta + ' found', null, infoDiv);
  }
  meta = 'Frequency';
  const frq = wordInfo.frequency;
  if (frq.wcpm) {
    const infoElem = doCreateElement(doc, 'div', 'tc-' + meta + 's', null, null, infoDiv);
    // const vals = `Frequency: wcpm: ${frq.wcpm}, wcdp: ${frq.wcdp}, pos: ${frq.pos}, pos freq: ${frq.posFreq}`;
    const vals = `Frequency: wcpm: ${frq.wcpm}, wcdp: ${frq.wcdp}`;
    doCreateElement(doc, 'div', 'tc-' + meta, vals, null, infoElem);
  } else {
    doCreateElement(doc, 'div', 'tc-' + meta, 'No ' + meta + ' found', null, infoDiv);
  }
}

function printSynonymsRx(doc, wordInfo, token, parentDiv) {
  // TODO: maybe show that there are none?

  const pos = token['np'] || utils.toSimplePos(token['pos']);
  const syns = wordInfo.synonyms.filter(x => x.posTag == pos)
  if (!(syns) || syns.values.length == 0) {return;}

  const synonymsDiv = doCreateElement(doc, 'div', 'tc-synonyms', null, null, parentDiv);

  doCreateElement(doc, 'hr', null, null, null, synonymsDiv);
  doCreateElement(doc, 'div', 'tc-synonym-list', syns[0].join(', '), null, synonymsDiv);
}

function printActionsRx(doc, wordInfo, token, parentDiv, originElement) {
  const actionsDiv = doCreateElement(doc, 'div', 'tcrobe-def-actions', null, null, parentDiv);
  const buttons = {
    [GRADE.UNKNOWN]: 'Add as unknown',
    [GRADE.HARD]: 'Add as known poorly',
    [GRADE.GOOD]: 'Add as known (but still need to revise)',
    [GRADE.KNOWN]: 'Set word known (don\'t need to revise)',
  }
  for (const [grade, helpText] of Object.entries(buttons)) {
    createSVG(GRADE_SVGS[grade], null, [['title', helpText], ['width', 32], ['height', 32]],
      actionsDiv).addEventListener("click",
            (event) => addOrUpdateCards(event, wordInfo, token, grade, originElement)
      );
  }
}

function popupDefinitionsRx(doc, wordInfo, popupContainer) {
  for (const provider of wordInfo.providerTranslations) {
    if (provider.posTranslations.length == 0) continue;

    popupContainer.appendChild(doCreateElement(doc, 'hr', 'tcrobe-def-hr', null, null));
    const defSource = doCreateElement(doc, 'div', 'tcrobe-def-source', null, null, popupContainer);
    doCreateElement(doc, 'div', 'tcrobe-def-source-name', provider.provider, null, defSource);

    for (const translation of provider.posTranslations) {
      if (translation.values.length == 0) continue;

      const actual_defs = translation.values; // sourceDefinition[pos_def];
      defSource.appendChild(doCreateElement(doc, 'div', 'tcrobe-def-source-pos', translation.posTag, null));
      const defSourcePosDefs = doCreateElement(doc, 'div', 'tcrobe-def-source-pos-defs', null, null, defSource);
      defSourcePosDefs.appendChild(doCreateElement(doc, 'span', 'tcrobe-def-source-pos-def', translation.values.join(', ')));
    }
  }
}

function destroyPopup(event, doc, popupParent) {
  const currentTarget = doc.querySelector('.tcrobe-popup-target');
  if (currentTarget) {
    currentTarget.classList.remove('tcrobe-popup-target')
    event.stopPropagation();  // we don't want other events, but we DO want the default, for clicking on links
    popupParent.querySelectorAll("token-details").forEach(el => el.remove());
    return true;
  }

  // clear any existing popups
  popupParent.querySelectorAll("token-details").forEach(el => el.remove());
  return false;
}

function populatePopup(event, doc) {

  const userEvent = {
    type: 'bc_word_lookup',
    data: {
      target_word: JSON.parse(event.target.parentElement.dataset.tcrobeEntry).lemma,
      target_sentence: event.target.parentElement.parentElement.dataset.sentCleaned,
    },
    userStatsMode: utils.glossing };
  platformHelper.sendMessage({source: DATA_SOURCE, type: "submitUserEvents", value: userEvent }, (response) => {
    console.debug('Submitted a bc_word_lookup event', response);
  });

  console.debug('Populating popup for event', event);
  // We clicked on the same element twice, it's probably a link, so we shouldn't try and do any more
  // In any case, we close the popup
  const currentTarget = doc.querySelector('.tcrobe-popup-target');
  if (currentTarget) {
    currentTarget.classList.remove('tcrobe-popup-target')
    // clear any existing popups
    popupParent.ownerDocument.querySelectorAll("token-details").forEach(el => el.remove());
    if (currentTarget == event.target) {
      event.stopPropagation();  // we don't want other events, but we DO want the default, for clicking on links
      return null;
    }
  }
  // set the new popup target
  event.target.classList.add('tcrobe-popup-target');
  const popup = doCreateElement(doc, 'token-details', null, null, null, popupParent);
  popup.setAttribute('theme-css-url', platformHelper.getURL('transcrobes.css'));
  popup.setAttribute('theme-name', utils.themeName);

  // stop the other events
  event.stopPropagation(); event.preventDefault();

  // position the html block
  const eventX = event.clientX;
  const eventY = event.pageY;
  // place the popup just under the clicked item
  popup.style.display = "block";
  // added for readium
  popup.style.position = "absolute";

  const popupWidth = parseInt(popup.getBoundingClientRect().width, 10);

  if (eventX < (popupWidth / 2)) {
    popup.style.left = '0px';
  } else if (popupParent.ownerDocument.documentElement.clientWidth < (eventX + (popupWidth / 2)) ) {
  // } else if (document.documentElement.clientWidth < (eventX + (width / 2)) ) {
    // popup.style.left = `${document.documentElement.clientWidth - width}px`;
    popup.style.left = `${popupParent.ownerDocument.documentElement.clientWidth - popupWidth}px`;
  } else {
    popup.style.left = (eventX - (popupWidth / 2)) + 'px';
  }
  let translateDown = 20;
  if (popupParent.ownerDocument.querySelector("#headerMenu")) {
    translateDown += popupParent.ownerDocument.querySelector("#headerMenu").getBoundingClientRect().height;
  }
  popup.style.top = (eventY + translateDown) + 'px';

  if (document.fullscreenElement || window.parent.document.fullscreenElement) {
    let maxHeight = document.fullscreenElement.getBoundingClientRect().height - popup.getBoundingClientRect().top;
    if (popup.getBoundingClientRect().height > maxHeight) {
      popup.style.height = `${maxHeight}px`;
    }
  }
  return popup
}

function updateWordForEntry(entry, glossing, entryPadding, tokenData, doc) {
  if (entryPadding) {
    // FIXME: this should be the class but how do i make it variable? with css variables?
    entry.style.paddingLeft = `${SEGMENTED_BASE_PADDING * utils.fontSize / 100}px`; // should this be padding or margin?
  }
  let token = tokenData || JSON.parse(entry.dataset.tcrobeEntry);
  let lemma = token['l'] || token['lemma'];
  let word = doCreateElement(doc, 'span', 'tcrobe-word', lemma, null);
  entry.appendChild(word);
  entry.addEventListener("click", (event) => { populatePopup(event, doc); });

  getUserCardWords().then((uCardWords) => {
    if (uCardWords == null) {console.debug('uCardWords is null in updateWordForEntry', entry)}
    if (!(uCardWords.known.has(lemma)) && glossing > utils.USER_STATS_MODE.NO_GLOSS) {
      let gloss = (token['bg']['nt'] || token['bg']).split(",")[0].split(";")[0];  // Default L1, context-aware, "best guess" gloss

      if (glossing == utils.USER_STATS_MODE.L2_SIMPLIFIED) {
        // server-side set user known synonym
        if (('us' in token) && (token['us'].length > 0)) {
          gloss = token['us'][0];
        } else {
          // FIXME: this will almost certainly be VERY slow!!!
          // try and get a local user known synonym
          gloss = platformHelper.sendMessage({ source: DATA_SOURCE, type: "getWordFromDBs", value: lemma }, (response) => {
            const syns = response.synonyms[token['np'] || utils.toSimplePos(token['pos'])];

            let innerGloss;
            if (syns) {
              const userSynonyms = utils.filterKnown(uCardWords.bases, uCardWords.known, syns);
              if (userSynonyms.length > 0) {
                innerGloss = userSynonyms[0];
              }
            }
            return innerGloss || gloss;
          });
        }
      } else if (glossing == utils.USER_STATS_MODE.TRANSLITERATION) {
        gloss = (token['p'] || token['pinyin']).join("");
      }
      // console.debug('i go there with', gloss)
      word.dataset.tcrobeGloss = gloss;
      word.classList.add('tcrobe-gloss');
    } else {
      word.classList.remove('tcrobe-gloss');
    }
  });
}

function doCreateElement(doc, elType, elClass, elInnerText, elAttrs, elParent) {
  if (!(elType)) { throw "eltype must be an element name"; };
  const el = doc.createElement(elType);
  if (!!(elClass)) {
    let arr = Array.isArray(elClass) ? elClass : elClass.split(' ');
    arr.forEach(cssClass => el.classList.add(cssClass));
  }
  if (!!(elInnerText)) {
    el.textContent = elInnerText;
  }
  if (!!(elAttrs)) {
    for (let attr of elAttrs) {
      el.setAttribute(attr[0], attr[1]);
    }
  }
  if (!!(elParent)) {
    elParent.appendChild(el);
  }
  return el;
}

function toggleSentenceVisible(event, l1Sentence) {
  if (l1Sentence.classList.contains('hidden')){
    const userEvent = {
      type: 'bc_sentence_lookup',
      data: {
        target_word: event.target.parentElement.dataset.tcrobeWord,
        target_sentence: event.target.parentElement.dataset.sentCleaned,
      },
      userStatsMode: utils.glossing,
    };
    platformHelper.sendMessage({ source: DATA_SOURCE, type: "submitUserEvents", value: userEvent }, (response) => {
      console.debug("Sent submitUserEvents", response);
    });
  }
  l1Sentence.classList.toggle('hidden');
  for (const button of event.target.parentElement.querySelectorAll('svg')) {
    button.classList.toggle('hidden');
  }
  event.stopPropagation();
}

const popupStyle = `
  hr {
  	margin: 0;
  }
  .tcrobe-def-popup {
  	text-align: center;
  	border-radius: 6px;
  	padding: 3px 0;
    z-index: 99999;
    padding: 5px;
    max-width: 90%;
    min-width: 180px;
    opacity: 1;
  }
  @media (min-width: 400px) {
    .tcrobe-def-popup {
      max-width: 380px;
    }
  }
  .tcrobe-def-container { text-align: left; }
  .tcrobe-def-source { margin-left: 6px; padding: 5px 0; }
  .tcrobe-def-source-name { box-sizing: border-box; text-align: left; }
  .tcrobe-def-source-pos { margin-left: 12px; }
  .tcrobe-def-source-pos-defs { margin-left: 18px; padding: 0 0 0 5px; }
  .tcrobe-def-header { box-sizing: border-box; display: flex; justify-content: space-between; }
  .tcrobe-def-actions { box-sizing: border-box; padding-bottom: 4px; display: flex; justify-content: space-around; }
  .tcrobe-def-pinyin { box-sizing: border-box; padding: 2px; }
  .tcrobe-def-best { box-sizing: border-box; padding: 2px; }
  .tcrobe-def-sentbutton { box-sizing: border-box; padding: 2px; }
`;

class TokenDetails extends HTMLParsedElement {
  static get observedAttributes() {
    return ['theme-css-url', 'theme-name'];
  }

  setThemes(name, newValue) {
    console.debug(`Custom token-details ${name} attribute changed.`);
    if (name === 'theme-name') {
      this.shadowRoot.querySelector('.tcrobe-def-popup').classList.add(newValue);
    } else {
      const themeCSSUrl = this.getAttribute('theme-css-url');

      if (!!(themeCSSUrl) && !this.shadowRoot.querySelector('style')){
        const style = document.createElement('style');
        style.textContent = `
          @import url("${themeCSSUrl}");
          ${popupStyle}
        `;
        this.shadowRoot.appendChild(style);
      }
    }
  }

  attributeChangedCallback(name, _oldValue, newValue) {
    this.setThemes(name, newValue);
  }

  constructor() {
    super();
    this.attachShadow({ mode: "open" });
  }

  connectedCallback(){
    this.init();
  }

  init(){
    const doc = document;  // does it matter where we create, or just attach???
    const target = doc.querySelector('.tcrobe-popup-target');
    const popup = doc.createElement('div');
    popup.classList.add('tcrobe-def-popup');
    this.shadowRoot.appendChild(popup);

    const sentenceEl = target.closest('.tcrobe-sent');
    const entryEl = target.closest('.tcrobe-entry');
    const token = JSON.parse(entryEl.dataset.tcrobeEntry);
    // create the html block
    platformHelper.sendMessage({ source: DATA_SOURCE, type: "getWordFromDBs", value: token['l'] || token['lemma'] }, (response) => {
      console.debug('Should be a word back from getWordFromDBs', response);

      let wordInfo = response;

      const defHeader = doCreateElement(doc, 'div', 'tcrobe-def-header', null, null, popup)
      defHeader.appendChild(doCreateElement(doc, 'div', 'tcrobe-def-pinyin', (token['p'] || token['pinyin']).join(""), null));
      defHeader.appendChild(doCreateElement(doc, 'div', 'tcrobe-def-best', !!(token['bg']) ? (token['bg']['nt'] || token['bg']).split(",")[0].split(";")[0] : '', null));

      const sentButton = doCreateElement(doc, 'div', 'tcrobe-def-sentbutton', null, null, defHeader);
      sentButton.dataset.sentCleaned = sentenceEl.dataset.sentCleaned;
      sentButton.dataset.tcrobeWord = token['l'] || token['lemma'];

      const sentTrans = sentenceEl.dataset.sentTrans;
      const popupExtras = doCreateElement(doc, 'div', 'tcrobe-def-extras hidden', null, null, popup);
      doCreateElement(doc, 'div', 'tcrobe-def-sentence', sentTrans, null, popupExtras);
      doCreateElement(doc, 'div', 'tcrobe-def-messages hidden', null, null, popup);

      createSVG(SVG_SOLID_EXPAND, null, [['title', 'See translated sentence'], ['width', 32], ['height', 32]], sentButton)
        .addEventListener("click", (event) => { toggleSentenceVisible(event, popupExtras); });
      createSVG(SVG_SOLID_COMPRESS, 'hidden', [['title', 'Hide translated sentence'], ['width', 32], ['height', 32]], sentButton)
        .addEventListener("click", (event) => { toggleSentenceVisible(event, popupExtras); });

      const popupContainer = doCreateElement(doc, 'div', 'tcrobe-def-container', null, null, popup);
      printInfosRx(doc, wordInfo, popupContainer);
      printSynonymsRx(doc, wordInfo, token, popupContainer);
      // FIXME: need to fix!!! for getting db in background!!!
      printActionsRx(doc, wordInfo, token, popupContainer, target);
      popupDefinitionsRx(doc, wordInfo, popupContainer);
    });
  }
}

class EnrichedTextFragment extends HTMLParsedElement {
  static get observedAttributes() {
    return ['data-model', 'id'];
  }

  originalSentenceFromTokens(tokens){
    let os = "";
    for (const token of tokens){
      os += token['ot'] || token['l'] || token['originalText'] || token['lemma'];
    }
    return os;
  }

  ensureStyle() {
    // Global style for glosses
    if (document.body && !document.querySelector('#transcrobesInjectedStyle')) {
      const rtStyle = document.createElement('style');
      rtStyle.id = 'transcrobesInjectedStyle';
      rtStyle.textContent = `
        token-details {
          position: absolute; z-index: 99999;
        }
        .tcrobe-entry { position: relative; cursor: pointer; }
        span.tcrobe-word.tcrobe-gloss::after {
          content: ' (' attr(data-tcrobe-gloss) ')';
        }`;
      document.body.appendChild(rtStyle);
    }
  }

  generateSentences(doc, sentences, updateWordCallback){
    const sents = doCreateElement(doc, 'span', 'tcrobe-sents', null, null);
    sentences.forEach(sentence => {
      const sent = doCreateElement(doc, 'span', 'tcrobe-sent', null, null);

      let tokens = sentence['t'] || sentence['tokens'];
      sent.dataset.sentCleaned = this.originalSentenceFromTokens(tokens);
      sent.dataset.sentTrans = sentence['l1'];
      for (const token of tokens) {
        const word = token['l'] || token['lemma'];
        if ('bg' in token) {  // if there is a Best Guess key (even if empty) then we might want to look it up
          const entry = doCreateElement(doc, 'span', 'tcrobe-entry', null, null);
          entry.dataset.tcrobeEntry = JSON.stringify(token);
          if (updateWordCallback) {
            updateWordCallback(entry, utils.glossing, utils.segmentation, token, doc);
          }
          sent.appendChild(entry);
        } else {
          sent.appendChild(doc.createTextNode(!(utils.toEnrich(word)) ? " " + word : word));
        }
        sents.appendChild(sent);
      }
    });
    return sents;
  }

  constructor() {
    super();
    // FIXME: how to best get the document???
    this.doc = document;
  }

  connectedCallback(){
    this.ensureStyle();
    let sentences = null;
    if ('model' in this.dataset && JSON.parse(this.dataset.model)['s'].length > 0) {
      sentences = JSON.parse(this.dataset.model)['s'];
    } else if (this.id) {
      sentences = transcrobesModel[this.id]["s"];
    }
    if (sentences) {
      // FIXME: this doesn't work in chrome extensions with polyfills it seems,
      // so that means we can't have text there and then replace. And this is all
      // because the chrome devs have some philosophical issue with allowing proper components
      // in extensions. The argument on the 7-year old issue is typical Google...
      // this.getRootNode().innerText = '';
      this.innerHTML = '';
      this.appendChild(this.generateSentences(this.doc, sentences, updateWordForEntry));
      readObserver.observe(this);
    };
  }

  attributeChangedCallback(name, oldValue, newValue) {
    this.ensureStyle();
    let sentences = null;
    if (name === 'data-model') {
      sentences = JSON.parse(newValue)['s'];
    } else if (name === 'id') {
      sentences = transcrobesModel[this.id]["s"];
    }
    if (sentences) {
      this.innerHTML = '';
      this.appendChild(this.generateSentences(this.doc, sentences, updateWordForEntry));
      readObserver.observe(this);
    }
  }
}
function defineElements(){
  customElements.define("token-details", TokenDetails);
  customElements.define("enriched-text-fragment", EnrichedTextFragment);
}

export {
  setPlatformHelper,
  setPopupParent,
  defineElements,
  getUserCardWords,
  destroyPopup,
  createSVG,
  onScreen,
  EnrichedTextFragment,
  TokenDetails,
  SVG_HAPPY_4,
  SVG_SAD,
  SVG_SAD_7,
  SVG_SOLID_CHECK,
  SVG_SOLID_COMPRESS,
  SVG_SOLID_EXPAND,
  SVG_SOLID_PLUS,
}
