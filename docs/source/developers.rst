.. _developers:
.. highlight:: shell

Developers
==========

Getting Started
---------------

Before getting started, [fork this repo](https://help.github.com/en/github/getting-started-with-github/fork-a-repo) and [clone your fork](https://help.github.com/en/github/creating-cloning-and-archiving-repositories/cloning-a-repository).

Development Environment
~~~~~~~~~~~~~~~~~~~~~~~

This project uses ``pipenv`` to create Python virtual environment. This must be installed on your system before setting up your dev environment.


With pipenv installed, run ``make sync_all`` to setup your development environment. This will create all the requred virtual environments to work on runway, build docs locally, and run integration tests locally. The virtual environments all have Runway installed as editable meaning as you make changes to the code of your local clone, it will be reflected in all the virtual environments.


Travis CI
---------

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
| ``NPM_PACKAGE_NAME``      | Name to use when publishing an npm package.  |
+---------------------------+----------------------------------------------+
| ``NPM_PACKAGE_VERSION``   | Override the version number used for npm.    |
+---------------------------+----------------------------------------------+

**Travis CI User Permissions Example**

.. code-block:: json

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
