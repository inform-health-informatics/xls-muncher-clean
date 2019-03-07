
"""Fixtures for xlsmuncher tests."""

from contextlib import contextmanager
import os
import pytest
from sqlalchemy import event

from xlsmuncher.database import Session
from xlsmuncher.database.db import Base, connect


@pytest.fixture(scope='function')
def db():
    """Provides an isolated database session to tests."""
    # Connect to the DB and start a top-level transaction
    engine = connect(os.getenv('XLSMUNCHER_TEST_DB'), create_tables=False)
    connection = engine.connect()
    transaction = connection.begin()
    # Create our tables within the transaction, so we can roll this back too
    Base.metadata.create_all(connection)
    # Configure the session to use this connection
    Session.configure(bind=connection)

    # Override the default session_maker so it uses sub-transactions
    @contextmanager
    def nested_session_scope():
        """Provide a nested transactional scope around a series of operations."""
        session = Session()
        # Start the session in a SAVEPOINT
        session.begin_nested()

        # Each time the SAVEPOINT ends, reopen it
        @event.listens_for(session, "after_transaction_end")
        def restart_savepoint(session, trans):
            if trans.nested and not trans._parent.nested:
                # ensure that state is expired the way
                # session.commit() at the top level normally does
                session.expire_all()
                session.begin_nested()

        try:
            yield session
            session.commit()
        except:  # noqa
            session.rollback()
            raise
        finally:
            session.close()
    Session.scope = nested_session_scope

    # Provide the connection to tests
    try:
        yield connection
    finally:
        # Teardown - rollback everything that happened and disconnect
        transaction.rollback()
        connection.close()
        engine.dispose()
