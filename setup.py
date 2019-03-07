from setuptools import setup, find_packages

setup(name='xlsmuncher',
      version='0.1.0',
      description='Importing planned surgical procedure Excel spreadsheets to a database',
      url='https://github.com/uclh-critical-care/xls-muncher',
      author='Jonathan Cooper',
      author_email='j.p.cooper@ucl.ac.uk',
      classifiers=['Development Status :: 3 - Alpha',
                   'Programming Language :: Python',
                   'Programming Language :: Python :: 3',
                   'Operating System :: OS Independent',
                   'Intended Audience :: Science/Research',
                   'License :: Other/Proprietary License'],
      install_requires=['openpyxl', 'xlrd', 'sqlalchemy', 'pyyaml', 'python-dateutil'],
      python_requires='>=3.3',
      packages=find_packages(exclude=['*test']),
      package_data={
          # If any (sub-)package contains *.yaml files, include them:
          '': ['*.yaml']
      },
      entry_points={
          'console_scripts': [
              'xlsmunch = xlsmuncher.script:munch',
              'dump_proc_db = xlsmuncher.script:dump_db',
          ],
      },
      zip_safe=False
      )
