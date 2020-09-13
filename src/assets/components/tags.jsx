import React from 'react';

class Tags extends React.Component {
	constructor( props ) {
		super( props );

		this.state = {
			tags: '',
		};
	};

	render() {
		const { tags } = this.state;

		return (
			<div className="container">
			{/*	Heading*/}
			<h2 className="heading">Notrobes: add/edit your Transcrobes notes</h2>
			{/* Search Input*/}
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

			{/*	Error Message*/}
				{message && <p className="message">{ message }</p>}

			{/*	Loader*/}
			<img src={ Loader } className={`search-loading ${ loading ? 'show' : 'hide' }`} alt="loader"/>

			{/*	Result*/}
			{ this.renderSearchResults() }

			</div>
		)
	}
}
