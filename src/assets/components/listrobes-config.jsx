import React, { Component } from "react";
import { DragDropContext, Droppable, Draggable } from "react-beautiful-dnd";
import styled from 'styled-components';
import 'reactjs-popup/dist/index.css';
import Select from 'react-select';
import TCCheckbox from './TCCheckbox.jsx';

// a little function to help us with reordering the result
const reorder = (list, startIndex, endIndex) => {
  const result = Array.from(list);
  const [removed] = result.splice(startIndex, 1);
  result.splice(endIndex, 0, removed);

  return result;
};

const Row = styled.div`
  border: solid;
  display: flex;
  justify-content: space-between;
  padding: 4px;
  margin: 4px;
`;

// const Checkbox = ({ label, isSelected, onCheckboxChange }) => (
//   <div className="form-check">
//     <label>
//       <input
//         type="checkbox"
//         name={label}
//         checked={isSelected}
//         onChange={onCheckboxChange}
//         className="form-check-input"
//       />
//       {label}
//     </label>
//   </div>
// );

export class ListrobesConfig extends Component {
  constructor(props) {
    super(props);
    this.handleDragEnd = this.handleDragEnd.bind(this);
    this.handleForceWcpmChange = this.handleForceWcpmChange.bind(this);
    this.handleItemsPerPageChange = this.handleItemsPerPageChange.bind(this);
    this.handleWordListsChange = this.handleWordListsChange.bind(this);
  }

  handleDragEnd(result) {
    // dropped outside the list
    if (!result.destination) {
      return;
    }

    const gradeOrder = reorder(
      this.props.graderConfig.gradeOrder,
      result.source.index,
      result.destination.index
    );

    this.props.onConfigChange({...this.props.graderConfig, gradeOrder: gradeOrder});
  }

  handleForceWcpmChange(e){
    this.props.onConfigChange({...this.props.graderConfig, forceWcpm: e.target.checked});
  }

  handleWordListsChange(selectedLists){
    const selectedMap = new Map(selectedLists.map(x => [x.value, x]))
    const newWordLists = _.cloneDeep(this.props.graderConfig.wordLists);
    for (const wordList of newWordLists) {
      wordList.selected = selectedMap.has(wordList.value);
    }
    this.props.onConfigChange({...this.props.graderConfig, wordLists: newWordLists});
  }

  handleItemsPerPageChange(e){
    this.props.onConfigChange({...this.props.graderConfig, itemsPerPage: parseInt(e.target.value, 10)});
  }

  render() {
    const gradeOrder = this.props.graderConfig.gradeOrder;
    return (
      <div>
        <div>
          Taps for state
        </div>
        <div>
          <DragDropContext onDragEnd={this.handleDragEnd}>
            <Droppable droppableId="droppable">
              {(provided, snapshot) => (
                <div
                  {...provided.droppableProps}
                  ref={provided.innerRef}
                >
                  {gradeOrder.map((item, index) => (
                    <Draggable key={item.id} draggableId={item.id} index={index}>
                      {(provided, snapshot) => (
                        <Row
                          ref={provided.innerRef}
                          {...provided.draggableProps}
                          {...provided.dragHandleProps}
                        >
                          <div style={{paddingRight: '8px'}}>{index}</div><div>{item.content}</div>{item.icon}
                        </Row>
                      )}
                    </Draggable>
                  ))}
                  {provided.placeholder}
                </div>
              )}
            </Droppable>
          </DragDropContext>
        </div>
        <div>
          Source word lists
            <Select
            onChange={this.handleWordListsChange}
            defaultValue={this.props.graderConfig.wordLists.filter(x => x.selected)}
            isMulti
            name="wordLists"
            options={this.props.graderConfig.wordLists}
            className="basic-multi-select"
            classNamePrefix="select"
          />
        </div>
        <div>
          <TCCheckbox label="Force word count per million ordering"
            isSelected={this.props.graderConfig.forceWcpm} onCheckboxChange={this.handleForceWcpmChange} />
        </div>
        <div style={{ display: "flex", justifyContent: "space-between" }}>
          <label htmlFor="itemsPerPage">Items per page (1 to 250)</label>
          <input style={{width: "30%"}} name="itemsPerPage" min="1" max="250" type="number"
            value={this.props.graderConfig.itemsPerPage} onChange={this.handleItemsPerPageChange} />
        </div>
      </div>
    );
  }
}
