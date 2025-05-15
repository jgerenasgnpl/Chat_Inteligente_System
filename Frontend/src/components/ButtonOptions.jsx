import React from 'react';
import { Button } from 'antd';

const ButtonOptions = ({ options, onClick }) => {
  if (!options || options.length === 0) return null;

  return (
    <div style={{ marginTop: 10 }}>
      {options.map((opt, idx) => (
        <Button
          key={idx}
          size="small"
          style={{ marginRight: 5 }}
          onClick={() => onClick(opt)}
        >
          {opt}
        </Button>
      ))}
    </div>
  );
};

export default ButtonOptions;
