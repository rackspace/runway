#############
Configuration
#############

Configuration options and parameters for :ref:`Kubernetes <mod-k8s>` modules.


*******
Options
*******

**kubectl_version (Optional[str])**
  Specify a version of Kubectl for Runway and download and use.
  See :ref:`Version Management <k8s-version>` for more details.

  .. rubric:: Example
  .. code-block:: yaml

    options:
      kubectl_version: 1.14.5


**********
Parameters
**********

:ref:`Kubernetes <mod-k8s>` does not support the use of parameters at this time.
