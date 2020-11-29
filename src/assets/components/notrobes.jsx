import React from 'react';
import '../css/notrobes.css';
import axios from 'axios';
import Loader from '../img/loader.gif';
import Plus from '../img/plus.png';
import Good from '../img/good.png';

const auth = (typeof csrftoken === 'undefined') ?
    [ "Authorization", "Basic " + btoa(username + ":" + password)] :
    [ "X-CSRFToken", csrftoken ]

const urlBase = (typeof apiUrl === 'undefined') ? '' : apiUrl;

const headers = {
    "Accept": "application/json",
    "Content-Type": "application/json",
};

headers[auth[0]] = auth[1];

var timeoutId;
const lookedAtDuration = 2000;  // ms

class Notrobes extends React.Component {
    constructor( props ) {
        super( props );

        this.state = {
            query: '',
            tags: '',
            results: {},
            loading: false,
            message: '',
        };

        this.cancel = '';
    }

    /**
     * Fetch the search results and update the state with the result.
     * Also cancels the previous query before making the new one.
     *
     * @param {String} query Search Query.
     *
     */
    fetchSearchResults = ( query ) => {
        const searchUrl = `${urlBase}/enrich/word_definitions`;

        if( this.cancel ) {
            this.cancel.cancel();
            if (timeoutId) {
                window.clearTimeout(timeoutId);
                timeoutId = null;
            }
        }
        this.cancel = axios.CancelToken.source();

        axios.post( searchUrl, { data: query }, {
            cancelToken: this.cancel.token,
            headers: headers
        } )
            .then( res => {
                const resultNotFoundMsg = ! res.data
                                        ? 'There are no more search results. Please try a new search'
                                        : '';
                this.setState( {
                    results: res.data,
                    message: resultNotFoundMsg,
                    loading: false
                } )

                if (!timeoutId) {
                    // I tried putting this in a function, but failed... :-(
                    timeoutId = window.setTimeout(function() {
                        timeoutId = null;
                        const eventUrl = `${urlBase}/user_event/`;
                        const eventData = { type: 'bc_word_lookup',
                          data : {
                            target_word: query,
                            target_sentence: ""
                          }
                        }
                        axios.post( eventUrl, eventData, {
                            headers: headers
                        } )
                            .then( res => {
                                console.log(`Submitted word lookup for ${query}`);
                            } )
                            .catch( error => {
                                if ( axios.isCancel(error) || error ) {
                                    this.setState({
                                        loading: false,
                                        message: `Failed to send the lookup event ${query}. Please check network`
                                    })
                                }
                            } )
                    }, lookedAtDuration);
                }
            } )
            .catch( error => {
                if ( axios.isCancel(error) || error ) {
                    this.setState({
                        loading: false,
                        message: 'Failed to fetch the data. Please check network'
                    })

                    if (timeoutId) {
                        window.clearTimeout(timeoutId);
                        timeoutId = null;
                    }
                }
            } )
    };

    /*
     * Add/update note for the user
     *
     * @param {Json} the definition details
     */
    addNote(definition, event) {
        const postUrl = `${urlBase}/notes/set_word`;
        console.log(definition);
        const note = definition;
        const { tags } = this.state;
        note["Tags"] = tags.split(' ');

        if ( this.cancel ) {
            this.cancel.cancel();

            if (timeoutId) {
                window.clearTimeout(timeoutId);
                timeoutId = null;
            }
        }

        this.cancel = axios.CancelToken.source();

        axios.post( postUrl, note, {
            cancelToken: this.cancel.token,
            headers: headers
        } )
            .then( res => {
                console.log(res);
                const updateMessage = ( res.data.status != 'ok' )
                                        ? 'Failed to update the note. Please check network or contact support'
                                        : 'Successfully updated note';
                this.setState( {
                    message: updateMessage,
                    loading: false
                } );
                this.fetchSearchResults(definition.Simplified);
            } )
            .catch( error => {
                console.error(error);
                if ( axios.isCancel(error) || error ) {
                    this.setState({
                        message: 'Failed to update the note. Please check network or contact support',
                        loading: false
                    })
                }
            } )
    };

    mysendEvent(word){
    }

    handleOnInputChange = ( event ) => {
        const query = event.target.value;
        if ( ! query ) {
            this.setState( { query, results: {}, message: '' } );
        } else {
            this.setState( { query, loading: true, message: '' }, () => {
                this.fetchSearchResults( query );
            } );
        }
    };

    handleOnTagsChange = ( event ) => {
        const tags = event.target.value;
        this.setState( { tags } );
    };

    getStats(stats) {
        return (
            stats.map( result => {
                return (
                    <div key={ result.name } className="meta-item"><span className="meta-item-title"> { result.name }: </span><span className="meta-item-text"> { result.metas } </span>

                    <hr/>
                    </div>
                )
            } )
        )
    }

    getModelStats(modelStats) {
        return (
            modelStats.map( result => {
                return (
                    <div key={ result.last_seen } className="meta-item"><span className="meta-item-title"> Nb. seen: { result.nb_seen } </span><br/><span className="meta-item-text"> Last seen: { result.last_seen } </span><br/><span className="meta-item-text"> Nb. Checked: { result.nb_checked } </span><br/><span className="meta-item-text"> Last Checked: { result.last_checked } </span>

                    <hr/>
                    </div>
                )
            } )
        )
    }

    getDefinitions(defs) {
        return (
            defs.map( (result, ind) => {
                const res = (Array.isArray(result)) ? result[0] : result;  {/* currently multiple ways of returning */}
                return (
                    res &&
                    <div key={ ind } className="def-item">

                        <span className="def-item-add"><img src={ Plus } width="32" height="32" className="def-item-add-img" alt="Add note to learning"
                            onClick={ () => this.addNote(res) } /></span>
                        <span className="def-item-title"> { res.Pinyin }: </span>
                        <span className="def-item-text"> { res.Meaning }: </span>
                        <hr/>
                    </div>
                )
            } )
        )
    }

    getNotes(notes) {
        return (
            notes.map( (result, ind) => {
                return (
                    result && <div key={ ind } className="def-item"><span className="def-item-title"> { result.Pinyin }: </span><span className="def-item-text"> { result.Meaning } </span><span className="def-item-tags"> Tags: { result.Tags.join(', ') } </span></div>
                )
            } )
        )
    }

    renderSearchResults = () => {
        const { results } = this.state;

        if ( results.defs ) {
            console.log(results);
            return (
                <div className="results-container">
                    <h6 className="result-heading">Entry definitions</h6>
                    { results.defs.length &&
                        this.getDefinitions(results.defs)
                    }
                    <h6 className="result-heading">Entry fallback</h6>
                    { results.fallback.length &&
                        this.getDefinitions(results.fallback)
                    }
                    <h6 className="result-heading">Entry stats</h6>
                    { results.stats.length &&
                        this.getStats(results.stats)
                    }
                    <h6 className="result-heading">Entry personal stats</h6>
                    { results.modelStats.length &&
                        this.getModelStats(results.modelStats)
                    }
                    <h6 className="result-heading">Existing notes</h6>
                    { results.notes.length &&
                        this.getNotes(results.notes)
                    }
                </div>
            )
        }
    };

    render() {
        const { query, tags, loading, message } = this.state;

        return (
            <div className="container">
            {/* Heading*/}
            <h2 className="heading">Add/edit your Transcrobes notes</h2>
            {/* Search Input*/}
            <div>
              <label className="search-label" htmlFor="search-input">
                  <input
                      type="text"
                      name="query"
                      value={ query }
                      id="search-input"
                      placeholder="Search..."
                      onChange={this.handleOnInputChange}
                  />
                  <i className="fa fa-search search-icon" aria-hidden="true"/>
              </label>
            </div>
            {/* Tags Input*/}
            <div>
              <label className="search-label" htmlFor="tags-input">
                  <input
                      type="text"
                      name="tags"
                      value={ tags }
                      id="tags-input"
                      placeholder="Enter your tags..."
                      onChange={this.handleOnTagsChange}
                  />
              </label>
              {/* Error Message*/}
                  {message && <p className="message">{ message }</p>}
            </div>
            {/* Loader*/}
            <img src={ Loader } className={`search-loading ${ loading ? 'show' : 'hide' }`} alt="loader"/>

            {/* Result*/}
            { this.renderSearchResults() }

            </div>
        )
    }
}

export default Notrobes
