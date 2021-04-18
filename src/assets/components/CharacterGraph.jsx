import React, { Component } from 'react'
import HanziWriter from 'hanzi-writer';

const WIDTH = 150;
const HEIGHT = 150;
// const SWIDTH = WIDTH.toString();
// const SHEIGHT = HEIGHT.toString();
// const SHALF_WIDTH = (WIDTH/2).toString();
// const SHALF_HEIGHT = (HEIGHT/2).toString();

function s(num, half=false){
  return (num/(half ? 2 : 1)).toString();
}

export default class CharacterGraph extends Component {
  componentDidUpdate(prevProps) {
    const { animate, character, index, showAnswer, } = this.props;
    if (!!showAnswer) {
      this.state.hanzi.cancelQuiz();
      this.state.hanzi.showCharacter();
      this.state.hanzi.showOutline();
    }
    if (animate && animate !== prevProps.animate) {
      console.debug('Animating character', character);
      this.state.hanzi.animateCharacter({
        onComplete: () => { this.props.onAnimateFinished(index, character) }
      });
    }
  }

  componentDidMount() {
    const { graph, structure } = this.props.character;
    const { showAnswer, width, height } = this.props;
    console.debug('Updating from CharacterGraph mount', graph, structure);
    const options = {
      width: width || WIDTH,
      height: height || HEIGHT,
      padding: 3,
      // quiz options
      showCharacter: showAnswer,
      showOutline: showAnswer,
      // animate options
      strokeAnimationSpeed: 2, // 2x normal speed
      delayBetweenStrokes: 300, // milliseconds
      radicalColor: '#337ab7', // blue
      charDataLoader: () => structure,
    }

    const hanzi = HanziWriter.create(graph, graph, options);
    if (!showAnswer) {
      hanzi.quiz({
        leniency: 2.0,  // default 1.0, min 0, max???
      });
    };
    this.setState({
      hanzi: hanzi,
    });
  }

  render() {
    const { character, width, height } = this.props;
    const SWIDTH = s(width || WIDTH);
    const SHEIGHT = s(height || HEIGHT);
    const SHALF_WIDTH = s(width || WIDTH, true);
    const SHALF_HEIGHT = s(height || HEIGHT, true);
    return (
      <div style={{ padding: ".1em"}}>
        <svg xmlns="http://www.w3.org/2000/svg" width={SWIDTH} height={SHEIGHT} id={character.graph}>
          <line x1="0" y1="0" x2={SWIDTH} y2={SHEIGHT} stroke="#DDD" />
          <line x1={SWIDTH} y1="0" x2="0" y2={SHEIGHT} stroke="#DDD" />
          <line x1={SHALF_WIDTH} y1="0" x2={SHALF_WIDTH} y2={SHEIGHT} stroke="#DDD" />
          <line x1="0" y1={SHALF_HEIGHT} x2={SWIDTH} y2={SHALF_HEIGHT} stroke="#DDD" />
        </svg>
      </div>
    )
  }
}
