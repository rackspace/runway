.. _CloudFormation template: https://github.com/onicagroup/runway/blob/master/quickstarts/runway/runway-quickstart.yml
.. _Dockerfile: https://github.com/onicagroup/runway/blob/master/quickstarts/runway/Dockerfile
.. _Docker hub: https://hub.docker.com

Other Ways to Use Runway
========================

While we recommend using one of the install methods outlined in the
:ref:`Installation<install>` section, we realize that these may not be an
option for some so we have provided a `CloudFormation`_ template for spinning
up a deploy environment in AWS and a `Docker`_ image/Dockerfile that can be
used to run Runway.


CloudFormation
^^^^^^^^^^^^^^

This `CloudFormation template`_ is probably the easiest and quickest way to go
from "zero to Runway" as it allows for using an IAM Role eliminate the need to
configure API keys. The template will deploy your preference of Linux or
Windows Runway host. Windows Runway host includes vsCode, which some users may
find easier for manipulating Runway config files.


Docker
^^^^^^

Docker users can build their own Docker image to run a local Runway
container or modify this `Dockerfile`_ to build a Runway image to suit specific
needs.

We have also provide a pre-build Docker image on `Docker Hub`_ that can be
used with the following command.

.. code-block:: shell

    $ docker run -it --rm onica/runway-quickstart

