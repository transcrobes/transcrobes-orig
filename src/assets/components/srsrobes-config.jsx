import React, { Component } from "react";
import Select from 'react-select';
import 'reactjs-popup/dist/index.css';

import TCCheckbox from './TCCheckbox.jsx';


export class SRSrobesConfig extends Component {
  constructor(props) {
    super(props);
    this.handleSimpleChange = this.handleSimpleChange.bind(this);
    this.handleWordListsChange = this.handleWordListsChange.bind(this);
    this.handleCardTypesChange = this.handleCardTypesChange.bind(this);
    this.handleBadReviewWaitMinutesChange = this.handleBadReviewWaitMinutesChange.bind(this);
  }

  handleWordListsChange(selectedLists){
    console.log(`this.props wlc`, this.props)
    const selectedMap = new Map(selectedLists.map(x => [x.value, x]))
    const newWordLists = _.cloneDeep(this.props.activityConfig.wordLists);
    for (const wordList of newWordLists) {
      wordList.selected = selectedMap.has(wordList.value);
    }
    this.props.onConfigChange({...this.props.activityConfig, wordLists: newWordLists});
  }

  handleCardTypesChange(selectedTypes){
    console.debug(`this.props ctc`, this.props)
    const selectedMap = new Map(selectedTypes.map(x => [x.value, x]))
    const newCardTypes = _.cloneDeep(this.props.activityConfig.activeCardTypes);
    for (const cardType of newCardTypes) {
      cardType.selected = selectedMap.has(cardType.value);
    }
    this.props.onConfigChange({...this.props.activityConfig, activeCardTypes: newCardTypes});
  }

  handleDayStartsHourChange(e) {
    console.debug(`handleDayStartsChange`, e.target)
    const dayStartsHour = e.target.value;
    const todayStarts = (new Date().getHours() < dayStartsHour
        ? dayjs().startOf('day').subtract(1, 'day')
        : dayjs().startOf('day')
      ).add(dayStartsHour, 'hour').unix();

    const update = {...this.props.activityConfig,
        dayStartsHour,
        todayStarts,
      };

    this.props.onConfigChange(update);
  }

  handleSimpleChange(e){
    console.debug(`e handleSimpleChange`, e.target)
    const update = {...this.props.activityConfig,
        [e.target.name]: e.target.hasOwnProperty('checked') ? e.target.checked : e.target.value
      };
    this.props.onConfigChange(update);
  }

  handleBadReviewWaitMinutesChange(e) {
    this.props.onConfigChange(
      {...this.props.activityConfig,
        badReviewWaitSecs: e.target.value * 60} // the user inputs in minutes, we store in seconds
        );
  }

  render() {
    console.debug(`this.props in srsrobes-config`, this.props)
    return (
      <div>
        <div>
          Source word lists
            <Select
            onChange={this.handleWordListsChange}
            defaultValue={this.props.activityConfig.wordLists.filter(x => x.selected)}
            isMulti
            name="wordLists"
            options={this.props.activityConfig.wordLists}
            className="basic-multi-select"
            classNamePrefix="select"
          />
        </div>
        <div>
          Active card types
            <Select
            onChange={this.handleCardTypesChange}
            defaultValue={this.props.activityConfig.activeCardTypes.filter(x => x.selected)}
            isMulti
            name="activeCardTypes"
            options={this.props.activityConfig.activeCardTypes}
            className="basic-multi-select"
            classNamePrefix="select"
          />
        </div>
        <div>
          <TCCheckbox name="showSynonyms" label="Show meaning question L2 synonyms"
            isSelected={this.props.activityConfig.showSynonyms} onCheckboxChange={this.handleSimpleChange} />
        </div>
        <div>
          <TCCheckbox name="forceWcpm" label="Force word count per million ordering"
            isSelected={this.props.activityConfig.forceWcpm} onCheckboxChange={this.handleSimpleChange} />
        </div>
        <div>
          <TCCheckbox name="showL2LengthHint" label="Show L2 length hint"
            isSelected={this.props.activityConfig.showL2LengthHint} onCheckboxChange={this.handleSimpleChange} />
        </div>
        <div>
          <TCCheckbox name="showProgress" label="Show daily progress information"
            isSelected={this.props.activityConfig.showProgress} onCheckboxChange={this.handleSimpleChange} />
        </div>
        <div style={{display: "flex", justifyContent: "space-between"}}>
          <label htmlFor="dayStartsHour">Day start hour (0 to 23)</label>
          <input style={{width: "30%", maxHeight: "2em"}} name="dayStartsHour" min="0" max="23" type="number"
            value={this.props.activityConfig.dayStartsHour} onChange={this.handleDayStartsHourChange} />
        </div>
        <div style={{display: "flex", justifyContent: "space-between"}}>
          <label htmlFor="badReviewWaitMinutes">Bad review wait mins (1 to 300)</label>
          <input style={{width: "30%", maxHeight: "2em", minWidth: "3em"}} name="badReviewWaitMinutes" min="1"
            max="300" type="number" value={Math.round(this.props.activityConfig.badReviewWaitSecs / 60)}
            onChange={this.handleBadReviewWaitMinutesChange} />
        </div>
        <div style={{display: "flex", justifyContent: "space-between"}}>
          <label htmlFor="maxNew">Max new p/d (1 to 10000)</label>
          <input style={{width: "40%", maxHeight: "2em", minWidth: "3em"}} name="maxNew" min="1"
            max="10000" type="number" value={this.props.activityConfig.maxNew}
            onChange={this.handleSimpleChange} />
        </div>
        <div style={{display: "flex", justifyContent: "space-between"}}>
          <label htmlFor="maxRevisions">Max revisions p/d (1 to 10000)</label>
          <input style={{width: "40%", maxHeight: "2em", minWidth: "3em"}} name="maxRevisions" min="1"
            max="10000" type="number" value={this.props.activityConfig.maxRevisions}
            onChange={this.handleSimpleChange} />
        </div>
      </div>
    );
  }
}
