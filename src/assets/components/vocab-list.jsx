import React, { Component } from 'react';
import { VocabItem } from './vocab-item.jsx';
import SearchLoading from './SearchLoading.jsx';

export class VocabList extends Component {
  constructor(props) {
    super(props);
  };

  render() {
    const { vocab, loading } = this.props;
    const unloaded = (loading || !vocab)
    return (
      <>
        {unloaded && <SearchLoading src="/static/img/loader.gif" />}
        {!unloaded && vocab.length === 0 && <span>No remaining vocabulary items</span>}
        {!unloaded &&
          vocab.map((vocabItem, index) => {
            return (
              <VocabItem key={vocabItem.graph} item={vocabItem} gradeOrder={this.props.graderConfig.gradeOrder}
                index={index} onGradeUpdate={this.props.onGradeChange} onMouseOver={this.props.onMouseOver}
                onMouseOut={this.props.onMouseOut} />
            );
          })
        }
        {!unloaded &&
          (<div style={{ width: '100%', paddingTop: '1em' }}>
            <button className="btn btn-primary btn-user btn-block" onClick={this.props.onValidate} style={{ width: '80%' }} type="button">Validate</button>
          </div>)
        }
      </>
    );
  }
}
