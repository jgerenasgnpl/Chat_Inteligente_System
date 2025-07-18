
from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class FlowState(Base):
    __tablename__ = "flow_states"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    transitions = relationship("FlowTransition", back_populates="state", foreign_keys="FlowTransition.state_id")

class FlowAction(Base):
    __tablename__ = "flow_actions"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    type = Column(String, nullable=False)
    payload = Column(Text, nullable=True)

class FlowCondition(Base):
    __tablename__ = "flow_conditions"
    id = Column(Integer, primary_key=True, index=True)
    expression = Column(Text, nullable=False)

class FlowTransition(Base):
    __tablename__ = "flow_transitions"
    id = Column(Integer, primary_key=True, index=True)
    state_id = Column(Integer, ForeignKey("flow_states.id"), nullable=False)
    condition_id = Column(Integer, ForeignKey("flow_conditions.id"), nullable=True)
    action_id = Column(Integer, ForeignKey("flow_actions.id"), nullable=True)
    next_state_id = Column(Integer, ForeignKey("flow_states.id"), nullable=False)
    state = relationship("FlowState", foreign_keys=[state_id], back_populates="transitions")
    condition = relationship("FlowCondition", foreign_keys=[condition_id])
    action = relationship("FlowAction", foreign_keys=[action_id])