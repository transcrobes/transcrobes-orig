import React, { Component } from 'react'
import SearchLoading from './SearchLoading.jsx';
import { CARD_ID_SEPARATOR, CARD_TYPES } from '../js/schemas.js';
import styled from 'styled-components';
import { say } from '../js/lib.js';
import PracticerInput from './PracticerInput.jsx';
import DefinitionGraph from './DefinitionGraph.jsx';

const CentredFlex = styled.div`
  display: flex;
  justify-content: center;
`;

const QuestionWrapper = styled.div`
  display: block;
  justify-content: center;
`;
const AnswerWrapper = styled.div`
  display: flex;
  justify-content: center;
`;

// min-height: 30vh;
const GraphSoundQuestionStyle = styled.div`
    font-size: 4em;
    padding: .5em;
`;

const StyledAnswer = styled.div`
  display: flex;
  justify-content: center;
  font-size: 2em;
  padding: .5em;
`;

// min-height: 30vh;
const StyledQuestion = styled.div`
  display: flex;
  justify-content: center;
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

function GraphQuestion({ card, characters }) {
  return (
    <GraphSoundQuestionStyle> {card && card.front ? card.front :
      <DefinitionGraph characters={characters} showAnswer={true}></DefinitionGraph> } </GraphSoundQuestionStyle>
  )
}

function SoundQuestion({ card, definition, characters, showAnswer }) {
  return (
    <GraphSoundQuestionStyle>
      <div className="row" style={{justifyContent: "center", alignItems: "center"}}>
        <div>{card && card.front ? card.front : definition.sound}</div>
        <div>
          <button type="button" onClick={() => say(definition.graph)}
            className="btn btn-primary btn-user btn-block" style={{marginLeft: "2em"}}>Say it!</button>
        </div>
      </div>
      <div className="row" style={{justifyContent: "center", alignItems: "center"}}>
        <DefinitionGraph characters={characters} showAnswer={showAnswer}></DefinitionGraph>
      </div>
    </GraphSoundQuestionStyle>
  )
}

function MeaningQuestion({ card, definition, showSynonyms, showL2LengthHint, characters, showAnswer }) {
  return (<>
    <div className="row" style={{justifyContent: "center", alignItems: "center"}}>
      <StyledQuestion> {card && card.front
        ? card.front
        : (
          <MeaningWrapper>
            <Meaning showSynonyms={showSynonyms} definition={definition} />
            {showL2LengthHint && <div key="lenHint">(L2 length: {definition.graph.length})</div>}
          </MeaningWrapper>
        )
      }
      </StyledQuestion>
    </div>
    <div className="row" style={{justifyContent: "center", alignItems: "center"}}>
      <DefinitionGraph characters={characters} showAnswer={showAnswer}></DefinitionGraph>
    </div>
  </>
  )
}

function GraphAnswer({ card, definition, showSynonyms }) {
  return (
    <div>
      {card && card.back ? card.back :
        <>
          <div style={{ display: "flex", alignItems: "center" }}>
            <StyledAnswer> {definition.sound} </StyledAnswer>
            <button type="button" onClick={() => say(definition.graph)}
              className="btn btn-primary btn-user btn-block" style={{ marginLeft: "2em" }}>Say it!</button>
          </div>
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
        <MeaningWrapper><Meaning showSynonyms={showSynonyms} definition={definition} /></MeaningWrapper>
      }
    </div>
  )
}

function MeaningAnswer({ card, definition }) {
  return (
    <div>
      {card && card.back ? card.back :
        <div style={{ display: "flex", alignItems: "center" }}>
          <StyledAnswer> {definition.sound} </StyledAnswer>
          <button type="button" onClick={() => say(definition.graph)}
            className="btn btn-primary btn-user btn-block" style={{ marginLeft: "2em" }}>Say it!</button>
        </div>
      }
    </div>
  )
}

function getAnswer(card, definition, characters, showSynonyms) {
  console.debug(`answer is here`, card)
  const cardType = card.cardId.split(CARD_ID_SEPARATOR)[1];
  switch (cardType) {
    case CARD_TYPES.GRAPH.toString(): return (<GraphAnswer card={card} definition={definition} characters={characters} showSynonyms={showSynonyms} />);
    case CARD_TYPES.SOUND.toString(): return (<SoundAnswer card={card} definition={definition} characters={characters} showSynonyms={showSynonyms} />);
    case CARD_TYPES.MEANING.toString(): return (<MeaningAnswer card={card} definition={definition} characters={characters} showSynonyms={showSynonyms} />);
  }
}

function getQuestion(card, definition, characters, showSynonyms, showL2LengthHint, showAnswer) {
  console.debug(`Card to show for a question`, card)
  const cardType = card.cardId.split(CARD_ID_SEPARATOR)[1];
  switch (cardType) {
    case CARD_TYPES.GRAPH.toString(): return (<GraphQuestion card={card} definition={definition} characters={characters} showSynonyms={showSynonyms}
      showAnswer={showAnswer} />);
    case CARD_TYPES.SOUND.toString(): return (<SoundQuestion card={card} definition={definition} characters={characters} showSynonyms={showSynonyms}
      showAnswer={showAnswer} />);
    case CARD_TYPES.MEANING.toString(): return (<MeaningQuestion card={card} definition={definition} characters={characters} showSynonyms={showSynonyms}
      showL2LengthHint={showL2LengthHint} showAnswer={showAnswer} />);
  }
}

export class VocabRevisor extends Component {
  constructor(props) {
    super(props);
    this.handlePractice = this.handlePractice.bind(this);
  }
  // componentDidUpdate(prevProps) {
  //   const { showAnswer } = this.props;
  //   if (showanswer && showAnswer !== prevProps.showAnswer) {
  //
  //   }
  // }
  handlePractice(...args){
    this.props.onPractice(...args);
  }

  render() {
    console.log(`VocabRevisor this.props`, this.props)
    const showAnswer = this.props.showAnswer;
    const { currentCard, definition, characters, loading } = this.props;
    const { showSynonyms, showL2LengthHint } = this.props.activityConfig ;
    return (
      <>
        {loading && <SearchLoading src="/static/img/loader.gif" />}
        {(!loading && !definition) && <span>No review items loaded</span>}
        {(!loading && definition)
          && (
          <>
            <QuestionWrapper>
              {getQuestion(currentCard, definition, characters, showSynonyms, showL2LengthHint, showAnswer)}
            </QuestionWrapper>
            {!showAnswer &&
              <CentredFlex>
                <button style={{marginTop: "1em"}} className="btn btn-large btn-primary" onClick={this.props.onShowAnswer}>Show Answer</button>
              </CentredFlex>
            }
            {showAnswer &&
              <>
                <AnswerWrapper>{getAnswer(currentCard, definition, characters, showSynonyms)}</AnswerWrapper>
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
