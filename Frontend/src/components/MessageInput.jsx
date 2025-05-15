import React, { useState } from 'react';
import { Input, Button } from 'antd';

const MessageInput = ({ onSend }) => {
  const [text, setText] = useState('');

  const handleSend = () => {
    if (!text.trim()) return;
    onSend(text);
    setText('');
  };

  return (
    <div style={{ marginTop: 10 }}>
      <Input.TextArea
        rows={2}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onPressEnter={(e) => {
          if (!e.shiftKey) {
            e.preventDefault();
            handleSend();
          }
        }}
        placeholder="Escribe tu mensaje aquí"
      />
      <Button type="primary" onClick={handleSend} style={{ marginTop: 5 }}>
        Enviar
      </Button>
    </div>
  );
};

export default MessageInput;
