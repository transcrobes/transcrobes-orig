import React, { Component } from 'react';
import _ from "lodash";
import styled from 'styled-components';

import { CARD_ID_SEPARATOR, CARD_TYPES } from '../js/schemas.js';
import { practice, GRADES } from '../js/review.js';
import { ListrobesConfigLauncher } from './listrobes-config-launcher.jsx'
import { VocabList } from './vocab-list.jsx';
import { USER_STATS_MODE } from '../js/lib.js';

const DATA_SOURCE = "listrobes.jsx";
const DEFAULT_ITEMS_PER_PAGE = 100;
const DEFAULT_FORCE_WCPM = false;
const MIN_LOOKED_AT_EVENT_DURATION = 1300; // milliseconds
let timeoutId;

const GRADE_ICONS = GRADES.reduce((acc, curr) => (acc[curr['id']] = curr['icon'], acc), {});

function gradesWithoutIcons(grades) {
  return grades.map(x => { return {id: x.id, content: x.content} })
}
function gradesWithIcons(grades) {
  return grades.map(x => { return {id: x.id, content: x.content, icon: GRADE_ICONS[x.id]} })
}

// FIXME: should this be here? Where then???
function getGradeOrder(){
  return GRADES;
}

const ColumnList = styled.div`
 column-width: 150px;
 padding-left: 1em;
 padding-top: 1em;
`;

export class Listrobes extends Component {
  constructor(props) {
    super(props);
    console.log(`props in Listrobes constructor`, props)
    this.state = {
      // db: null,
      vocab: [],
      proxy: props.proxy,
      graderConfig: {gradeOrder: getGradeOrder(), forceWcpm: DEFAULT_FORCE_WCPM, itemsPerPage:
        DEFAULT_ITEMS_PER_PAGE, wordLists: []},
      loading: true,
    };
    this.handleConfigChange = this.handleConfigChange.bind(this);
    this.handleGradeChange = this.handleGradeChange.bind(this);
    this.handleMouseOut = this.handleMouseOut.bind(this);
    this.handleMouseOver = this.handleMouseOver.bind(this);
    this.handleValidate = this.handleValidate.bind(this);
    this.submitLookupEvents = this.submitLookupEvents.bind(this);
  };

  async componentDidMount() {
    this.state.proxy.sendMessage({
      source: DATA_SOURCE,
      type: "getDefaultWordLists",
      value: {},
    }, (response) => {
      console.log('back from getDefaultWordLists with ', response);
      const wordLists = response;
      this.setState({
        graderConfig: { ...this.state.graderConfig, wordLists },
      }, () => {
        console.log(`this.state.graderConfig after got wordLists`, this.state.graderConfig)
        this.state.proxy.sendMessage({
          source: DATA_SOURCE,
          type: "getVocabReviews",
          value: { ...this.state.graderConfig, gradeOrder: gradesWithoutIcons(this.state.graderConfig.gradeOrder) },
        }, (vocab) => {
          this.setState({ vocab, loading: false })
        })
      });
    });
  }

  // FIXME: this is duplicated in notrobes.jsx
  submitLookupEvents(lookupEvents, userStatsMode) {
    this.state.proxy.sendMessage({
      source: DATA_SOURCE,
      type: "submitLookupEvents",
      value: { lookupEvents, userStatsMode },
    }, (response) => {
      console.log(`Lookup events submitted`, response)
    });
  }

  handleConfigChange(graderConfig){
    if (graderConfig.itemsPerPage != this.state.graderConfig.itemsPerPage ||
        graderConfig.forceWcpm != this.state.graderConfig.forceWcpm ||
        !_.isEqual(graderConfig.wordLists, this.state.graderConfig.wordLists)) {

      this.state.proxy.sendMessage({
        source: DATA_SOURCE,
        type: "getVocabReviews",
        value: { ...graderConfig, gradeOrder: gradesWithoutIcons(graderConfig.gradeOrder) },
      }, (vocab) => {
        this.setState({ graderConfig, vocab })
      })
    } else {
      this.setState({ graderConfig });
    }
  }

  handleMouseOver(index) {
    if (!timeoutId) {
      timeoutId = window.setTimeout(() => {
        let items = [...this.state.vocab];
        items[index].lookedUp = true;
        this.setState({ vocab: items });
        console.debug(`Looked up`, items[index]);
        timeoutId = null;
      }, MIN_LOOKED_AT_EVENT_DURATION);
    }
  }

  handleMouseOut() {
    if (timeoutId) {
      console.debug(`Cleared timeout in listrobes`);
      window.clearTimeout(timeoutId);
      timeoutId = null;
    }
  }

  handleGradeChange(index){
    let items = [...this.state.vocab];
    items[index].clicks = (items[index].clicks + 1) % this.state.graderConfig.gradeOrder.length;
    this.setState({vocab: items});
  }

  handleValidate(){
    this.setState({ loading: true })
    const newCards = [];
    const consultedDefinitions = [];
    for (const word of this.state.vocab) {
      if (word.lookedUp) {
        consultedDefinitions.push({ target_word: word.graph, target_sentence: "", })
      }
      const grade = parseInt(this.state.graderConfig.gradeOrder[word.clicks].id, 10);
      const cards = CARD_TYPES.typeIds().map(i => {
        return practice({cardId: `${word.wordId}${CARD_ID_SEPARATOR}${i}`}, grade, 0)
      });
      newCards.push(...cards);
    }
    this.state.proxy.sendMessage({
      source: DATA_SOURCE,
      type: "createCards",
      value: newCards,
    }, (response) => {
      console.log(`response from createCards`, response)
      this.state.proxy.sendMessage({
        source: DATA_SOURCE,
        type: "getVocabReviews",
        value: { ...this.state.graderConfig, gradeOrder: gradesWithoutIcons(this.state.graderConfig.gradeOrder) },
      }, (vocab) => {
        this.setState({ vocab, loading: false })
      })
    });

    this.submitLookupEvents(consultedDefinitions, USER_STATS_MODE.L1);
  }

  render(){
    return (
      <div className="container">
        <ColumnList>
          <ListrobesConfigLauncher loading={this.state.loading} graderConfig={this.state.graderConfig}
            onConfigChange={this.handleConfigChange} />
          <VocabList graderConfig={this.state.graderConfig} vocab={this.state.vocab} loading={this.state.loading}
            onGradeChange={this.handleGradeChange} onValidate={this.handleValidate} onMouseOver={this.handleMouseOver}
            onMouseOut={this.handleMouseOut} />
        </ColumnList>
      </div>
    )
  }
}

export default Listrobes;
