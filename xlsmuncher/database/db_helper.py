"""
Helper method for using the database from python
"""


from .db_model import Procedure, Patient


def all_db_columns():
    """
    Get a list of all the database columns
    """
    return Procedure.__table__.columns + Patient.__table__.columns


def has_required_fields(procedure, verbose=0):
    """Determine whether the given dictionary contains all our required fields.

    This avoids hitting the DB for the most common source of errors.
    """
    for field in all_db_columns():
        if not field.nullable and field.autoincrement is not True and field.default is None:
            if not procedure.get(field.name, None):
                if verbose >= 3:
                    print('Missing required field', field.name, 'in', procedure)
                return False
    return True
