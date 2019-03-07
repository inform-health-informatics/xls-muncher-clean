"""Command-line entry point for the XLS muncher."""

import argparse


def munch():
    """Run the import."""
    parser = argparse.ArgumentParser(
        description="Import planned surgical procedures from a single Excel file")
    parser.add_argument('xls_file',
                        help='path to the Excel file to import')
    parser.add_argument('--verbose', '-v',
                        action='count', default=0,
                        help='print more information about the import process')
    args = parser.parse_args()
    from .ingester import ingest_file
    ingest_file(args.xls_file, verbose=args.verbose)


def dump_db():
    """Show all procedures in the database (for debugging)."""
    from .database import Procedure, Session

    with Session.scope() as session:
        for procedure in session.query(Procedure).all():
            print(procedure)

# TODO: Dump DB to an Excel spreadsheet with all info
