import React from "react";

const NataliaResponder = ({ messages }) => {
  const ultimaEntrada = messages[messages.length - 1];

  if (ultimaEntrada && ultimaEntrada.text.includes("hola")) {
    return <div className="bot-response">Hola, ¿cómo puedo ayudarte hoy?</div>;
  }

  return null;
};

export default NataliaResponder;
