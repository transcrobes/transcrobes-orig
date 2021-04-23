import React from 'react';
import dayjs from 'dayjs';
import styled from 'styled-components';
import PracticerInput from './PracticerInput.jsx';
import { say } from '../js/lib.js';
import { CARD_TYPES, cardType } from '../js/schemas.js';
import DefinitionGraph from './DefinitionGraph.jsx';

const ThinHR = styled.hr` margin: .3rem; `;

function WordInfo({definition, characters}){
  return (
    <>
      <div className="row">
        <div className="col-sm-2">
          <h6 className="result-heading">Word info</h6>
        </div>
        <div className="col-6 graph-item" style={{ fontSize: '2em' }}>
          <DefinitionGraph charWidth="100" charHeight="100" characters={characters} showAnswer={true} />
        </div>
        <div className="col sound-item" style={{ fontSize: '2em', display: "flex",  }}>
          <div className="row" style={{ marginLeft: ".5em", display: "flex", alignItems: "center" }}>
            <Sound definition={definition} />
            <div><button type="button" onClick={() => say(definition.graph)}
              style={{ marginLeft: "2em"}} className="btn btn-primary btn-user btn-block">Say it!</button></div>
          </div>
        </div>
        {/* <div className="col sound-item" style={{ fontSize: '2em' }}> </div> */}
      </div>
    </>
  )
}
function Practicer({definition, onPractice}){
  return (
    <>
      <ThinHR />
      <div className="row">
        <div className="col-sm-2">
          <h6 className="result-heading">Card Actions</h6>
        </div>
        <div className="col">
          <PracticerInput practiceObject={definition} onPractice={onPractice} />
        </div>
      </div>
    </>
  )
}

function ExistingCards({ cards }) {
  const cardsArray = [...cards.values()];
  return (
    <>
      <ThinHR />
      <div className="row">
        <div className="col-sm-2">
          <h6 className="result-heading">Existing Cards</h6>
        </div>
        <div className="col">
          {cardsArray.length > 0  // cards is a map
            ? ([(<div key="titles" className="row">
              <span className="col-3 offset-md-1" style={{ fontWeight: "bold", borderBottomStyle: "solid" }}
              >Type</span>
              <span className="col-5" style={{ fontWeight: "bold", borderBottomStyle: "solid" }}>Due Date</span>
              <span className="col" style={{ fontWeight: "bold", borderBottomStyle: "solid" }}>Is Known</span>
            </div>), cardsArray.map((result) => {
              return (
                result && <div key={result.cardId} className="row">
                  <span className="col-3 offset-md-1 def-item-title"
                    style={{ textTransform: "capitalize" }}>{CARD_TYPES.cardName(cardType(result))}</span>
                  <span className="col-5 def-card-due-date">
                    {dayjs.unix(result.dueDate).toDate().toLocaleString('en-UK')}
                  </span>
                  <span className="col def-card-known">{result.known ? "Yes" : "No"}</span>
                </div>
              )
            })]
            )
            : (<span>No cards for this item</span>)
          }
        </div>
      </div>
    </>
  )
}
function WordLists({lists}){
  return (
    <>
      <ThinHR />
      <div className="row lists-info" style={{ paddingTop: ".5em" }}>
        <div className="col-md-2">
          <h6 className="result-heading">Lists (name: position)</h6>
        </div>
        {lists.length > 0  // cards is a map
          ? (<div className="col">
            {lists.map((wl) => `${wl.name}: ${wl.position}`).reduce((prev, curr) => [prev, ', ', curr])}
          </div>)
          : (<span>No lists for this item</span>)}
      </div>
    </>
  )
}

function Synonyms({ definition }) {
  return (
    <>
      <ThinHR />
      <div className="row">
        <div className="col-md-2">
          <h6 className="result-heading">Related Words</h6>
        </div>
        {definition.synonyms.length > 0 &&
          <div className="col synonym-items">
            {definition.synonyms.map((result, ind) => {
              return (
                // probably don't need the key, right?
                <PosItem key={ind} item={result} />
              )
            })}
          </div>
          || <span>No synonyms found</span>
        }
      </div>
    </>
  )
}
function WordModelStats({ wordModelStats }) {
  return (
    <>
      <ThinHR />
      <div className="row">
        <div className="col-md-2">
          <h6 className="result-heading">Personal Word Stats</h6>
        </div>
        {wordModelStats &&
          (<div className="col meta-item">
            <div>
              <span className="meta-item-title" style={{ fontWeight: "bold" }}>Nb. seen: </span>
              <span>{wordModelStats.nbSeen} </span>
            </div>
            <div>
              <span className="meta-item-text" style={{ fontWeight: "bold" }}>Last seen: </span>
              <span>{dayjs.unix(wordModelStats.lastSeen).toDate().toLocaleString('en-UK')} </span>
            </div>
            <div>
              <span className="meta-item-text" style={{ fontWeight: "bold" }}>Nb. seen since last check: </span>
              <span>{wordModelStats.nbSeenSinceLastCheck} </span>
            </div>
            <div>
              <span className="meta-item-text" style={{ fontWeight: "bold" }}>Nb. Checked: </span>
              <span>{wordModelStats.nbChecked} </span>
            </div>
            <div>
              <span className="meta-item-text" style={{ fontWeight: "bold" }}>Last Checked: </span>
              <span>{dayjs.unix(wordModelStats.lastChecked).toDate().toLocaleString('en-UK')} </span>
            </div>
          </div>)
          || (<span>No word stats found</span>)
        }
      </div>
    </>
  )
}

function PosItem({item}){
  return (
    <div className="pos-item">
      {item.values.length > 0 ? <>
      <span className="pos-tag" style={{fontWeight: "bold"}}>{ item.posTag }: </span>
      <span className="pos-values">{ item.values.join(', ') }</span>
      </>
      : <span className="pos-tag">No { item.posTag } found</span>}
    </div>
  )
}

function ProviderTranslations({ definition }) {
  return (
    <>
      <ThinHR />
      <div className="row">
        <div className="col">
          <h6 className="result-heading">Entry Definitions</h6>
        </div>
      </div>
      {definition.providerTranslations.length &&
        definition.providerTranslations.map((providerEntry, ind) => {
          return (
            providerEntry.posTranslations.length > 0 &&
            <React.Fragment key={providerEntry.provider}>
              <ThinHR />
              <div className="row def-item">
                <div className="col-sm-1">
                  <span className="provider-name">{providerEntry.provider}</span>
                </div>
                <div className="col">
                  {providerEntry.posTranslations.map((posItem, ind) => {
                    return ( <PosItem key={posItem.posTag} item={posItem} />)
                  })}
                </div>
              </div>
            </React.Fragment>
          )
        })}
    </>
  )
}

function Sound({definition}) { return ( <div className="sound-item">{definition.sound}</div>) }

function WordMetadata({definition}){
  return (
    <>
      <ThinHR />
      <div className="row">
        <div className="col-sm-2">
          <h6 className="result-heading">Metadata</h6>
        </div>
        <div className="col meta-item">
          <span className="meta-item-title" style={{ fontWeight: "bold" }}>HSK: </span>
          <span className="meta-item-text">
            {(definition.hsk && definition.hsk.levels.length > 0)
              ? definition.hsk.levels.join(', ') : "Not in the HSK"}
          </span>
        </div>
        <div className="col meta-item">
          <span className="meta-item-title" style={{ fontWeight: "bold" }}>Freq: </span>
          <span className="meta-item-text">
            {(definition.frequency && definition.frequency.wcpm) ? definition.frequency.wcpm : "No frequency data"}
          </span>
        </div>
      </div>
    </>
  )
}

class Word extends React.Component {
  constructor(props) {
    super(props);
  }

  render() {
    const { definition, cards, wordModelStats, lists, characters, onPractice } = this.props;
    return (
      definition &&
      <div className="word-container">
        <div className="results-container">
          <WordInfo definition={definition} characters={characters} />
          <Practicer definition={definition} onPractice={onPractice} />
          <ExistingCards cards={cards} />
          <WordLists lists={lists} />
          <WordMetadata definition={definition} />
          <ProviderTranslations definition={definition} />
          <Synonyms definition={definition} />
          <WordModelStats wordModelStats={wordModelStats} />
        </div>
      </div>
    )
  }
}

export default Word
