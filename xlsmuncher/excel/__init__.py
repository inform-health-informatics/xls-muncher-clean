"""
This module abstracts away the differences in interface for the libraries
working with .xls and .xlsx files, so the rest of the code doesn't need to
worry about what type of file it's dealing with.
"""

from .common import column_name_to_index  # noqa
from .workbook import Workbook  # noqa
