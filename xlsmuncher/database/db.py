"""
This module handles database connections.
"""

from contextlib import contextmanager
from os import getenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .db_model import Base


Session = sessionmaker()  # Provides a session generator when connected
Session._connected = False  # Used to track whether connect() has been called


@contextmanager
def _session_scope():
    """Provide a transactional scope around a series of operations.

    Will connect to the default database if connect() has not been called explicitly.
    """
    if not Session._connected:
        connect()
    session = Session()
    try:
        yield session
        session.commit()
    except:  # noqa
        session.rollback()
        raise
    finally:
        session.close()


Session.scope = _session_scope


def connect(conn_string=None, create_tables=True):
    """Connect to a database.

    :param conn_string: specification of the connection. If None, the environment
        variable XLSMUNCHER_DB will be used instead
    :param create_tables: whether to create the tables we need
    :returns: the database engine
    """
    if conn_string is None:
        conn_string = getenv('XLSMUNCHER_DB')
    engine = create_engine(conn_string, echo=False)
    if create_tables:
        Base.metadata.create_all(engine)
    Session.configure(bind=engine)
    Session._connected = True
    return engine
