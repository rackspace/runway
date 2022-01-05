#######################
cleanup_s3.purge_bucket
#######################

:Hook Path: ``runway.cfngin.hooks.cleanup_s3.purge_bucket``


Delete objects in a Bucket.
Primarily used as a :attr:`~cfngin.config.pre_destroy` hook before deleting an S3 bucket.


.. versionchanged:: 2.0.0
  Moved from ``runway.hooks`` to ``runway.cfngin.hooks``.



****
Args
****

.. data:: bucket_name
  :type: str
  :noindex:

  Name of the S3 bucket.
