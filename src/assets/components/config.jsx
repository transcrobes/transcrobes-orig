import React from "react";
import Popup from 'reactjs-popup';
import { FaBars } from 'react-icons/fa';
import styled from 'styled-components';

export const StyledPopup = styled(Popup)`
  &-content[role=tooltip] {
    width: 250px;
  }
`;

export const ConfigButton = React.forwardRef(({ open, ...props }, ref) => (
  // FIXME: understand why the popup goes to the right if the width isn't set!
  <div style={{width: '2em', paddingBottom: '8px'}} ref={ref}>
    <FaBars {...props}> </FaBars>
  </div>
));
