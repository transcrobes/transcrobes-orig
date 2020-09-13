import React from "react";
import ReactDOM from "react-dom";
import Notrobes from "./components/notrobes.jsx";


const root = document.getElementById("root");

class App extends React.Component {
	render() {
		return (
			<div>
				<Notrobes />
			</div>
		);
	}
}

ReactDOM.render( <App/>, document.getElementById('root') );
