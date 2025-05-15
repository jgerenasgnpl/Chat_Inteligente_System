import React, { useState, useEffect } from 'react';
import { Card, Input, Button, List, Typography, Spin, message } from 'antd';
import { enviarMensaje, obtenerHistorial } from '../services/api';

const { Text } = Typography;

const ChatContainer = () => {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [inputText, setInputText] = useState('');
  const [userId] = useState('1'); // En producción, esto vendría de la autenticación
  const [conversationId, setConversationId] = useState(null);
  
  // Cargar historial al inicio
  useEffect(() => {
    const fetchHistory = async () => {
      try {
        setLoading(true);
        const response = await obtenerHistorial(userId);
        setMessages(response.data);
        
        // Si hay mensajes, obtener el ID de conversación
        if (response.data.length > 0) {
          setConversationId(response.data[0].conversation_id);
        }
      } catch (error) {
        console.error('Error al cargar historial:', error);
        message.error('No se pudo cargar el historial');
      } finally {
        setLoading(false);
      }
    };
    
    fetchHistory();
  }, [userId]);
  
  // Enviar mensaje
  const handleSendMessage = async () => {
    if (!inputText.trim()) return;
    
    try {
      setLoading(true);
      
      // Añadir mensaje del usuario al chat (optimista)
      setMessages(prev => [...prev, {
        id: Date.now(),
        sender_type: 'user',
        text_content: inputText,
        timestamp: new Date().toISOString()
      }]);
      
      // Limpiar input
      setInputText('');
      
      // Enviar mensaje al backend
      const response = await enviarMensaje(userId, inputText, null, conversationId);
      
      // Actualizar conversationId si es la primera vez
      if (!conversationId) {
        setConversationId(response.data.conversation_id);
      }
      
      // Añadir respuesta del sistema
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        sender_type: 'system',
        text_content: response.data.message,
        timestamp: new Date().toISOString(),
        buttons: response.data.buttons
      }]);
      
    } catch (error) {
      console.error('Error al enviar mensaje:', error);
      message.error('No se pudo enviar el mensaje');
    } finally {
      setLoading(false);
    }
  };
  
  // Manejar clic en botón
  const handleButtonClick = async (buttonId) => {
    try {
      setLoading(true);
      
      // Enviar selección al backend
      const response = await enviarMensaje(userId, null, buttonId, conversationId);
      
      // Añadir respuesta del sistema
      setMessages(prev => [...prev, {
        id: Date.now(),
        sender_type: 'system',
        text_content: response.data.message,
        timestamp: new Date().toISOString(),
        buttons: response.data.buttons
      }]);
      
    } catch (error) {
      console.error('Error al seleccionar opción:', error);
      message.error('No se pudo procesar la selección');
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <Card title="Chat de Negociación" style={{ width: '100%', maxWidth: 600, margin: '0 auto' }}>
      <div style={{ height: 400, overflowY: 'auto', marginBottom: 16, padding: 8 }}>
        <List
          itemLayout="horizontal"
          dataSource={messages}
          renderItem={item => (
            <div style={{ 
              textAlign: item.sender_type === 'user' ? 'right' : 'left',
              marginBottom: 12
            }}>
              <div style={{
                display: 'inline-block',
                padding: '8px 12px',
                borderRadius: 8,
                maxWidth: '80%',
                backgroundColor: item.sender_type === 'user' ? '#1890ff' : '#f0f0f0',
                color: item.sender_type === 'user' ? 'white' : 'black'
              }}>
                <Text>{item.text_content}</Text>
              </div>
              
              {/* Botones de respuesta */}
              {item.buttons && item.buttons.length > 0 && (
                <div style={{ marginTop: 8, textAlign: 'left' }}>
                  {item.buttons.map(btn => (
                    <Button 
                      key={btn.id}
                      type="default"
                      style={{ marginRight: 8, marginBottom: 8 }}
                      onClick={() => handleButtonClick(btn.id)}
                    >
                      {btn.text}
                    </Button>
                  ))}
                </div>
              )}
            </div>
          )}
        />
      </div>
      
      <div style={{ display: 'flex' }}>
        <Input
          placeholder="Escribe un mensaje..."
          value={inputText}
          onChange={e => setInputText(e.target.value)}
          onPressEnter={handleSendMessage}
          disabled={loading}
          style={{ marginRight: 8 }}
        />
        <Button 
          type="primary" 
          onClick={handleSendMessage}
          loading={loading}
        >
          Enviar
        </Button>
      </div>
    </Card>
  );
};

export default ChatContainer;