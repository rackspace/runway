.. _developers:

Developers
==========

Want to work on the Runway code itself?

The simplest way to get started is to modify the source code in place while working on an existing project.

To do this, first ensure you can deploy the project successfully using the ``pipenv`` method of executing Runway.

Then, running the following command from your Runway project folder will check out out the latest source code
from Git and then will configure ``pipenv`` to use that code::

    $ pipenv install -e git+https://github.com/onicagroup/runway#egg=runway

(If you have your own fork, replace ``onicagroup`` appropriately.)

Where was the source code downloaded to? This command will tell you::

    $ pipenv --venv
    /Users/myname/.local/share/virtualenvs/my-project-name-d7VNcTay

From that folder, look in ``src/runway/runway``.

You can now edit the files there as you like, and whatever changes you make will be reflected when you
next execute Runway (using ``pipenv``) in the project folder.

