import React from "react";
import ReactDOM from "react-dom";
import Listrobes from "../components/listrobes.jsx";

class App extends React.Component {
  render() {
    return (
      <Listrobes proxy={window.wproxy} />
    );
  }
}

ReactDOM.render( <App/>, document.getElementById('root') );
