import React from "react";
import ReactDOM from "react-dom";
import SRSrobes from "../components/srsrobes.jsx";

class App extends React.Component {
  render() {
    return (
      <SRSrobes proxy={window.wproxy} />
    );
  }
}

ReactDOM.render( <App/>, document.getElementById('root') );
