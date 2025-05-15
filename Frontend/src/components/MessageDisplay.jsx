import React from 'react';
import { Card } from 'antd';
import ButtonOptions from './ButtonOptions'; 

const MessageDisplay = ({ message, onOptionClick }) => {
  const isBot = message.sender === 'bot';

  return (
    <div
      style={{
        display: 'flex',
        justifyContent: isBot ? 'flex-start' : 'flex-end',
        marginBottom: 10,
      }}
    >
      <Card style={{ background: isBot ? '#f5f5f5' : '#d9f7be', maxWidth: '70%' }}>
        <div>{message.text}</div>

        {/* renderizar los botones si hay opciones */}
        <ButtonOptions options={message.options} onClick={onOptionClick} />
      </Card>
    </div>
  );
};

export default MessageDisplay;
