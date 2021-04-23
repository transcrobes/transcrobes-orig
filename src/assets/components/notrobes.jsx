import React from 'react';
import '../css/notrobes.css';
import axios from 'axios';
import Loader from '../img/loader.gif';
import { simpOnly, USER_STATS_MODE } from '../js/lib.js';
import Word from './Word.jsx';
import { IconContext } from 'react-icons';
import { Converter } from 'opencc-js';

const DATA_SOURCE = "notrobes.jsx";

// FIXME: add JWT and remove basic?
const auth = (typeof csrftoken === 'undefined') ?
  ["Authorization", "Basic " + btoa(username + ":" + password)] :
  ["X-CSRFToken", csrftoken]

const urlBase = (typeof apiUrl === 'undefined') ? '' : apiUrl;

const headers = {
  "Accept": "application/json",
  "Content-Type": "application/json",
};

headers[auth[0]] = auth[1];

var timeoutId;
const MIN_LOOKED_AT_EVENT_DURATION = 2000;  // ms
const MAX_ALLOWED_CHARACTERS = 6;  // FIXME: obviously only somewhat sensible for Chinese...

class Notrobes extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      proxy: props.proxy,
      query: '',
      wordListNames: {},
      userListWords: {},
      word: {},
      loading: false,
      initialised: false,
      converter: null,
      message: '',
    };

    this.cancel = '';
    this.addOrUpdateCards = this.addOrUpdateCards.bind(this);
    this.submitLookupEvents = this.submitLookupEvents.bind(this);
  }

  async componentDidMount() {
    this.state.proxy.sendMessage({
      source: DATA_SOURCE,
      type: "getUserListWords",
      value: {},
    }, (response) => {
      console.log('back from getUserListWords with ', response);
      const { wordListNames, userListWords } = response;
      this.setState({
        wordListNames,
        userListWords,
        converter: Converter({ from: 't', to: 'cn' }),
        initialised: true
      });
    });
  }

  submitLookupEvents(lookupEvents, userStatsMode) {
    this.state.proxy.sendMessage({
      source: DATA_SOURCE,
      type: "submitLookupEvents",
      value: { lookupEvents, userStatsMode },
    }, (response) => {
      console.log(`Lookup events submitted`, response)
    });
  }

  /**
   * Fetch the search results and update the state with the result.
   * Also cancels the previous query before making the new one.
   *
   * @param {String} query Search Query.
   *
   */
  async fetchSearchResults(query) {
    const searchUrl = `${urlBase}/enrich/word_definitions`;

    if (this.cancel) {
      this.cancel.cancel();
      if (timeoutId) {
        window.clearTimeout(timeoutId);
        timeoutId = null;
      }
    }
    this.cancel = axios.CancelToken.source();

    this.state.proxy.sendMessage({
      source: DATA_SOURCE,
      type: "getWordDetails",
      value: { graph: query },
    }, (response) => {
      console.log(`Attempted to getWordDetails, reponse is`, response)
      if (!!response.word && !!response.word.wordId) {
        this.setState({
          ...response,
          message: '',
          loading: false,
          lists: (this.state.userListWords[response.word.wordId] || []).map(x => (
            { listId: x.listId, name: this.state.wordListNames[x.listId], position: x.position }
          )),
        });
        if (!timeoutId) {
          const lookupEvent = { target_word: response.word.graph, target_sentence: "", };
          timeoutId = window.setTimeout(() => { this.submitLookupEvents([lookupEvent], USER_STATS_MODE.L1) },
            MIN_LOOKED_AT_EVENT_DURATION);
        }
      } else {
        console.log('Going to the server for ', query);
        axios.post(searchUrl, { data: query }, {
          cancelToken: this.cancel.token,
          headers: headers
        }).then(res => {
          const resultNotFoundMsg = !res.data
            ? 'There are no search results. Please try a new search'
            : '';
          console.log(resultNotFoundMsg, res);
          this.setState({
            // FIXME: need to get the characters here!!!
            word: res.data.definition,
            message: resultNotFoundMsg,
            loading: false
          })

          if (!timeoutId && !!res.data.definition) {
            const lookupEvent = { target_word: res.data.definition, target_sentence: "", };
            timeoutId = window.setTimeout(() => { this.submitLookupEvents([lookupEvent], USER_STATS_MODE.L1) },
              MIN_LOOKED_AT_EVENT_DURATION);
          }
        }).catch(error => {
            if (axios.isCancel(error) || error) {
              this.setState({
                loading: false,
                message: 'Failed to fetch the data. Please check network'
              });

              if (timeoutId) {
                window.clearTimeout(timeoutId);
                timeoutId = null;
              }
            }
          })
      }
    });
  };

  async addOrUpdateCards(definition, grade){
    console.debug(`doing the addOrUpdateCards in notrobes.jsx:`, definition, grade);
    this.state.proxy.sendMessage({
      source: DATA_SOURCE,
      type: "addOrUpdateCards",
      value: { wordId: definition.wordId, grade }
    }, (response) => {
      console.debug(`got response back from addOrUpdateCards in notrobes.jsx:`, response);
      const cards = response;
      this.setState({
        loading: false,
        message: 'Cards recorded',
        cards
      });
    });
  }

  handleOnInputChange = (event) => {
    const query = event.target.value;
    console.log('the query', query);
    if (!query) {
      this.setState({ query, word: {}, loading: false, message: '' });
    } else if (query && !simpOnly(query)) {
      console.debug('the query is not to enrich', query);
      this.setState({ query, word: {}, loading: false,
        message: 'Only simplified characters can be searched for' });
    } else if (query && this.state.converter(query) !== query) {
      console.debug('query contains traditional characters', query);
      this.setState({ query, word: {}, loading: false,
        message: 'The system does not support traditional characters' });
    } else if (query.length > MAX_ALLOWED_CHARACTERS){
      console.debug('Entered a query of more than 8 characters', query);
      this.setState({ query, word: {}, loading: false,
        message: `The system only handles words of up to ${MAX_ALLOWED_CHARACTERS} characters` });
    } else {
      this.setState({ query, loading: true, message: '' }, () => {
        this.fetchSearchResults(query);
      });
    }
  };

  renderSearchResults = () => {
    if (this.state.word && Object.entries(this.state.word).length > 0) {
      console.debug(`Rendering results for word ${this.state.word}`, this.state);
      return (
        <div>
          <Word definition={this.state.word} characters={this.state.characters} cards={this.state.cards} wordModelStats={this.state.wordModelStats}
            lists={this.state.lists} onPractice={this.addOrUpdateCards} />
        </div>
      )
    }
  };

  render() {
    const { query, loading, initialised, message } = this.state;
    return (
      <div className="container">
        {/* Heading */}
        <h2 className="heading">Notrobes: Vocabulary search, discover words</h2>
        {/* Search Input */}
        <div>
          <label className="search-label" htmlFor="search-input">
            <input
              type="text"
              name="query"
              value={query}
              id="search-input"
              placeholder="Search..."
              disabled={!initialised}
              onChange={this.handleOnInputChange}
            />
            <i className="fa fa-search search-icon" aria-hidden="true" />
          </label>
        </div>
        {/* Loader */}
        <img src={Loader} className={`search-loading ${(loading || !initialised) ? 'show' : 'hide'}`} alt="loader" />

        {/* Message */}
        {message && <div style={{ fontColor: "red", fontWeight: "bold", fontSize: "2em"}}>{message}</div>}

        {/* Result */}
        <IconContext.Provider value={{ color: "blue", size: '3em' }}>
          {this.renderSearchResults()}
        </IconContext.Provider>

      </div>
    )
  }
}

export default Notrobes
