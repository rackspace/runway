"""Packaging settings."""

from codecs import open as codecs_open
from os.path import abspath, dirname, join
from subprocess import call

from setuptools import Command, find_packages, setup

from runway import __version__


THIS_DIR = abspath(dirname(__file__))
with codecs_open(join(THIS_DIR, 'README.rst'), encoding='utf-8') as readfile:
    LONG_DESCRIPTION = readfile.read()


class RunTests(Command):
    """Run all tests."""

    description = 'run tests'
    user_options = []

    def initialize_options(self):
        """Implement dummy initialize_options method."""
        pass

    def finalize_options(self):
        """Implement dummy finalize_options method."""
        pass

    def run(self):  # pylint: disable=no-self-use
        """Run all tests."""
        errno = call(['py.test',
                      '--cov=runway',
                      '--cov-report=term-missing'])
        raise SystemExit(errno)


INSTALL_REQUIRES = [
    'docopt',
    'flake8',
    'flake8-docstrings',
    'pep8-naming',
    'future',
    'pylint',
    # 'stacker>=1.1.5',
    'yamllint'
] + [  # stacker dependencies
    'troposphere>=1.9.0',
    # upstream stacker requires boto3>=1.3.1 & botocore>=1.6.0, but
    # unfortunately pip will mess up on transitive dependecies
    # https://github.com/pypa/pip/issues/988
    # Best option here seems to be to just require the latest version of boto3
    # (since that's what's most often going to be installed) and the matching
    # compatible botocore version. It's more rigid than necessary, but should
    # hopefully make users less likely to encounter an error OOTB.
    'botocore>=1.9.0',
    'boto3>=1.6.0',
    "colorama~=0.3.7",  # likely won't be needed w/ Stacker 1.2
    'PyYAML~=3.12',
    'awacs>=0.6.0',
    'formic~=0.9b',
    'gitpython~=2.0',
    'schematics~=2.0.1',
    'python-dateutil~=2.0'
]
# embedded stacker is v1.1.4 with the following patches applied:
# https://github.com/remind101/stacker/pull/530 (slated for v1.2.0)
# https://github.com/remind101/stacker/pull/536 (in master)
# https://github.com/remind101/stacker/pull/538 (in master)
# https://github.com/remind101/stacker/pull/540 (in master)
# https://github.com/remind101/stacker/pull/541 (in master)
# and the following deleted:
#   * tests
#   * blueprints/testutil.py
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
        # 'Programming Language :: Python :: 3.2',
        # 'Programming Language :: Python :: 3.3',
        # 'Programming Language :: Python :: 3.4',
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
    cmdclass={'test': RunTests},
)
