
import React from 'react';

class Notes extends React.Component {
	constructor( props ) {
		super( props );

		this.state = {
			notes: '',
		};
	};

	render() {
		const { notes } = this.state;
        return (
            <div className="container">
                {/*	Heading */}
                <h2 className="heading">Existing notes</h2>
                {/* Note detail */}
                <p>{ JSON.stringify(notes) }</p>
            </div>
        )
	}
