from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base_class import Base  # o donde tengas tu declarative_base()

class FlowState(Base):
    __tablename__ = "flow_states"
    id   = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    # relación opcional a transiciones que parten de este estado
    transitions = relationship("FlowTransition", back_populates="state")

class FlowAction(Base):
    __tablename__ = "flow_actions"
    id      = Column(Integer, primary_key=True, index=True)
    name    = Column(String, unique=True, index=True)
    type    = Column(String, nullable=False)  # por ejemplo "ejecutar_consulta_bd"
    payload = Column(Text, nullable=True)      # aquí podrías guardar tu query o configuración

class FlowCondition(Base):
    __tablename__ = "flow_conditions"
    id         = Column(Integer, primary_key=True, index=True)
    expression = Column(Text, nullable=False)  # ej: "context['saldo_total'] > 0"

class FlowTransition(Base):
    __tablename__ = "flow_transitions"
    id             = Column(Integer, primary_key=True, index=True)
    state_id       = Column(Integer, ForeignKey("flow_states.id"), nullable=False)
    condition_id   = Column(Integer, ForeignKey("flow_conditions.id"), nullable=True)
    action_id      = Column(Integer, ForeignKey("flow_actions.id"), nullable=True)
    next_state_id  = Column(Integer, ForeignKey("flow_states.id"), nullable=False)

    # relaciones
    state      = relationship("FlowState", foreign_keys=[state_id], back_populates="transitions")
    condition  = relationship("FlowCondition", foreign_keys=[condition_id])
    action     = relationship("FlowAction",  foreign_keys=[action_id])