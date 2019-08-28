"""Packaging settings."""
import sys
from codecs import open as codecs_open
from os.path import abspath, dirname, join

from setuptools import find_packages, setup

from src.runway import __version__


THIS_DIR = abspath(dirname(__file__))
with codecs_open(join(THIS_DIR, 'README.rst'), encoding='utf-8') as readfile:
    LONG_DESCRIPTION = readfile.read()


INSTALL_REQUIRES = [
    'Send2Trash',
    'awacs',  # for embedded hooks
    # awscli included for embedded hooks and aws subcommand
    # version set to match stacker requirement and include awscli fix #4182
    'awscli>=1.16.191<2.0',
    'botocore>=1.12.111',  # matching awscli/boto3 requirement
    'boto3>=1.9.111<2.0',  # matching stacker requirement
    'cfn-lint',
    'docopt',
    'requests',
    'future',
    # embedded pyhcl is 0.3.12
    # with the LICENSE file added to its root folder
    # and the following patches applied
    # https://github.com/virtuald/pyhcl/pull/57
    'pyhcl~=0.3',
    'pyOpenSSL',  # For embedded hook & associated script usage
    'six',
    'typing;python_version<"3.5"',
    'yamllint',
    'zgitignore',  # for embedded hooks
    # embedded stacker is v1.7.0
    # with the LICENSE file added to its root folder
    # and the following patches applied
    # https://github.com/cloudtools/stacker/pull/731 (CAPABILITY_AUTO_EXPAND)
    # https://github.com/cloudtools/stacker/pull/744 (diffs via CFN changesets)
    # and the following files/folders deleted:
    #   * tests
    #   * blueprints/testutil.py
    # and the stacker & stacker.cmd scripts adapted with EMBEDDED_LIB_PATH
    'stacker~=1.7',
    # stacker's troposphere dep is more loose, but we need to ensure we use a
    # sufficiently recent version for compatibility embedded blueprints
    'troposphere>=2.4.2',
    # botocore pins its urllib3 dependency like this, so we need to do the
    # same to ensure v1.25+ isn't pulled in by pip
    'urllib3>=1.20,<1.25',
]

# ensuring pyyaml dep matches awscli
if sys.version_info[:2] == (2, 6):
    INSTALL_REQUIRES.append('PyYAML>=3.10,<=3.13')
    INSTALL_REQUIRES.append('cfn_flip<=1.2.0')  # 1.2.1+ require PyYAML 4.1+
else:
    INSTALL_REQUIRES.append('PyYAML>=4.1,<=5.1')
    INSTALL_REQUIRES.append('cfn_flip>=1.2.1')


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
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    python_requires='>=2.6',
    keywords='cli',
    # exclude=['docs', 'tests*'],
    packages=find_packages(where='src'),
    package_dir={"": "src"},
    install_requires=INSTALL_REQUIRES,
    extras_require={
        'test': ['flake8', 'pep8-naming', 'flake8-docstrings',
                 'mock~=3.0.5', 'pylint',
                 # python3 flake8-docstrings fails with pydocstyle 4:
                 # https://github.com/PyCQA/pydocstyle/issues/375
                 # newer versions do not support python2:
                 # https://github.com/PyCQA/pydocstyle/pull/374
                 'pydocstyle<4.0.0'],
    },
    entry_points={
        'console_scripts': [
            'runway=runway.cli:main',
        ],
    },
    scripts=['scripts/stacker-runway', 'scripts/stacker-runway.cmd',
             'scripts/tf-runway', 'scripts/tf-runway.cmd',
             'scripts/tfenv-runway', 'scripts/tfenv-runway.cmd'],
    include_package_data=True,  # needed for templates,blueprints,hooks
    test_suite='tests'
)
