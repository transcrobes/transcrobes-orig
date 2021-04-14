import React, { Component } from "react";
import { SRSrobesConfig } from "./srsrobes-config.jsx";
import { StyledPopup, ConfigButton } from "./config.jsx";

export class SRSrobesConfigLauncher extends Component {
  render() {
    return (
        <StyledPopup
          disabled={this.props.loading}
          trigger={open => <ConfigButton open={open} />}
          position="right top">
          <SRSrobesConfig activityConfig={this.props.activityConfig} onConfigChange={this.props.onConfigChange} />
        </StyledPopup>
    );
  }
}
