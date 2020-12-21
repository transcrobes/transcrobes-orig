import React, { Component } from 'react';
import styled from 'styled-components';

function RowItem({item, gradeOrder}){
  // FIXME: migrate the style to a styled-component
  return (
    <div style={{display: 'flex', justifyContent: 'space-between'}}>
      <div>{item.graph}</div>
      <div>{gradeOrder[item.clicks].icon}</div>
    </div>
  )
}

function MeaningTooltip({item}){
  return (
    <DescriptionText>
      <div>
        <div>
          Pinyin: {item.sound.join(' ')}
        </div>
        <div>
          Meaning: {item.meaning}
        </div>
      </div>
    </DescriptionText>
  )
}

const TipText = styled.div`
  border: 1px #333 solid;
  padding:3px;
  width:80%;
  font-size:150%;
  page-break-inside:avoid;
`;

const DescriptionText = styled.div`
  display:none;
  position:absolute;
  border:1px solid #000;
  padding:5px;
  background-color: white;
  opacity: 1;
  ${TipText}:hover & {
    display: block;
  }
`;

export class VocabItem extends Component {
  constructor(props) {
    super(props);
    this.handleClick = this.handleClick.bind(this);
    this.handleMouseOver = this.handleMouseOver.bind(this);
  };

  handleMouseOver(e) {
    e.preventDefault();
    this.props.onMouseOver(this.props.index)
  }

  handleClick(e) {
    e.preventDefault();
    this.props.onGradeUpdate(this.props.index)
  }

  render(){
    return (
      <TipText>
        <div onClick={this.handleClick} onMouseEnter={this.handleMouseOver} onMouseLeave={this.props.onMouseOut} >
          <RowItem item={this.props.item} gradeOrder={this.props.gradeOrder} />
          <MeaningTooltip item={this.props.item} />
        </div>
      </TipText>
    )
  }
}
