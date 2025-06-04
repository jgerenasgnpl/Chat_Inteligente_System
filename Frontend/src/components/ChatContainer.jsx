import React, { useState, useEffect } from 'react';
import { Card, Input, Button, List, Typography, Spin, message } from 'antd';
import { enviarMensaje, obtenerHistorial } from '../services/api';

const { Text } = Typography;

// ✅ COMPONENTE MEJORADO CON SOPORTE PARA:
// - Intenciones en mensajes
// - Botones con payloads complejos  
// - Mensajes automáticos cuando se hace clic en botones
// - Manejo flexible de estructuras de respuesta del backend

const ChatContainer = () => {
  const [messages, setMessages] = useState([]); // ✅ Siempre inicializar como array
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
        
        // ✅ Validar estructura del historial según tu backend
        console.log('Respuesta del historial:', response);
        
        let historialMessages = [];
        let conversationIdFromHistory = null;
        
        if (response && response.messages && Array.isArray(response.messages)) {
          // Estructura: {conversation_id: 1, messages: Array(48), total: 48}
          historialMessages = response.messages;
          conversationIdFromHistory = response.conversation_id;
        } else if (response && response.data && response.data.messages && Array.isArray(response.data.messages)) {
          // Estructura alternativa: {data: {conversation_id: 1, messages: Array(48)}}
          historialMessages = response.data.messages;
          conversationIdFromHistory = response.data.conversation_id;
        } else if (response && Array.isArray(response)) {
          // Si viene directamente como array
          historialMessages = response;
        } else {
          console.warn('La respuesta del historial no tiene la estructura esperada:', response);
          historialMessages = [];
        }
        
        setMessages(historialMessages);
        
        // ✅ Log adicional para depurar la estructura de mensajes
        if (historialMessages.length > 0) {
          console.log('Estructura del primer mensaje:', historialMessages[0]);
          console.log('Estructura del último mensaje:', historialMessages[historialMessages.length - 1]);
        }
        
        // Usar el conversation_id del historial si existe
        if (conversationIdFromHistory) {
          setConversationId(conversationIdFromHistory);
        } else if (historialMessages.length > 0 && historialMessages[0].conversation_id) {
          setConversationId(historialMessages[0].conversation_id);
        }
      } catch (error) {
        console.error('Error al cargar historial:', error);
        message.error('No se pudo cargar el historial');
        setMessages([]); // ✅ Asegurar que sea un array vacío en caso de error
      } finally {
        setLoading(false);
      }
    };
    
    fetchHistory();
  }, [userId]);
  
  // ✅ Enviar mensaje de texto (mejorado)
  const handleSendMessage = async (intention = null) => {
    if (!inputText.trim()) return;
    
    try {
      setLoading(true);
      
      // ✅ Validar que messages sea un array antes de hacer spread
      const currentMessages = Array.isArray(messages) ? messages : [];
      
      // Añadir mensaje del usuario al chat (optimista)
      setMessages(prev => {
        const prevArray = Array.isArray(prev) ? prev : [];
        return [...prevArray, {
          id: Date.now(),
          sender_type: 'user',
          text_content: inputText,
          timestamp: new Date().toISOString()
        }];
      });
      
      // Guardar el texto antes de limpiar
      const messageText = inputText;
      
      // Limpiar input
      setInputText('');
      
      // ✅ Enviar mensaje al backend con intención opcional
      const response = await enviarMensaje(userId, messageText, null, conversationId, intention);
      
      console.log('Respuesta del envío:', response);
      
      // ✅ Actualizar conversationId si es la primera vez
      if (!conversationId) {
        if (response && response.conversation_id) {
          setConversationId(response.conversation_id);
        } else if (response && response.data && response.data.conversation_id) {
          setConversationId(response.data.conversation_id);
        }
      }
      
      // ✅ Añadir respuesta del sistema con manejo flexible de estructura
      setMessages(prev => {
        const prevArray = Array.isArray(prev) ? prev : [];
        
        let responseText = '';
        let responseButtons = [];
        
        if (response && response.response) {
          responseText = response.response;
          responseButtons = response.buttons || [];
        } else if (response && response.message) {
          responseText = response.message;
          responseButtons = response.buttons || [];
        } else if (response && response.data) {
          responseText = response.data.message || response.data.response;
          responseButtons = response.data.buttons || [];
        } else {
          responseText = 'Respuesta del sistema';
        }
        
        const newMessage = {
          id: Date.now() + 1,
          sender_type: 'system',
          text_content: responseText,
          timestamp: new Date().toISOString(),
          buttons: responseButtons
        };
        return [...prevArray, newMessage];
      });
      
    } catch (error) {
      console.error('Error al enviar mensaje:', error);
      message.error('No se pudo enviar el mensaje');
      
      // ✅ Revertir el mensaje optimista en caso de error
      setMessages(prev => {
        const prevArray = Array.isArray(prev) ? prev : [];
        return prevArray.filter(msg => msg.text_content !== inputText);
      });
    } finally {
      setLoading(false);
    }
  };
  
  // ✅ FUNCIÓN MEJORADA PARA MANEJAR BOTONES CON PAYLOADS
  const handleButtonClick = async (button) => {
    try {
      setLoading(true);
      
      // ✅ Extraer datos del botón (puede ser solo ID o un objeto completo)
      let buttonId = null;
      let messageText = null;
      let intention = null;
      
      if (typeof button === 'string' || typeof button === 'number') {
        // Botón simple con solo ID
        buttonId = button;
      } else if (button && button.payload) {
        // Botón con payload complejo
        messageText = button.payload.message;
        intention = button.payload.intention;
        buttonId = button.id;
      } else if (button && button.id) {
        // Botón con ID simple
        buttonId = button.id;
        messageText = button.text;
      }
      
      // ✅ Mostrar mensaje del usuario si hay texto
      if (messageText) {
        setMessages(prev => {
          const prevArray = Array.isArray(prev) ? prev : [];
          return [...prevArray, {
            id: Date.now(),
            sender_type: 'user',
            text_content: messageText,
            timestamp: new Date().toISOString()
          }];
        });
      }
      
      // ✅ Enviar selección al backend con intención
      const response = await enviarMensaje(
        userId, 
        messageText, 
        buttonId, 
        conversationId, 
        intention
      );
      
      console.log('Respuesta del botón:', response);
      
      // ✅ Añadir respuesta del sistema
      setMessages(prev => {
        const prevArray = Array.isArray(prev) ? prev : [];
        
        let responseText = '';
        let responseButtons = [];
        
        if (response && response.response) {
          responseText = response.response;
          responseButtons = response.buttons || [];
        } else if (response && response.message) {
          responseText = response.message;
          responseButtons = response.buttons || [];
        } else if (response && response.data) {
          responseText = response.data.message || response.data.response;
          responseButtons = response.data.buttons || [];
        } else {
          responseText = 'Respuesta del sistema';
        }
        
        const newMessage = {
          id: Date.now() + 1,
          sender_type: 'system',
          text_content: responseText,
          timestamp: new Date().toISOString(),
          buttons: responseButtons
        };
        return [...prevArray, newMessage];
      });
      
    } catch (error) {
      console.error('Error al seleccionar opción:', error);
      message.error('No se pudo procesar la selección');
    } finally {
      setLoading(false);
    }
  };
  
  // ✅ Asegurar que messages sea siempre un array
  const safeMessages = Array.isArray(messages) ? messages : [];
  
  return (
    <Card title="Chat de Negociación" style={{ width: '100%', maxWidth: 600, margin: '0 auto' }}>
      <div style={{ height: 400, overflowY: 'auto', marginBottom: 16, padding: 8 }}>
        {loading && safeMessages.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 20 }}>
            <Spin size="large" />
          </div>
        ) : (
          <List
            itemLayout="horizontal"
            dataSource={safeMessages}
            renderItem={(item, index) => (
              <div key={item.id || index} style={{ 
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
                  <Text>
                    {/* ✅ Manejo flexible de diferentes estructuras de mensaje */}
                    {item.text_content || item.message || item.content || 'Mensaje sin contenido'}
                  </Text>
                </div>
                
                {/* ✅ Botones de respuesta mejorados */}
                {item.buttons && Array.isArray(item.buttons) && item.buttons.length > 0 && (
                  <div style={{ marginTop: 8, textAlign: 'left' }}>
                    {item.buttons.map((btn, btnIndex) => {
                      // ✅ Determinar el texto del botón según su estructura
                      let buttonText = '';
                      if (btn.text) {
                        buttonText = btn.text;
                      } else if (btn.payload && btn.payload.message) {
                        buttonText = btn.payload.message;
                      } else if (btn.label) {
                        buttonText = btn.label;
                      } else if (btn.title) {
                        buttonText = btn.title;
                      } else {
                        buttonText = `Opción ${btnIndex + 1}`;
                      }
                      
                      return (
                        <Button 
                          key={btn.id || btnIndex}
                          type="default"
                          style={{ marginRight: 8, marginBottom: 8 }}
                          onClick={() => handleButtonClick(btn)}
                          disabled={loading}
                        >
                          {buttonText}
                        </Button>
                      );
                    })}
                  </div>
                )}
              </div>
            )}
          />
        )}
      </div>
      
      <div style={{ display: 'flex' }}>
        <Input
          placeholder="Escribe un mensaje..."
          value={inputText}
          onChange={e => setInputText(e.target.value)}
          onPressEnter={() => handleSendMessage()}
          disabled={loading}
          style={{ marginRight: 8 }}
        />
        <Button 
          type="primary" 
          onClick={() => handleSendMessage()}
          loading={loading}
        >
          Enviar
        </Button>
      </div>
    </Card>
  );
};

export default ChatContainer;