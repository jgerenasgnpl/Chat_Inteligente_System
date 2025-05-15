import axios from 'axios';

const API = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000'
});

// Usar la ruta con prefijo duplicado que funciona
export const enviarMensaje = (user_id, text, button_selected = null, conversation_id = null) => {
  console.log(`Enviando mensaje a: ${API.defaults.baseURL}/api/v1/api/v1/chat/message`);
  
  return API.post('/api/v1/api/v1/chat/message', {
    user_id,
    message: text,
    button_selected,
    conversation_id
  });
};

// También actualizar la ruta para el historial
export const obtenerHistorial = (user_id, conversation_id = null) => {
  // Verificar si esta ruta existe también con prefijo duplicado
  const url = conversation_id 
    ? `/api/v1/api/v1/chat/historial/${user_id}?conversation_id=${conversation_id}`
    : `/api/v1/api/v1/chat/historial/${user_id}`;
  
  console.log(`Obteniendo historial desde: ${API.defaults.baseURL}${url}`);
  
  return API.get(url);
};

// Actualizar también esta función
export const obtenerConversaciones = (user_id, active_only = false) => {
  return API.get(`/api/v1/api/v1/chat/conversations?user_id=${user_id}&active_only=${active_only}`);
};