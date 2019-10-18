.. _mod-k8s:

Kubernetes
==========

Kubernetes manifests can be deployed via Runway, offering an ideal way to
handle core infrastructure-layer (e.g. shared ConfigMaps & Service Accounts)
configuration of clusters. Perform the following steps to align your k8s
directories with Runway's requirements & best practices.


Part 1: Adding Kubernetes to Deployment
---------------------------------------

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


Part 2: Specify the Kubectl Version
-------------------------------------

By specifying the version via a ``.kubectl-version`` file in your overlay
directory, or a module option, Runway will automatically download & use that
version for the module. This is recommended to keep a predictable experience
when deploying your module.

.kubectl-version::

    1.14.5


or in runway.yml, either for a single module::

    ---
    deployments:
      - modules:
          - path: myk8smodule
            options:
              kubectl_version:
                "*": 1.14.5  # applies to all environments
                # prod: 1.13.0  # can also be specified for a specific environment


and/or for a group of modules:
::

    ---
    deployments:
      - modules:
          - path: myk8smodule
          - path: anotherk8smodule
        module_options:  # shared between all modules in deployment
          kubectl_version:
            "*": 1.14.5  # applies to all environments
            # prod: 1.13.0  # can also be specified for a specific environment


Without a version specified, Runway will fallback to whatever ``kubectl``
it finds first in your PATH.


Part 3: Setting KUBECONFIG location
-------------------------------------

If using a non-default kubeconfig location, you can provide it using Runway's
option for setting environment variables. This can be set as a relative path
or an absolute one. E.g.::

    ---
    deployments:
      - modules:
          - path: myk8smodule
            options:
              kubectl_version:
      - regions:
          - us-east-1
    env_vars:
      staging:
        KUBECONFIG:
          - .kube
          - staging
          - config
      prod:
        KUBECONFIG:
          - .kube
          - prod
          - config

(this would set ``KUBECONFIG`` to ``<path_to_runway.yml>/.kube/staging/config``
in the staging environment)
