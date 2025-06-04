import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const API = axios.create({
  baseURL: BASE_URL
});

export const enviarMensaje = async (user_id, text, button_selected = null, conversation_id = null, intention = null) => {
  const payload = { 
    user_id, 
    message: text, 
    button_selected, 
    conversation_id 
  };
  
  if (intention) {
    payload.intention = intention;
    console.log('🎯 Enviando con intención:', intention);
  }
  
  const res = await API.post('/api/v1/api/v1/chat/message', payload);
  return res.data; 
};

export const obtenerHistorial = async (user_id, conversation_id = null) => {
  const url = conversation_id
    ? `/api/v1/api/v1/chat/historial/${user_id}?conversation_id=${conversation_id}` // ✅ Estructura correcta
    : `/api/v1/api/v1/chat/historial/${user_id}`; // ✅ Estructura correcta
  const res = await API.get(url);
  return res.data; 
};

export const obtenerConversaciones = async (user_id, active_only = false) => {
  const res = await API.get(
    `/api/v1/api/v1/chat/conversations?user_id=${user_id}&active_only=${active_only}` // ✅ Estructura correcta
  );
  return res.data;
};