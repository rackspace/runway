"""Packaging settings."""

from codecs import open as codecs_open
from os.path import abspath, dirname, join

from setuptools import find_packages, setup

from runway import __version__


THIS_DIR = abspath(dirname(__file__))
with codecs_open(join(THIS_DIR, 'README.rst'), encoding='utf-8') as readfile:
    LONG_DESCRIPTION = readfile.read()


INSTALL_REQUIRES = [
    'Send2Trash',
    'docopt',
    'flake8',
    'flake8-docstrings',
    'pep8-naming',
    'future',
    'pyhcl',
    # pylint v2+ is only py3 compatible; doesn't make sense to offer it
    # until runway is py3 compatible
    'pylint~=1.9',
    'yamllint',
    # embedded stacker is v1.3.0 with the following patches applied:
    # https://github.com/cloudtools/stacker/pull/565 (arbitrary command hook)
    # https://github.com/cloudtools/stacker/pull/607 (per hook enable/disable)
    # and the LICENSE file added to its root folder
    # and the following files/folders deleted:
    #   * tests
    #   * blueprints/testutil.py
    # and the stacker & stacker.cmd scripts adapted with EMBEDDED_LIB_PATH
    'stacker~=1.3',
    # upstream stacker requires boto3>=1.3.1 & botocore>=1.6.0, but
    # unfortunately pip will mess up on transitive dependecies
    # https://github.com/pypa/pip/issues/988
    # Best option here seems to be to just require the latest version of boto3
    # (since that's what's most often going to be installed) and the matching
    # compatible botocore version. It's more rigid than necessary, but should
    # hopefully make users less likely to encounter an error OOTB.
    'botocore>=1.9.0',
    'boto3>=1.6.0'
]
SCRIPTS = ['scripts/stacker-runway', 'scripts/stacker-runway.cmd']

setup(
    name='runway',
    version=__version__,
    description='Simplify infrastructure/app testing/deployment',
    long_description=LONG_DESCRIPTION,
    url='https://github.com/onicagroup/runway',
    author='Onica Group LLC',
    author_email='opensource@onica.com',
    license='Apache License 2.0',
    classifiers=[
        'Intended Audience :: Developers',
        'Topic :: Utilities',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        # 'Programming Language :: Python :: 3',
        # 'Programming Language :: Python :: 3.5',
        # 'Programming Language :: Python :: 3.6',
    ],
    # Python 3 support blocked by
    # https://github.com/remind101/stacker/issues/465
    python_requires='~=2.6',
    keywords='cli',
    packages=find_packages(exclude=['docs', 'tests*']),
    install_requires=INSTALL_REQUIRES,
    extras_require={
        'test': ['flake8', 'pep8-naming', 'flake8-docstrings', 'pylint'],
    },
    entry_points={
        'console_scripts': [
            'runway=runway.cli:main',
        ],
    },
    scripts=SCRIPTS,
    include_package_data=True,  # needed for templates
    test_suite='tests'
)
