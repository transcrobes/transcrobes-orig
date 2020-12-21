import React, { Component } from "react";
import { IconContext } from "react-icons";
import { ListrobesConfig } from "./listrobes-config.jsx";
import { StyledPopup, ConfigButton } from "./config.jsx";

export class ListrobesConfigLauncher extends Component {
  constructor(props) {
    super(props);
  };

  render() {
    return (
      <IconContext.Provider value={{ color: "blue", size: '2em' }}>
        <StyledPopup
          disabled={this.props.loading}
          trigger={open => <ConfigButton open={open} />}
          position="right top">
          <ListrobesConfig graderConfig={this.props.graderConfig} onConfigChange={this.props.onConfigChange} />
        </StyledPopup>
      </IconContext.Provider>
    );
  }
}
