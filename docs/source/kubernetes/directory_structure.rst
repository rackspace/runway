.. _k8s-directory-structure:

###################
Directory Structure
###################

Example directory structures for a :ref:`index:Kubernetes` :term:`Module`.

.. code-block::

  .
  ├── .gitignore
  ├── aws-auth-cm.k8s
  │   ├── base
  │   │   └── kustomization.yaml
  │   └── overlays
  │       └── template
  │           └── kustomization.yaml
  ├── runway.yml
  └── service-hello-world.k8s
      ├── README.md
      ├── base
      │   ├── configMap.yaml
      │   ├── deployment.yaml
      │   ├── kustomization.yaml
      │   └── service.yaml
      └── overlays
          ├── prod
          │   ├── deployment.yaml
          │   └── kustomization.yaml
          └── template
              ├── kustomization.yaml
              └── map.yaml
