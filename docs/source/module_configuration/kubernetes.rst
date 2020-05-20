Kubernetes
==========


Part 1: Adding Kubernetes to Deployment
---------------------------------------

.. I think i was able to translate everything over to the new structure pretty well except for maybe this section.
.. Does anything in this section need to be covered more in one of the new sections?

Start by adding your
`Kustomize overlay organized <https://kubernetes.io/docs/tasks/manage-kubernetes-objects/kustomization/#bases-and-overlays>`_
Kubernetes directory to your runway.yml's list of modules.

Directory tree:
::

    .
    ├── runway.yml
    └── kubernetesstuff.k8s
        ├── base
        │   ├── kustomization.yaml
        │   └── service.yaml
        └── overlays
            ├── prod
            │   └── kustomization.yaml
            └── staging
                └── kustomization.yaml


runway.yml:
::

    ---
    deployments:
      - modules:
          - kubernetesstuff.k8s
        regions:
          - us-east-1

Each overlay's kustomization can be as simple as including the base directory
and (optionally) adding a resource prefix. E.g., in the staging directory's
kustomize.yml::

    bases:
      - ../base
    namePrefix: staging-

The base directory's kustomization then in turn includes the base directory's
manifests::

    resources:
      - service.yaml
