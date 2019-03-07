
"""
This module is experimenting with a sample Excel ingest.
"""

import datetime
import os
import yaml

from dateutil.parser import parse as parse_date
from sqlalchemy.exc import IntegrityError, StatementError

from .database import Session, Procedure, Patient, procedure_constructor, has_required_fields
from .excel import column_name_to_index, Workbook


class FieldParser:
    """Extract a cell's data from Excel to form a DB field.

    This class handles the vagaries of different Excel layouts, by taking many options
    when instantiated defining different parsing approaches. Instances of this class
    form the values in a mapping from Excel column name, and specify how to parse cells
    in that column. There is (or will be!) logic to handle cases such as:
    - multiple columns in the Excel being concatenated to a single column in the DB
    - a single column in Excel being split into multiple DB columns
    - handling typical cases of malformed data (e.g. dates given as strings)
    - propagating data forward across rows to fill blanks (e.g. a surgery date given
      only at the start of a set of rows)
    - figuring out if a procedure has been cancelled by reading formatting info
    """

    def __init__(self, db_col_name,
                 extra_column=None,
                 data_insert_method='replace',
                 propagate_missing_values=False,
                 check_next_first=False,
                 cancellation_mark=None,
                 cancellation_colours=[],
                 extra_date_formats=[],
                 day_offsets={}):
        """Create a new field parser.

        :param db_col_name: the DB column into which parsed data will be written
        :param extra_column: the name of an extra DB column into which parsed data will be
            written. If this is supplied, the Excel cell is assumed to contain space-separated
            values, the last of which goes in the primary column and the rest in this one.
        :param data_insert_method: this controls the behaviour if multiple Excel columns
            map to a single DB column. The default is for later values to overwrite earlier
            ones, but 'append' may be passed to do string concatenation instead.
            TODO: Make the default 'error' instead?
        :param propagate_missing_values: if set, whenever this field is missing a value that
            from the previous parsed record will be used instead (which may itself have been
            propagated from an earlier record).
        :param check_next_first: if set, in conjunction with propagate_missing_values, a cell
            with missing value will check the *next* row before propagating a value from the
            previous record. This supports (.e.g) gynae files with a 'fake' merge cell in
            which the value is in the second row of a block.
        :param cancellation_mark: indicates if formatting on this field denotes a cancelled
            appointment (by default we do not check). Allowed values are:
            - 'strike': strikethrough formatting denotes a cancelled appointment
            - 'red': all red text denotes a cancelled appointment (just some words red does not)
            - 'background': background colour denotes a cancelled appointment. Relevant colours
              are given in the `cancellation_colours` parameter.
            - 'foreground': text colour denotes a cancelled appointment. Relevant colours
              are given in the `cancellation_colours` parameter.
        :param cancellation_colours: hex colour codes for backgrounds denoting cancelled appts.
        :param extra_date_formats: iterable of strftime format codes for use in parsing date
            strings. Usually dates will actually be dates in the Excel, but sometimes dates
            are represented as strings that Excel doesn't automatically convert to dates.
        :param day_offsets: dictionary mapping cell contents to offsets from the week start date,
            for use in the one-week-per-sheet layout.
        """
        self.db_col_name = db_col_name

        # Note that the following logic is wrong, but works here because
        # we know that columns that appear in both tables have the same definitions
        if db_col_name in Procedure.__table__.columns:
            self.db_col = Procedure.__table__.columns[db_col_name]
        else:
            self.db_col = Patient.__table__.columns[db_col_name]
        self.db_col_type = self.db_col.type.__class__.__name__
        self.extra_column_name = extra_column
        assert data_insert_method in {'replace', 'append'}
        self.data_insert_method = data_insert_method
        self.propagate_missing_values = propagate_missing_values
        self.check_next_first = check_next_first
        assert cancellation_mark in {None, 'strike', 'red', 'background', 'foreground'}
        self.cancellation_mark = cancellation_mark
        self.cancellation_colours = {col.lower() for col in cancellation_colours}
        self.extra_date_formats = extra_date_formats
        self.day_offsets = day_offsets
        self.value_transformers = {}

    def __repr__(self):
        """Allow nicer printing of dictionaries of FieldParsers."""
        return '<FieldParser({})>'.format(self.db_col_name)

    def set_date_basis(self, start_date):
        """Specify the base date for day_offsets.

        This will set `self.value_transformers` with the same keys as `self.day_offsets` but
        with the `start_date` added on.
        """
        for value, offset in self.day_offsets.items():
            self.value_transformers[value] = start_date + datetime.timedelta(days=offset)

    def parse_cell(self, cell, record, previous_record):
        """Parse data from a single cell into the given record.

        :param cell: the Excel cell to be parsed
        :param record: a dictionary of fields defining the procedure currently being
            parsed. The keys are column names in the DB. This method will fill in an
            entry corresponding to `cell`.
        :param previous_record: the complete dictionary record for the last procedure
            parsed.
        """
        value = cell.value
        # Check for value transformers
        if self.value_transformers and value:
            value = self.value_transformers[value]
        # Check for a malformed date that we have a format string for
        if self.db_col_type == 'Date' and isinstance(value, str) and value:
            for date_format in self.extra_date_formats:
                try:
                    value = datetime.datetime.strptime(value.strip(), date_format).date()
                except ValueError:
                    pass
                else:
                    break  # Parsed succesfully - don't try another format
            else:
                try:
                    value = parse_date(value, ignoretz=True, dayfirst=True, fuzzy=False).date()
                except ValueError:
                    # TODO: Consider warning/error logging in general
                    print('Unable to parse date "{}"'.format(value))
                    return
        # Coerce Excel datetime fields to dates where that's what we're expecting
        if self.db_col_type == 'Date' and isinstance(value, datetime.datetime):
            value = value.date()
        # Check for booleans represented as strings
        if self.db_col_type == 'Boolean' and isinstance(value, str):
            if value.lower() in ['n', 'no']:
                value = False
            elif value.lower() in ['y', 'yes']:
                value = True
        # Check whether to append or replace data, and assign to the record
        if (self.data_insert_method == 'append' and
                record.get(self.db_col_name, None) and value):
            record[self.db_col_name] += ' ' + value
        else:
            record[self.db_col_name] = value
        # Check for values split across columns
        if self.extra_column_name and value:
            parts = [part[::-1] for part in value[::-1].split(maxsplit=1)]
            record[self.db_col_name] = parts[0]
            parts.append(' ')  # Make sure there is a second value
            record[self.extra_column_name] = parts[1]
        # Check if we need to propagate a previous value
        if self.propagate_missing_values and record[self.db_col_name] in [None, '']:
            if self.check_next_first and previous_record is not None:
                next_cell = cell.sheet.cell(cell.row + 1, cell.col)
                # We pass None as previous_record to avoid calling recursively
                self.parse_cell(next_cell, record, None)
            if (record[self.db_col_name] in [None, ''] and previous_record and
                    previous_record.get(self.db_col_name) is not None):
                record[self.db_col_name] = previous_record[self.db_col_name]
        # Check for cancellations
        if self.cancellation_mark:
            mark = getattr(cell.font, self.cancellation_mark)
            if mark:
                if (not self.cancellation_mark.endswith('ground') or
                        mark in self.cancellation_colours):
                    record['cancelled'] = True


def read_config(file_path):
    """Read a YAML configuration file and build a config object.

    The returned dictionary may have the following fields:
    - surgical_pathway: fixed value for the surgical_pathway field
    - surgical_consultant: fixed value for the surgical_consultant field
    - columns: dictionary mapping Excel column headings to FieldParser objects

    :param file_path: path to the configuration file
    """
    config = {'columns': {}, 'sheets': []}
    with open(file_path, 'r') as file_stream:
        contents = yaml.safe_load(file_stream)
    # Global/fixed settings
    for setting, typ in {'surgical_pathway': str,
                         'surgical_consultant': str,
                         'sheets': list,
                         'week_start_date_cell': str,
                         'heading_row': int}.items():
        if setting in contents:
            if isinstance(contents[setting], typ):
                config[setting] = contents[setting]
            else:
                raise ValueError('Config setting {} has wrong type; expected {}, got {}'.format(
                    setting, typ.__name__, type(contents[setting]).__name__))
    # Set up field parsers
    if config.get('heading_row', 1) == 0:
        excel_name_field = 'excel_column'
    else:
        excel_name_field = 'excel_heading'
    for col_def in contents.get('columns', []):
        excel_name = col_def[excel_name_field].strip()
        db_name = col_def['column_name']
        kwargs = {}
        for arg_name in ['data_insert_method', 'propagate_missing_values', 'check_next_first',
                         'cancellation_mark', 'cancellation_colours', 'extra_date_formats',
                         'day_offsets', 'extra_column']:
            if arg_name in col_def:
                kwargs[arg_name] = col_def[arg_name]
        config['columns'][excel_name] = FieldParser(db_name, **kwargs)
    return config


def ingest_sheet(sheet, config, session, verbose=1):
    """Import a single sheet to the database.

    :param sheet: the Excel sheet object
    :param config: dictionary with configuration options,
        notably specifying how to parse Excel columns
    :param session: the DB session to write data to
    :param verbose: the verbosity level
    """
    if verbose >= 1:
        print('Ingesting sheet "{}"'.format(sheet.title))
    # Parse the heading row (if present) to determine which columns contain what data
    header_row_number = config.get('heading_row', 1)
    col_map = {}  # Map 0-based column index to FieldParser instance
    if header_row_number > 0:
        header_row = sheet.row(header_row_number - 1)
        for col_idx, cell in enumerate(header_row.cells()):
            cell_text = str(cell.value).strip()
            if verbose >= 2:
                print("{}: '{}' {}".format(col_idx, cell_text, cell_text in config['columns']))
            if cell_text in config['columns']:
                col_map[col_idx] = config['columns'][cell_text]
    else:
        # No heading row; the config contains Excel column names (A, B, etc.)
        for name, parser in config['columns'].items():
            col_map[column_name_to_index(name)] = parser
    if not col_map:
        print('Warning: sheet "{}" has no recognised columns'.format(sheet.title))
        return
    if verbose >= 1:
        print('Found columns:', col_map)
    # Set the base date on any parsers that need it
    if 'week_start_date_cell' in config:
        start_date = sheet.cell(name=config['week_start_date_cell']).value
        if start_date:
            start_date = parse_date(start_date).date()
            for parser in col_map.values():
                if parser.day_offsets:
                    parser.set_date_basis(start_date)
    # Now parse the remaining rows to find info on all procedures
    last_record = {}
    row_offset = header_row_number + 1
    for row_idx, row in enumerate(sheet.rows(skip_rows=row_offset - 1)):
        procedure_record = {}
        for field in ['surgical_pathway', 'surgical_consultant']:
            if field in config:
                procedure_record[field] = config[field]
        for col_idx, parser in col_map.items():
            if col_idx >= len(row):
                continue  # In some sheets later columns don't appear in all rows...
            if verbose >= 4:
                print('Add {}.{} = {}'.format(col_idx, parser.db_col_name, row.cell(col_idx).value))
            parser.parse_cell(row.cell(col_idx), procedure_record, last_record)
        if has_required_fields(procedure_record, verbose=verbose):
            procedure = procedure_constructor(**procedure_record)
            existing = procedure.find_existing(session)
            try:
                if existing:
                    if verbose >= 1:
                        print('Updating existing record', existing, 'with', procedure_record)
                    existing.update(procedure)
                else:
                    if verbose >= 1:
                        print('Adding new record', procedure, 'from', procedure_record)
                    session.add(procedure)
                session.commit()
            except (IntegrityError, StatementError) as e:
                print('Warning: ignoring row {}: {}'.format(row_offset + row_idx, e))
                session.rollback()
        last_record = procedure_record


def ingest_file(file_path, config_file_path=None, verbose=1):
    """Open an Excel file and import the data.

    :param file_path: path to the Excel file
    :param config_file_path: path to the YAML config file. If not given, a file
        with the same name as the Excel but different extension will be used.
    :param verbose: whether to output verbose progress file
    """
    if not config_file_path:
        config_file_path = os.path.splitext(file_path)[0] + '.yaml'
    if verbose >= 1:
        print('Opening workbook {} with config from {}'.format(file_path, config_file_path))

    config = read_config(config_file_path)
    book = Workbook(file_path)
    for sheet in book.sheets():
        if not config['sheets'] or sheet.title.strip() in config['sheets']:
            with Session.scope() as session:
                ingest_sheet(sheet, config, session, verbose=verbose)
