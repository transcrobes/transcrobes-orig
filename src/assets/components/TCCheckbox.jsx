import React from 'react';

export default function TCCheckbox({ name, label, isSelected, onCheckboxChange }) {
  return (
    <div className="form-check">
      <label htmlFor={name}>
        <input
          type="checkbox"
          name={name}
          checked={isSelected}
          onChange={onCheckboxChange}
          className="form-check-input"
        />
        {label}
      </label>
    </div>
  )
}
