import React from 'react';
import { FaFrown, FaMeh, FaSmile, FaCheck } from 'react-icons/fa';
import { GRADE } from '../js/schemas.js';
import styled from 'styled-components';

const PracticerStyle = styled.div`
  display: flex;
  justify-content: space-evenly;
  padding: .5em;
`;

const SexyButton = styled.button`
  border: none;
  background: none;
  cursor: pointer;
  &:focus {
    outline: 2px dashed #17171D;
  }
  &:hover {
    svg {
      transform: scale(1.1);
    }
  }
  &::-moz-focus-inner {
    border: 0;
  }
  svg {
    outline: none;
    transition: transform 0.15s linear;
  }
`;

class PracticerInput extends React.Component {
  addOrUpdateCards(grade) {
    console.log('addOrUpdateCards got clicked');
    this.props.onPractice(this.props.practiceObject, grade)
  }
  render(){
    return <PracticerStyle>
      <SexyButton title="I don't know this word yet"><FaFrown onClick={() => this.addOrUpdateCards(GRADE.UNKNOWN)} /></SexyButton>
      <SexyButton title="I am not confident with this word"><FaMeh onClick={() => this.addOrUpdateCards(GRADE.HARD)} /></SexyButton>
      <SexyButton title="I am comfortable with this word"><FaSmile onClick={() => this.addOrUpdateCards(GRADE.GOOD)} /></SexyButton>
      <SexyButton title="I know this word, I don't need to revise it again"><FaCheck onClick={() => this.addOrUpdateCards(GRADE.KNOWN)} /></SexyButton>
    </PracticerStyle>;
  }
}

export default PracticerInput;
