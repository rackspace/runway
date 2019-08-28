.. _developers:
.. highlight:: json

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

Travis CI
^^^^^^^^^

If you would like to simulate a fully build/deploy of runway on your fork,
you can do so by first signing up and `Travis CI <https://travis-ci.org/>`_
and linking it to your GitHub account. After doing so, there are a few
environment variables that can be setup for your environment.

Travis CI Environment Variables
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

+---------------------------+----------------------------------------------+
| ``AWS_ACCESS_KEY_ID``     | Credentials required to deploy build         |
|                           | artifacts to S3 at the end of the build      |
|                           | stage. See below for permission requirements.|
+---------------------------+----------------------------------------------+
| ``AWS_BUCKET``            | S3 bucket name where build artifacts will be |
|                           | pushed.                                      |
+---------------------------+----------------------------------------------+
| ``AWS_BUCKET_PREFIX``     | Prefix for all build artifacts published to  |
|                           | S3.                                          |
+---------------------------+----------------------------------------------+
| ``AWS_DEFAULT_REGION``    | Region where S3 bucket is located.           |
+---------------------------+----------------------------------------------+
| ``AWS_SECRET_ACCESS_KEY`` | Credentials required to deploy build         |
|                           | artifacts to S3 at the end of the build      |
|                           | stage. See below for permission requirements.|
+---------------------------+----------------------------------------------+
| ``FORKED``                | Used to enable the deploy steps in a forked  |
|                           | repo.                                        |
+---------------------------+----------------------------------------------+
| ``NPM_API_KEY``           | API key from NPM.                            |
+---------------------------+----------------------------------------------+
| ``NPM_EMAIL``             | Your email address tied to the API key.      |
+---------------------------+----------------------------------------------+
| ``NPM_PACKAGE_NAME``      | Name to use when publishing an npm package   |
+---------------------------+----------------------------------------------+

**Travis CI User Permissions Example**

::

    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "s3:PutObject",
                    "s3:PutObjectVersionAcl",
                    "s3:PutObjectTagging",
                    "s3:PutObjectAcl",
                    "s3:GetObject"
                ],
                "Resource": "arn:aws:s3:::$BUCKET_NAME/$PREFIX/*"
            },
            {
                "Sid": "RequiredForCliSyncCommand",
                "Effect": "Allow",
                "Action": [
                    "s3:ListBucket"
                ],
                "Resource": [
                    "arn:aws:s3:::$BUCKET_NAME"
                ]
            }
        ]
    }
