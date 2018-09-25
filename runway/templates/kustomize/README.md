# Create StorageClasses for AWS

The following example shows a `kustomization.yaml` file that creates four storage classes (gp2, io1, sc1, st1) in kubernetes, than patches the `gp2` storage class to be the default storage class via [JSON patches](https://tools.ietf.org/html/rfc6902).

After you apply this kustomize module, all AWS EBS volume types will be available to pods that request Persistent Volume Claims (PVC). If your deployment spec doesn't include a specific storage class type when requesting a PVC, you will get gp2 by default.

Additional notes:
* Existing storage classes cannot be updated. Any storage class sharing the exact name as defined here must be deleted before deploying the module.
* This module requires version v1.0.8 of kustomize, due to the JSON patch support.
* These storage classes will only create EBS volumes that are encrypted.
