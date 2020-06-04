#################
Advanced Features
#################

Advanced features and detailed information for using Kubernetes with Runway.


***************************
Setting KUBECONFIG Location
***************************

If using a non-default kubeconfig location, you can provide it using Runway's option for setting environment variables.
This can be set as a relative path or an absolute one.

.. code-block:: yaml

  ---
  deployments:
    - modules:
        - path: myk8smodule
          env_vars:
            KUBECONFIG:
              - .kube
              - ${env DEPLOY_ENVIRONMENT}
              - config

This would set `KUBECONFIG` to ``<path_to_runway.yml>/.kube/$DEPLOY_ENVIRONMENT/config`` where ``$DEPLOY_ENVIRONMENT`` is the current Runway :ref:`deploy environment <term-deploy-env>`.


----


.. _k8s-version:

******************
Version Management
******************

By specifying the version via a ``.kubectl-version`` file in your overlay directory, or a module option, Runway will automatically download & use that version for the module.
This is recommended to keep a predictable experience when deploying your module.

Without a version specified, Runway will fallback to whatever ``kubectl`` it finds first in your PATH.

.. rubric:: .kubectl-version
.. code-block::

  1.14.5

.. rubric:: runway.yml

Lookups can be used to provide different versions for each :ref:`deploy environment <term-deploy-env>`.

.. code-block:: yaml

  ---
  deployments:
    - modules:
        - path: sampleapp.k8s
          options:
            kubectl_version: ${var kubectl_version.${env DEPLOY_ENVIRONMENT}}
    - module:
        - sampleapp-01.k8s
        - sampleapp-02.k8s
      module_options:
        kubectl_version: 1.14.5
