# Aim

Parse multiple excel sheets containing common information but with different layouts into a data store

# Roadmap

- [ ] @TODO 2017-10-04 set-up repo, anonymise first sheets
- [ ] @TODO 2017-10-04 define spec

# Installation and usage

This tool is designed to be installed within a Python virtual environment. Once you have set up a
(Python 3) virtualenv (or conda environment) you can install all dependencies and the package
itself with:
```sh
pip install -r requirements/local.txt
pip install -e .
```

This is a 'developer' install for people working on the package. End users can instead use:
```sh
pip install -r requirements/base.txt
pip install .
```

The package provides two command line programs for ingesting and displaying procedure data:
* `xlsmunch [-h] [--verbose] xls_file` ingests a single Excel file
* `dump_proc_db` displays a summary of each entry in the database

## Database setup

Before running for the first time, set up a postgres user and databases for the muncher to write to:
```sh
createuser xlsmuncher
createdb -O xlsmuncher xlsmuncher
createdb -O xlsmuncher xlsmuncher_test
```

Then ensure you have the following environment variables set whenever running:
```sh
export XLSMUNCHER_DB="postgresql://xlsmuncher:@localhost/xlsmuncher"
export XLSMUNCHER_TEST_DB="postgresql://xlsmuncher:@localhost/xlsmuncher_test"
```

If the database structure has changed since you last ran, you will need to drop and re-create the
database (in due course we'll set up automatic data migrations to avoid this):
```sh
dropdb xlsmuncher
createdb -O xlsmuncher xlsmuncher
```

## Running tests

From within the main project folder, simply run `pytest`.

To regenerate reference data, run `pytest --regen`.

# Navigation

```
-|
 |-data
 |  |-anonymised (raw excel sheets)
 |-xlsmuncher (python package)
```
