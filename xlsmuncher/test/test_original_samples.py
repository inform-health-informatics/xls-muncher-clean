
"""Test the muncher against the original sample Excel files."""

import os
import pytest
import py.path
import yaml

from xlsmuncher.database import Session, Procedure, Patient
from xlsmuncher.ingester import ingest_file


@pytest.mark.parametrize('filename', [
    'gynae/gynae.xlsx',
    'headandneck/02 N Kalavrezos March 2015 onwards .xlsx',
    'headandneck/04.C Liew.xls',
    'orthopaedics/04. A Ghassemi.xls',
    'orthopaedics/11.E Taylor.xls',
    'orthopaedics/HADDAD 2016.xlsx',
    'thoracics/Thoracic OP List - June 2017.xls',
    'urology/ADOLESCENT UROLOGY/ADOLESCENCE  Theatre Diary 2014-2016.xls',
    'urology/RECONSTRUCTIVE UROLOGY/Mundy , Andrich/ARM THEATRE DIARY 2014-2016.xlsx',
])
def test_sample_data(pytestconfig, request, db, filename):
    # Ingest file
    full_path = pytestconfig.rootdir.join('data/anonymised', filename)
    ingest_file(str(full_path), verbose=0)

    ref_name = os.path.splitext(filename)[0] + '.yaml'
    ref_path = py.path.local(__file__).dirpath('data').join(ref_name)

    if pytestconfig.getoption('--regen'):
        # Regenerate reference data
        os.makedirs(os.path.dirname(ref_path), exist_ok=True)
        with Session.scope() as session:
            with open(ref_path, 'w') as file_stream:
                data = {}
                for procedure in session.query(Procedure).all():
                    proc_dict = {}
                    for col in procedure.__table__.columns:
                        proc_dict[col.name] = getattr(procedure, col.name)
                    for col in Patient.__table__.columns:  # pylint: disable=E1101
                        proc_dict[col.name] = getattr(procedure.patient, col.name)
                    data[procedure.id] = proc_dict
                yaml.safe_dump(data, file_stream)
    else:
        # Check contents against original ingest
        with open(ref_path, 'r') as file_stream:
            ref_data = yaml.safe_load(file_stream)

        with Session.scope() as session:
            data = session.query(Procedure).all()
            for count, procedure in enumerate(data):
                proc_dict = {}
                for col in procedure.__table__.columns:
                    proc_dict[col.name] = getattr(procedure, col.name)
                for col in Patient.__table__.columns:  # pylint: disable=E1101
                    proc_dict[col.name] = getattr(procedure.patient, col.name)
                # Rename id to procedure_id needed during the transition phase
                if 'procedure_id' in proc_dict:
                    proc_dict['id'] = proc_dict['procedure_id']
                    del proc_dict['procedure_id']
                assert proc_dict == ref_data[procedure.procedure_id]
            assert 1 + count == len(ref_data)
