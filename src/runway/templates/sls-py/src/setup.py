"""Package setup file."""
from setuptools import setup

setup(name='src',
      version='1.0.0',
      description='Lambda function package',
      packages=['src'],
      install_requires=[
          'PyYAML',
      ],
      zip_safe=False)
