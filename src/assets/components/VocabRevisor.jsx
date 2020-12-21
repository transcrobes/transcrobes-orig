import React, { Component } from 'react'
import SearchLoading from './SearchLoading.jsx';
import { CARD_ID_SEPARATOR, CARD_TYPES } from '../js/schemas.js';
import styled from 'styled-components';
import { say } from '../js/lib.js';
import PracticerInput from './PracticerInput.jsx';

const CentredFlex = styled.div`
  display: flex;
  justify-content: center;
`;

const QuestionWrapper = styled.div`
  display: flex;
  justify-content: center;
`;
const AnswerWrapper = styled.div`
  display: flex;
  justify-content: center;
`;

const GraphSoundQuestionStyle = styled.div`
    min-height: 30vh;
    font-size: 4em;
    padding: .5em;
`;

const StyledAnswer = styled.div`
  display: flex;
  justify-content: center;
  font-size: 2em;
  padding: .5em;
`;

const StyledQuestion = styled.div`
  display: flex;
  justify-content: center;
  min-height: 30vh;
  font-size: 2em;
  padding: 1em;
`;

const MeaningWrapper = styled.div`
  display: block;
  padding: 0.5em;
`;

function Meaning({ definition, showSynonyms }) {
  const posTrans = [];
  for (const provider of definition.providerTranslations) {
    if (provider.posTranslations.length > 0) {
      for (const posTranslation of provider.posTranslations) {
        posTrans.push(
          <div key={'mean' + posTranslation.posTag}>
            {posTranslation.posTag}: {posTranslation.values.join(', ')}
          </div>);
      }
      break;
    }
  }
  const synonyms = [];
  if (showSynonyms) {
    for (const posSynonym of definition.synonyms) {
      if (posSynonym.values.length > 0) {
        synonyms.push(<div key={'syn' + posSynonym.posTag}>{posSynonym.posTag}: {posSynonym.values.join(', ')}</div>);
      }
    }
  }
  return posTrans.concat(synonyms);
}

function GraphQuestion({ card, definition }) {
  return (
    <GraphSoundQuestionStyle> {card && card.front ? card.front : definition.graph } </GraphSoundQuestionStyle>
  )
}

function SoundQuestion({ card, definition }) {
  return (
    <GraphSoundQuestionStyle>
      <div>{card && card.front ? card.front : definition.sound}</div>
      <div>
        <button type="button" onClick={() => say(definition.graph)}
          className="btn btn-primary btn-user btn-block">Say it!</button>
      </div>
    </GraphSoundQuestionStyle>
  )
}

function MeaningQuestion({ card, definition, showSynonyms, showL2LengthHint }) {
  return (
    <StyledQuestion> {card && card.front
      ? card.front
      : (<MeaningWrapper>
            <Meaning showSynonyms={showSynonyms} definition={definition} />
            { showL2LengthHint && <div key="lenHint">(L2 length: {definition.graph.length})</div>}
          </MeaningWrapper>)
      }
    </StyledQuestion>
  )
}

function GraphAnswer({ card, definition, showSynonyms }) {
  return (
    <div>
      {card && card.back ? card.back :
        <>
          <StyledAnswer> {definition.sound} </StyledAnswer>
          <MeaningWrapper><Meaning showSynonyms={showSynonyms} definition={definition} /></MeaningWrapper>
        </>
      }
    </div>
  )
}

function SoundAnswer({ card, definition, showSynonyms }) {
  return (
    <div>
      {card && card.back ? card.back :
        <>
          <StyledAnswer> {definition.graph} </StyledAnswer>
          <MeaningWrapper><Meaning showSynonyms={showSynonyms} definition={definition} /></MeaningWrapper>
        </>
      }
    </div>
  )
}

function MeaningAnswer({ card, definition }) {
  return (
    <div>
      {card && card.back ? card.back :
        <>
          <StyledAnswer> {definition.graph} </StyledAnswer>
          <StyledAnswer> {definition.sound} </StyledAnswer>
        </>
      }
    </div>
  )
}

function getAnswer(card, definition, showSynonyms) {
  console.debug(`answer is here`, card)
  const cardType = card.cardId.split(CARD_ID_SEPARATOR)[1];
  switch (cardType) {
    case CARD_TYPES.GRAPH.toString(): return (<GraphAnswer card={card} definition={definition} showSynonyms={showSynonyms} />);
    case CARD_TYPES.SOUND.toString(): return (<SoundAnswer card={card} definition={definition} showSynonyms={showSynonyms} />);
    case CARD_TYPES.MEANING.toString(): return (<MeaningAnswer card={card} definition={definition} showSynonyms={showSynonyms} />);
  }
}

function getQuestion(card, definition, showSynonyms, showL2LengthHint) {
  console.debug(`card is here`, card)
  const cardType = card.cardId.split(CARD_ID_SEPARATOR)[1];
  switch (cardType) {
    case CARD_TYPES.GRAPH.toString(): return (<GraphQuestion card={card} definition={definition} showSynonyms={showSynonyms} />);
    case CARD_TYPES.SOUND.toString(): return (<SoundQuestion card={card} definition={definition} showSynonyms={showSynonyms} />);
    case CARD_TYPES.MEANING.toString(): return (<MeaningQuestion card={card} definition={definition} showSynonyms={showSynonyms}
      showL2LengthHint={showL2LengthHint} />);
  }
}

export class VocabRevisor extends Component {
  constructor(props) {
    super(props);
    this.handlePractice = this.handlePractice.bind(this);
  }
  handlePractice(...args){
    this.props.onPractice(...args);
  }

  render() {
    console.log(`VocabRevisor this.props`, this.props)
    const showAnswer = this.props.showAnswer;
    const { currentCard, definition, loading } = this.props;
    const { showSynonyms, showL2LengthHint } = this.props.activityConfig ;
    return (
      <>
        {loading && <SearchLoading src="/static/img/loader.gif" />}
        {(!loading && !definition) && <span>No review items loaded</span>}
        {(!loading && definition)
          && (
          <>
            <QuestionWrapper>
              {getQuestion(currentCard, definition, showSynonyms, showL2LengthHint)}
            </QuestionWrapper>
            {!showAnswer &&
              <CentredFlex>
                <button className="btn btn-large btn-primary" onClick={this.props.onShowAnswer}>Show Answer</button>
              </CentredFlex>
            }
            {showAnswer &&
              <>
                <AnswerWrapper>{getAnswer(currentCard, definition, showSynonyms)}</AnswerWrapper>
                <PracticerInput practiceObject={currentCard} onPractice={this.handlePractice} />
              </>
            }
          </>
          )
        }
      </>
    )
  }
}

export default VocabRevisor
