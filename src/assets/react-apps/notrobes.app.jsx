import React from "react";
import ReactDOM from "react-dom";
import Notrobes from "../components/notrobes.jsx";
import "../css/notrobes.css";

class App extends React.Component {
	render() {
		return (
			<div>
				<Notrobes proxy={window.wproxy} />
			</div>
		);
	}
}

ReactDOM.render( <App/>, document.getElementById('root') );
