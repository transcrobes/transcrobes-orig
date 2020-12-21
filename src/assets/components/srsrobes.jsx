import React, { Component } from 'react';
import { IconContext } from "react-icons";
import { isRxDocument } from 'rxdb/plugins/core';
import dayjs from 'dayjs';
import _ from "lodash";

import { CARD_ID_SEPARATOR, CARD_TYPES, GRADE, wordId, cardType } from '../js/schemas.js';
import { shuffleArray } from '../js/review.js';
import { SRSrobesConfigLauncher } from './srsrobes-config-launcher.jsx'
import VocabRevisor from './VocabRevisor.jsx';
import { USER_STATS_MODE } from '../js/lib.js';

const DATA_SOURCE = "srsrobes.jsx";

const DEFAULT_FORCE_WCPM = false;  // repeated from listrobes, show this be the same?
const DEFAULT_QUESTION_SHOW_SYNONYMS = false;
const DEFAULT_QUESTION_SHOW_PROGRESS = false;
const DEFAULT_QUESTION_SHOW_L2_LENGTH_HINT = false;
const DEFAULT_DAY_STARTS_HOUR = 0;
const DEFAULT_BAD_REVIEW_WAIT_SECS = 600;
const DEFAULT_MAX_NEW = 20;
const DEFAULT_MAX_REVISIONS = 100;

const RANDOM_NEXT_WINDOW = 10;
function getRandomNext(candidates, nextWindowSize = RANDOM_NEXT_WINDOW) {
  const shortList = candidates.slice(0, nextWindowSize)
  return shortList[Math.floor(Math.random() * Math.floor(shortList.length))];
}

function Progress({activityConfig, newToday, revisionsToday}) {
  return (
    <div className="something">
      <div>New: {newToday} / {activityConfig.maxNew}</div>
      <div>Revisions: {revisionsToday} / {activityConfig.maxRevisions}</div>
    </div>
  );
};

export class SRSrobes extends Component {
  constructor(props) {
    super(props);
    this.state = {
      proxy: props.proxy,
      activityConfig: { badReviewWaitSecs: DEFAULT_BAD_REVIEW_WAIT_SECS, maxNew: DEFAULT_MAX_NEW,
        maxRevisions: DEFAULT_MAX_REVISIONS, forceWcpm: DEFAULT_FORCE_WCPM, dayStartsHour: DEFAULT_DAY_STARTS_HOUR,
        wordLists: [], showProgress: false, showSynonyms: false, showL2LengthHint: false, activeCardTypes: []},
      currentCard: {},
      showAnswer: false,
      newToday: 0,
      revisionsToday: 0,
      curNewWordIndex: 0,
      loading: true,
    };
    this.handleConfigChange = this.handleConfigChange.bind(this);
    this.handleShowAnswer = this.handleShowAnswer.bind(this);
    this.handlePractice = this.handlePractice.bind(this);
    this.getTodaysCounters = this.getTodaysCounters.bind(this);
    this.submitLookupEvents = this.submitLookupEvents.bind(this);
  };

  async componentDidMount() {
    // FIXME: What about adding a button to the popup config to have it save "current as default"?
    // this could also work for listrobes
    const dayStartsHour = DEFAULT_DAY_STARTS_HOUR; // FIXME: get from database/local config!
    const badReviewWaitSecs = DEFAULT_BAD_REVIEW_WAIT_SECS; // FIXME: get from database/local config!
    const maxNew = DEFAULT_MAX_NEW; // FIXME: get from database/local config!
    const maxRevisions = DEFAULT_MAX_REVISIONS; // FIXME: get from database/local config!
    const showSynonyms = DEFAULT_QUESTION_SHOW_SYNONYMS; // FIXME: get from database/local config!
    const showProgress = DEFAULT_QUESTION_SHOW_PROGRESS; // FIXME: get from database/local config!
    const showL2LengthHint = DEFAULT_QUESTION_SHOW_L2_LENGTH_HINT; // FIXME: get from database/local config!

    // FIXME: get from database/local config!
    const activeCardTypes = Object.entries(CARD_TYPES).filter(([_l, v]) => !(v instanceof Function))
      .map(([label, value]) => { return {label: label, value: value, selected: true} });

    const todayStarts = (new Date().getHours() < dayStartsHour
        ? dayjs().startOf('day').subtract(1, 'day')
        : dayjs().startOf('day')
      ).add(dayStartsHour, 'hour').unix();

    this.state.proxy.sendMessage({
      source: DATA_SOURCE,
      type: "getDefaultWordLists",
      value: {},
    }, (response) => {
      console.log('back from getDefaultWordLists in srsrobes with ', response);
      const wordLists = response;
      const activityConfig = {
        ...this.state.activityConfig,
        wordLists,
        activeCardTypes,
        maxRevisions,
        maxNew,
        showSynonyms,
        showProgress,
        showL2LengthHint,
        dayStartsHour,
        badReviewWaitSecs,
        todayStarts,
      };

      this.setState({
        activityConfig: { ...this.state.activityConfig, wordLists },
      }, () => {
        console.log(`this.state.activityConfig after got wordLists`, this.state.activityConfig)
        this.state.proxy.sendMessage({
          source: DATA_SOURCE,
          type: "getSRSReviews",
          value: { ...activityConfig },
        }, (reviewLists) => {
          const tempState = {
              ...this.state,
              activityConfig,
              ...reviewLists
            };
          this.nextPractice(tempState).then(practiceOut => {
            const partial = { ...tempState, ...practiceOut };
            this.setState({
              ...partial,
                activityConfig,
                loading: false,
            });
            console.debug(`this.state end of cdm`, {
              ...partial,
                activityConfig,
                loading: false,
            });
          })
        })
      });
    });
  }

  submitLookupEvents(lookupEvents, userStatsMode) {
    this.state.proxy.sendMessage({
      source: DATA_SOURCE,
      type: "submitLookupEvents",
      value: { lookupEvents, userStatsMode },
    }, (response) => {
      console.log(`Lookup events submitted`, response)
    });
  }

  handleConfigChange(activityConfig){
    console.debug(`activityConfig in handleConfigChange`, activityConfig)
    if (!_.isEqual(activityConfig, this.state.activityConfig)) {
      const newState = { ...this.state, activityConfig };
      this.nextPractice(newState).then(moreNewState =>{
        this.setState({ ...moreNewState, activityConfig, showAnswer: false })
      });
    } else {
      this.setState({ activityConfig, showAnswer: false });
    }
  }

  getTodaysCounters(state){
    // FIXME: make functional? store counters in the state? if so, we need to not recount!
    let newToday = 0;
    let revisionsToday = 0;
    const todayStarts = state.activityConfig.todayStarts;
    console.log(`state.existingCards`, todayStarts, state.existingCards)
    for (const [k, v] of state.existingCards) {
      if (v.lastRevisionDate > todayStarts && v.firstRevisionDate >= todayStarts) {
        console.log(`[k, v] is new`, [k, v])
        newToday++;
      } else if (v.lastRevisionDate > todayStarts && v.firstRevisionDate < todayStarts) {
        console.log(`[k, v] is revision`, [k, v])
        revisionsToday++;
      }
    }
    console.debug(`[newToday, revisionsToday] getTodaysCounters`, newToday, revisionsToday)
    return [newToday, revisionsToday];
  }

  async newCard(existingCards, curNewWordIndex, potentialWords, cardTypes){
    console.debug('newCard inputs: potentialWords, curNewWordIndex, existingCards',
      potentialWords, curNewWordIndex, existingCards);
    while (curNewWordIndex < potentialWords.length) {
      // get a random possible new card for the word
      for (const cardType of shuffleArray(Object.values(cardTypes)).filter(x => x.selected)) {
        let nextReview = potentialWords[curNewWordIndex];
        if (!existingCards.has(nextReview.wordId + CARD_ID_SEPARATOR + cardType.value)) {
          console.log(`${nextReview.wordId + CARD_ID_SEPARATOR + cardType.value} doesn't have card, choosing`);
          return [curNewWordIndex, cardType.value];
        }
        console.debug(`${nextReview} already has card ${cardType.label}, skipping`);
      }
      curNewWordIndex++;
    }
    return [0, 0];
  }

  async newRevisionFromState(state){
    const todaysReviewedCards = new Map([...state.existingCards.values()].filter(x => {
      return x.lastRevisionDate > state.activityConfig.todayStarts && x.firstRevisionDate > 0
    }).map(c => [c.cardId, c]));
    console.debug(`todaysReviewedCards`, todaysReviewedCards);
    const todaysReviewedWords = new Map([...todaysReviewedCards.values()]
      .map(x => [wordId(x), state.existingWords.get(wordId(x))]));
    console.debug(`todaysReviewedWords`, todaysReviewedWords);
    const potentialTypes = state.activityConfig.activeCardTypes.filter(x => x.selected).map(x => x.value.toString())
    console.debug(`types to choose from `, potentialTypes);

    const candidates = [...state.existingCards.values()].filter(x => {
      return x.dueDate < dayjs().unix()  // or maybe? dayjs.unix(state.activityConfig.todayStarts).add(1, 'day').unix()
        && (todaysReviewedCards.has(x.cardId) || !(todaysReviewedWords.has(wordId(x)))
        && potentialTypes.includes(cardType(x))
        && !x.known)
    }).sort((a, b) => a.dueDate - b.dueDate );

    console.debug(`candidates`, candidates);
    const candidate = getRandomNext(candidates);
    return candidate
      ? [candidate, cardType(candidate)]
      : [null, ""];
  }

  async nextPractice(state) {
    let currentCard; let curNewWordIndex; let cardType; let definition;
    console.debug(`state at start of nexPractice`, state)

    const [newToday, revisionsToday] = this.getTodaysCounters(state);
    let getNew = true;
    if (newToday >= state.activityConfig.maxNew) {getNew = false }
    if ((newToday / revisionsToday) > (state.activityConfig.maxNew / state.activityConfig.maxRevisions)) {
      getNew = false
    }
    console.debug(`Found ${newToday} new done, ${revisionsToday} revisions done, meaning getNew is ${getNew}`);
    if (getNew) {
      [curNewWordIndex, cardType] = await this.newCard(state.existingCards, state.curNewWordIndex,
        state.potentialWords, state.activityConfig.activeCardTypes)
      currentCard = { cardId: state.potentialWords[curNewWordIndex].wordId + CARD_ID_SEPARATOR + cardType };
      definition = state.potentialWords[curNewWordIndex];
      console.debug(`new card [curNewWordIndex, cardType]`, curNewWordIndex, cardType)
    } else {
      [currentCard, cardType] = await this.newRevisionFromState(state);
      definition = state.existingWords.get(wordId(currentCard))
      console.debug(`revision [currentCard, cardType]`, currentCard, cardType)
    }
    return { ...state,
      currentCard,
      definition,
      curNewWordIndex: (curNewWordIndex || state.curNewWordIndex),
      newToday,
      revisionsToday };
  }
  handleShowAnswer(){
    this.setState({ showAnswer: true });
  }

  async handlePractice(practiceObject, grade){
    const { currentCard } = this.state;
    const { badReviewWaitSecs } = this.state.activityConfig;

    if (grade < GRADE.HARD) {  // we consider it a lookup, otherwise we wouldn't have needed to look it up
      const lookupEvent = { target_word: this.state.definition.graph, target_sentence: "", };
      this.submitLookupEvents([lookupEvent], USER_STATS_MODE.L1);
    }

    if (practiceObject != currentCard) { throw 'Sanity check, this shouldnt happen!'; }
    console.debug('Practicing card', isRxDocument(currentCard) ? currentCard.toJSON() : currentCard, grade);

    this.state.proxy.sendMessage({
      source: DATA_SOURCE,
      type: "practiceCard",
      value: { currentCard, grade, badReviewWaitSecs },
    }, (response) => {
      const practicedCard = response
      const newState = { ...{ ...this.state },
        existingCards: (new Map(this.state.existingCards)).set(practicedCard.cardId, practicedCard),
        existingWords: (new Map(this.state.existingWords)).set(wordId(practicedCard),
          this.state.allNonReviewedWordsMap.get(wordId(practicedCard))),
        curNewWordIndex: !isRxDocument(currentCard) ? this.state.curNewWordIndex + 1 : this.state.curNewWordIndex }

      this.nextPractice(newState).then((nextCard) => {
        this.setState({...nextCard, showAnswer: false});
      })
    });
  }

  render(){
    const ac = this.state.activityConfig;
    return (
      <IconContext.Provider value={{ color: "blue", size: '3em' }}>
        <div style={{ padding: "1em" }}>
          <div className="d-flex justify-content-between">
            <SRSrobesConfigLauncher loading={this.state.loading} activityConfig={ac}
              onConfigChange={this.handleConfigChange} />
            { ac.showProgress && <Progress activityConfig={ac} newToday={this.state.newToday}
              revisionsToday={this.state.revisionsToday} /> }
          </div>
          <div className="d-flex flex-column">
            <VocabRevisor showAnswer={this.state.showAnswer}
              activityConfig={ac}
              currentCard={this.state.currentCard} definition={this.state.definition} loading={this.state.loading}
              onPractice={this.handlePractice}
              onShowAnswer={this.handleShowAnswer} />
          </div>
        </div>
      </IconContext.Provider>
    )
  }
}

export default SRSrobes;
