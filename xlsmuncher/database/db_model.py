"""
This module stores the database models for the Excel muncher.
"""

import datetime
from sqlalchemy import (Column, ForeignKey,
                        Boolean, Integer, String, Text, Date)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Patient(Base):
    """
    This table stores common information about patients
    """

    __tablename__ = 'patient'

    # TODO: Discuss whether we want to allow NULL for more fields
    idmrn = Column(String(32), primary_key=True)
    patient_given_name = Column(String, nullable=False, index=True)
    patient_family_name = Column(String, nullable=False, index=True)
    date_of_birth = Column(Date, nullable=True)
    nhs_number = Column(String(10), nullable=True, index=True)
    sex = Column(Integer, nullable=True)


class Procedure(Base):
    """This database table stores key common information about planned surgical procedures."""
    __tablename__ = 'procedure'

    procedure_id = Column(Integer, autoincrement=True, primary_key=True)

    idmrn = Column(String(32), ForeignKey('patient.idmrn'))
    surgical_procedure = Column(String, nullable=False, index=True)
    surgical_date = Column(Date, nullable=False, index=True)
    # TODO: CareCast export won't have a date
    # TODO: Need to figure out how to track if an appointment date changes
    # TODO: What should we do if a procedure is no longer listed in a new version of a given file
    surgical_priority = Column(String, nullable=True)
    surgical_consultant = Column(String, nullable=True)
    surgical_pathway = Column(String, nullable=False)
    surgical_notes = Column(Text, nullable=True)

    pacu_request = Column(Boolean, nullable=True)

    # This allows us to track when an appointment is later cancelled
    cancelled = Column(Boolean, nullable=False, default=False)

    patient = relationship("Patient", back_populates="procedures")

    def __repr__(self):
        """Friendly display of procedure records."""
        kwargs = self.__dict__.copy()
        kwargs.update(self.patient.__dict__)
        return ("<Procedure {procedure_id} '{surgical_procedure}' on {surgical_date:%Y-%m-%d}"
                " for {patient_given_name} {patient_family_name} (MRN={idmrn}){cancel}"
                " PACU={pacu_request}>".format(
                    cancel=' CANCELLED' if self.cancelled else '',
                    **kwargs))

    def find_existing(self, session):
        """Determine whether this procedure is already in the DB.

        Existence is based on a row matching on the procedure_key fields.

        :param session: the DB session to use
        """
        q = session.query(
            Procedure
        ).filter_by(
            idmrn=self.idmrn,
            surgical_procedure=self.surgical_procedure,
            surgical_date=self.surgical_date
        )
        existing_proc = q.one_or_none()
        if existing_proc:
            return existing_proc

        # There is no matching procedure, but there might still be
        # a matching patient. Look it up.
        return session.merge(self)

    def update(self, other):
        """Update this record with non-null fields from another one.

        :param other: the other Procedure instance to update this one with
        """
        for col in Procedure.__table__.columns:
            if col.autoincrement is not True:
                new_val = getattr(other, col.name)
                if new_val is not None:
                    setattr(self, col.name, new_val)


Patient.procedures = relationship("Procedure", order_by=Procedure.surgical_date,
                                  back_populates="patient", cascade="all, delete-orphan")


def procedure_constructor(*, pacu_request=None, cancelled=False, **kwargs):
    """
    Constructor to split arguments between and Procedure and Patient
    """
    procedure_args = {}
    patient_args = {}
    kwargs['pacu_request'] = pacu_request
    kwargs['cancelled'] = cancelled
    for name, value in kwargs.items():
        if value is not None:
            augment_argument_map(procedure_args, name, value, Procedure)
            augment_argument_map(patient_args, name, value, Patient)

    person = Patient(**patient_args)
    proc = Procedure(**procedure_args)
    person.procedures = [proc]
    proc.patient = person

    return proc


def augment_argument_map(data, name, value, table):
    """
    A a value to an argument map if it supposed to be in that table
    """
    if name in table.__table__.columns:
        col_type = table.__table__.columns[name].type
        if isinstance(col_type, String):
            data[name] = str(value)
        elif isinstance(col_type, Boolean):
            data[name] = bool(value)
        elif isinstance(col_type, Date) and not isinstance(value, datetime.date):
            data[name] = None
        else:
            data[name] = value
