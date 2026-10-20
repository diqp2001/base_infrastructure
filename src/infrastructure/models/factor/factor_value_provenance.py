"""
Provenance of stored factor values (BI-025 slice 2): one row per factor value that has recorded provenance, and
the lineage edges of derived values. New tables only — factor_values itself is unchanged (create_all adds them
to existing databases).
"""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from src.infrastructure.models import ModelBase as Base


class FactorValueProvenanceModel(Base):
    __tablename__ = "factor_value_provenance"

    factor_value_id = Column(Integer, ForeignKey("factor_values.id", ondelete="CASCADE"), primary_key=True)
    field = Column(String(100), nullable=False)
    source = Column(String(100), nullable=False)
    data_type = Column(String(50), nullable=False)          # SourceDataType value
    frequency = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False)             # ObservationStatus value
    received_at = Column(DateTime, nullable=True)            # naive UTC (mapper converts)
    ingested_at = Column(DateTime, nullable=True)            # naive UTC (mapper converts)
    rejection_reason = Column(Text, nullable=True)
    transformation = Column(String(255), nullable=True)
    policy_version = Column(String(50), nullable=True)
    validations = Column(Text, nullable=True)               # JSON list of {rule, passed, reason}


class FactorValueLineageModel(Base):
    __tablename__ = "factor_value_lineage"

    factor_value_id = Column(Integer, ForeignKey("factor_values.id", ondelete="CASCADE"), primary_key=True)
    input_factor_value_id = Column(Integer, ForeignKey("factor_values.id"), primary_key=True)
    position = Column(Integer, nullable=False, default=0)   # order of the inputs as recorded
