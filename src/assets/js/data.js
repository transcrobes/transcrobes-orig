import { isRxDocument } from 'rxdb/plugins/core';
import dayjs from 'dayjs';

import { CARD_ID_SEPARATOR, CARD_TYPES } from './schemas.js';
import { practice } from './review.js';
import { pythonCounter, sortByWcpm, shortMeaning } from './lib.js';
import * as utils from './lib.js';


async function addOrUpdateCards(db, wordId, grade){
  const cards = [];
  for (const cardType of CARD_TYPES.typeIds()) {
    const cardId = `${wordId}${CARD_ID_SEPARATOR}${cardType}`;
    const existing = await db.cards.findOne(cardId).exec();
    cards.push(await practiceCard(db, existing || { cardId: cardId }, grade, 0))  // Promise.all?
  }
  return cards;
}

async function getUserListWords(db){
  const listsBase = [...await db.word_lists.find().exec()].reduce((a, x) => ({ ...a, [x.listId]: [x.name, x.wordIds] }), {})
  const userListWords = {};
  const wordListNames = {};

  for (const p in listsBase) {
    const name = listsBase[p][0];
    wordListNames[p] = name;
    const wordIds = listsBase[p][1];
    let l = wordIds.length;
    for (let i = 0; i < l; i++) {
      if (wordIds[i] in userListWords) {
        userListWords[wordIds[i]].push({ listId: p, position: i + 1 });
      } else {
        userListWords[wordIds[i]] = [{ listId: p, position: i + 1 }];
      }
    }
  }
  return { userListWords, wordListNames };
}

async function getDefaultWordLists(db) {
  return [...(await db.word_lists.find().exec())].map(x => {
    return { label: x.name, value: x.listId, selected: x.default }
  });
}

async function getWordDetails(db, graph) {
  const localDefinition = await db.definitions.find().where('graph').eq(graph).exec();
  if (localDefinition.length > 0) {
    console.debug(`${graph} was found locally, not going to server`, localDefinition);

    const word = localDefinition.values().next().value;
    const cardIds = ((await db.cards.pouch.allDocs(
      { startkey: `${word.wordId}-`, endkey: `${word.wordId}-\uffff` })
    ).rows).map(x => x.id);
    const cards = await db.cards.findByIds(cardIds)  // a map is more useful
    const wordModelStats = [...(await db.word_model_stats.findByIds([word.wordId])).values()][0];

    return { word, cards, wordModelStats, }
  }
  return { word: null, cards: new Map(), wordModelStats: null, }
}

async function getCardWords(db) {
  // FIXME:
  // Is this the best way to do this?
  // Basically, there are three states:
  // "new": in the list to learn but not seen yet, so we want it translated
  // "learning": in the list to learn and we sort of know/have started learning, so we don't want it translated
  // "known": we know it, so we don't want to have it in active learning, and we don't want it translated

  const allCardWordIds = new Set((await db.cards.find().exec()).flatMap(x => x.wordId()));

  // If we have at least one card with an interval greater than zero,
  // it is considered "known" (here meaning simply "we don't want it translated in content we're consuming")
  const knownWordIds = new Set((await db.cards.find({
    selector: {$or: [{known: {$eq: true}}, {interval: {$gt: 0}}]}
  }).exec()).flatMap( x => x.wordId()));

  const allCardWords = (await db.definitions.findByIds(allCardWordIds));
  const allCardWordGraphs = new Set();
  const knownCardWordGraphs = new Set();
  for (const [wordId, word] of allCardWords){
    allCardWordGraphs.add(word.graph);
    if (knownWordIds.has(wordId)){
      knownCardWordGraphs.add(word.graph);
    }
  }

  return [knownCardWordGraphs, allCardWordGraphs, pythonCounter(knownWordIds)];
}

async function submitLookupEvents(db, lemmaAndContexts, userStatsMode) {
  const events = [];
  for (const lemmaAndContext of lemmaAndContexts) {
    events.push({
      type: 'bc_word_lookup',
      data: lemmaAndContext,
      userStatsMode: userStatsMode
    })
  }
  return await submitUserEvents(db, events);
}

async function submitUserEvents(db, eventData) {
  console.debug('submitting user event', eventData);
  let now = Date.now();  // maybe use? let uuid = utils.UUID();
  while (!!(await db.event_queue.findOne(now.toString()).exec())) {
    console.debug(`looks like event ${now} already exists, looking for another`);
    now = Date.now();  // maybe use?   uuid = utils.UUID();
  }
  await db.event_queue.insert({ eventTime: now.toString(), eventString: JSON.stringify(eventData)});
  return true;
}

async function getVocabReviews(db, graderConfig) {
  const selectedLists = graderConfig.wordLists.filter(x => x.selected).map(x => x.value);
  if (selectedLists.length === 0) {
    console.log('no wordLists, not trying  to find stuff');
    return;
  }
  const wordListObjects = (await db.word_lists.findByIds(selectedLists)).values();
  const potentialWordIds = new Set([...wordListObjects].flatMap(x => x.wordIds));
  const existingWords = new Set((await db.cards.find().exec()).flatMap(x => x.wordId()));

  let potentialWordsMap = await db.definitions.findByIds(potentialWordIds);
  let potentialWords; //  = [...potentialWordsMap.values()].filter(x => !existingWords.has(x.wordId));

  if (graderConfig.forceWcpm) {
    potentialWords = [...potentialWordsMap.values()]
      .filter(x => !existingWords.has(x.wordId)).sort(sortByWcpm);
  } else {
    // TODO: this ordering is a bit arbitrary. If there is more than one list that has duplicates then
    // I don't know which version gets ignored, though it's likely the second. Is this what is wanted?
    potentialWords = [...potentialWordIds].map(x => potentialWordsMap.get(x))
      .filter(x => x && !existingWords.has(x.wordId));
  }

  return potentialWords.slice(0, graderConfig.itemsPerPage).map(x => {
    return { wordId: x.wordId, graph: x.graph, sound: x.sound, meaning: shortMeaning(x.providerTranslations),
      clicks: 0}
  })
}

async function getSRSReviews(db, activityConfig) {
  const selectedLists = activityConfig.wordLists.filter(x => x.selected).map(x => x.value);
  if (selectedLists.length === 0) {
    console.log('No wordLists, not trying to find stuff');
    return {
      todaysWordIds: new Set(),  // Set of words reviewed today already: string ids
      allNonReviewedWordsMap: new Map(),  // Map of words in selected lists not already reviewed today: RxDocument
      existingCards: new Map(),  // Map of all cards reviewed at least once: RxDocument
      existingWords: new Map(),  // Map of all words which have had at least one card reviewed at least once: RxDocument
      potentialWords: [],  // Array of words that can be "new" words today: RxDocument
    }
  }

  const todaysWordIds = new Set((await db.cards.find()
      .where('lastRevisionDate').gt(dayjs().startOf('hour').hour(activityConfig.dayStartsHour).unix())
      .where('firstRevisionDate').gt(0).exec()
    ).flatMap( x => x.wordId()));

  const potentialWordIds = new Set([...(await db.word_lists.findByIds(selectedLists)).values()]
      .flatMap(x => x.wordIds).filter( x => !todaysWordIds.has(x)));
  const allNonReviewedWordsMap = await db.definitions.findByIds(potentialWordIds);
  const allKnownWordIds = new Set([...(await db.cards.find().where('known').eq(true).exec())].map(x => x.wordId()));

  const existingCards = new Map((await db.cards.find().where('firstRevisionDate').gt(0).exec()).map(c => [c.cardId, c]));
  console.debug(`existingCards at start`, existingCards);
  const existingWords = await db.definitions.findByIds([...existingCards.values()].map(x => x.wordId()));

  // TODO: this ordering is a bit arbitrary. If there is more than one list that has duplicates then
  // I don't know which version gets ignored, though it's likely the second. Is this what is wanted?
  const potentialWords = [...allNonReviewedWordsMap.values()]
      .filter(x => !existingWords.has(x.wordId) && !allKnownWordIds.has(x.wordId));
  if (activityConfig.forceWcpm) {
    potentialWords.sort(sortByWcpm);
  }
  return {
    todaysWordIds,  // Set of words reviewed today already: string ids
    allNonReviewedWordsMap,  // Map of words in selected lists not already reviewed today: RxDocument
    existingCards,  // Map of all cards reviewed at least once: RxDocument
    existingWords,  // Map of all words which have had at least one card reviewed at least once: RxDocument
    potentialWords,  // Array of words that can be "new" words today: RxDocument
  };
}

async function createCards(db, newCards) {
    return await db.cards.bulkInsert(newCards);
}

async function getWordFromDBs(db, word) {
  console.debug('trying to find', word);
  return await db.definitions.findOne().where('graph').eq(word).exec();
}

async function getContentConfigFromStore(db, contentId) {
  const dbValue = await db.content_config.findOne(contentId.toString()).exec();
  console.debug("dbValue in getContentConfigFromStore", dbValue);
  const returnVal = dbValue ? JSON.parse(dbValue.configString || '{}') : {};
  console.debug('the returnval is ', returnVal)
  return returnVal;
}

async function setContentConfigToStore(db, contentConfig) {
  console.debug('Setting contentConfig to store', contentConfig, { contentId: contentConfig.contentId, configString: JSON.stringify(contentConfig)});
  await db.content_config.upsert({ contentId: contentConfig.contentId.toString(), configString: JSON.stringify(contentConfig)});
  return true;
}

async function practiceCard(db, currentCard, grade, badReviewWaitSecs) {
  const cardToSave = practice(isRxDocument(currentCard) ? currentCard.toJSON() : currentCard,
    grade, badReviewWaitSecs);
  console.debug('Card to save is very surprising', cardToSave);
  let cardObject;
  if (isRxDocument(currentCard)) {
    // It's an update
    cardObject = currentCard;
    await currentCard.atomicPatch({
      interval: cardToSave.interval,
      repetition: cardToSave.repetition,
      efactor: cardToSave.efactor,
      dueDate: cardToSave.dueDate,
      known: cardToSave.known,
      lastRevisionDate: dayjs().unix(),
    });
    console.log(`currentCard after saving rxdoc`, currentCard.toJSON());
  } else {
    const newDate = dayjs().unix();
    if (!cardToSave.firstRevisionDate) {
      cardToSave.firstRevisionDate = newDate;
    }
    cardToSave.lastRevisionDate = newDate;
    cardObject = await db.cards.upsert(cardToSave)
    console.log(`currentCard after saving upsert`, cardObject.toJSON());
  }
  console.debug('Card object was saved in happiness', cardObject);
  return cardObject;
}

async function practiceCardsForWord(db, practiceDetails) {
  const wordInfo = practiceDetails.wordInfo;
  const grade = practiceDetails.grade;

  const existing = (await db.cards.findByIds(CARD_TYPES.typeIds().map(
    (cardType) => `${wordInfo.wordId}${CARD_ID_SEPARATOR}${cardType}`)));

  for (const cardType of CARD_TYPES.typeIds()) {
    const cardId = `${wordInfo.wordId}${CARD_ID_SEPARATOR}${cardType}`;
    let card = existing.has(cardId) ? existing.get(cardId) : { cardId: cardId };
    await practiceCard(db, card, grade, 0);  // here failureSeconds doesn't really have meaning
  }
}

async function sendUserEvents(db, baseUrl, maxSendEvents=500) {
  const localBaseUrl = baseUrl || utils.baseUrl
  if (!(localBaseUrl) || !(db)) {
    console.debug('No baseUrl or db in sendUserEvents, not executing', localBaseUrl, db);
    return { 'status': 'uninitialised' };
  }
  const allEvents = [];
  const allEventIds = [];

  const allEntries = await db.event_queue.find({ selector: {
    eventTime: {$gte: null}
  }, limit: maxSendEvents }).exec();

  console.debug("allEntries is", allEntries);
  for (const event of allEntries) {
    console.debug("Pushing events to queue", event);
    console.debug("Pushing events to queue", event.eventTime, event.eventString);
    allEventIds.push(event.eventTime.toString());
    const eventObj = JSON.parse(event.eventString);
    for (const anevent of (Array.isArray(eventObj) ? eventObj : [eventObj])) {
      allEvents.push(anevent);
    }
  }

  if (!(allEntries.length)) {
    console.log("Nothing in the events queue to send to the server");
    return { 'status': 'empty_queue' };
  }

  console.debug("Sending allEvents to API", allEvents);
  return await utils.fetchPlus(localBaseUrl + 'user_event/', allEvents, utils.DEFAULT_RETRIES)
    .then(data => {
      if (!(data) || !(data['status']) || !(data['status'] == 'success')) {
        let message = 'user_event update failed due to return status incorrect!';
        throw message;
      } else {
        // remove from queue
        db.event_queue.bulkRemove(allEventIds).then((results)=> {
          console.debug(`Deleted events from the queue with results`, results);
        });
      }
      console.debug(`Successfully submitted ${allEntries.length} events`);
      return { 'status': 'success' };
    }).catch((err) => {
      console.error(err);
      throw 'user_event update failed! That is bad!';
    });
}

export {
  // get data from db
  getUserListWords,
  getWordDetails,
  getCardWords,
  getWordFromDBs,
  getDefaultWordLists,
  getVocabReviews,
  getSRSReviews,
  getContentConfigFromStore,
  setContentConfigToStore,

  // add/update data (to) db
  addOrUpdateCards,
  createCards,
  submitLookupEvents,
  submitUserEvents,
  practiceCardsForWord,
  practiceCard,

  // update db and api
  sendUserEvents,
}
