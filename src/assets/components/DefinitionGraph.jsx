import React, { Component } from 'react'
import CharacterGraph from './CharacterGraph.jsx';

export default class DefinitionGraph extends Component {
  constructor(props) {
    super(props);
    this.state = {
      animate: false,
      toAnimate: props.characters.map(x => 0)
    };
    this.onChildAnimateFinished = this.onChildAnimateFinished.bind(this);
  }

  draw(){
    console.debug('Starting the animation from the start');
    let toAnimate = this.props.characters.map(x => 0);
    toAnimate[0] = 1;
    this.setState({toAnimate});
  }

  onChildAnimateFinished(index, character) {
    console.debug(`Index ${index} animated, now doing the following with character`, character);
    let toAnimate = [...this.state.toAnimate];
    toAnimate[index] = 0;
    toAnimate[index + 1] = 1;
    this.setState({toAnimate});
  }

  render() {
    const { characters, showAnswer } = this.props;
    console.debug('Rendering DefinitionGraph with chars', characters);
    return (
      <div className="row" style={{alignItems: "center", justifyContent: "center"}}>
        { characters.filter(x => !!x).map((character, index) => {
            return (
              <CharacterGraph width={this.props.charWidth} height={this.props.charHeight}
              animate={this.state.toAnimate[index]} index={index} key={character.graph} character={character}
              onAnimateFinished={this.onChildAnimateFinished} showAnswer={showAnswer} />
            );
          })
        }
        {showAnswer &&
          <div><button style={{ marginLeft: "2em" }} type="button" onClick={() => this.draw()}
            className="btn btn-primary btn-user btn-block">Draw it!</button></div>
        }
      </div>
    );
  }
}
