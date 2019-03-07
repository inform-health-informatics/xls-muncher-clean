"""
Make a fake workbook constuctor that builds the right thing
"""

from .xls import Workbook as xlsWorkbook
from .xlsx import Workbook as xlsxWorkbook

def Workbook(file_path): #  pylint: disable=I0011, C0103
    """Construct a Workbook object by opening an Excel file for reading.

    :param file_path: path to the Excel file. The file extension will be used
        to determine format
    """
    if file_path.endswith('.xlsx'):
        return xlsxWorkbook(file_path)
    else:
        return xlsWorkbook(file_path)
