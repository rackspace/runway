.. _mod-cdk:

Helm
====

This module manages the deployment of Helm Charts in a Kubernetes cluster.

Overview
--------
Helm is a package manager for Kubernetes. Helm Charts help to define, install, and upgrade even the most complex Kubernetes application.
This type of module adds support to include Helm charts in a runway deployment.

Adding a Helm module
--------------------
Start by adding the Helm directory to your Runway modules.

Directory tree:
::

    .
    ├── runway.yml
    └── helloworld.helm
        ├── .helm-version
        └── Chart.yaml

runway.yml:
::

    ---
    deployments:
      - modules:
          - helloworld.helm
        regions:
          - us-east-1
    env_vars:
        dev:
            KUBECONFIG: .kube/dev/config

Specifying the Helm Version
---------------------------
By specifying the version via a ``.helm-version`` file in your chart directory, Runway will automatically download and use that version for the module. This is mandatory to keep a predictable experience when deploying your module.

.helm-version::

    1.14.5

Setting KUBECONFIG location
---------------------------

If using a non-default kubeconfig location, you can provide it using Runway's option for setting environment variables. This can be set as an absolute one or a relative path like in the example above.