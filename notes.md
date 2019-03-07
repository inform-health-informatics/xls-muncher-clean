Command line script

Extract sheet level data
- folder (i.e. specialty)
- consultant name

Specify row entity (patient or procedure)

Discard header and footer data

Configuration file that specifies mapping of column names
- first name
- last name
- dob
- hospital number etc
- tci date
- procedure
- booking date
- combo of MRN + procedure + booking date should create unique key

Once extracted then map all to her row level entities
- row formatting
- row notes
- blank cells and what fill forward characteristic would mean

Second configuration file then explains how to handle these
- i.e. strike through means cancelled
- green means confirmed
- etc.

Data is then moved with timestamp into db
If matches existing patient/procedure combination then updates;
If doesn't match then creates an pt-proc-booking_date item
Hang metadata off that
