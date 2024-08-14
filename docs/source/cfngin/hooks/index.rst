.. _cfngin-hooks:

#####
Hooks
#####

A :class:`~cfngin.hook` is a python function, class, or class method that is executed before or after an action is taken for the entire config.

Only the following actions allow pre/post hooks:

:deploy:
  using fields :attr:`~cfngin.config.pre_deploy` and :attr:`~cfngin.config.post_deploy`
:destroy:
  using fields :attr:`~cfngin.config.pre_destroy` and :attr:`~cfngin.config.post_destroy`

.. class:: cfngin.hook

  When defining a hook in one of the supported fields, the follow fields can be used.

  .. rubric:: Lookup Support

  The following fields support lookups:

  - :attr:`~cfngin.hook.args`

  .. attribute:: args
    :type: Optional[Dict[str, Any]]
    :value: {}

    A dictionary of arguments to pass to the hook.

    This field supports the use of :ref:`lookups <cfngin-lookups>`.

    .. important::
      :ref:`Lookups <cfngin-lookups>` that change the order of execution, like :ref:`output <output lookup>`, can only be used in a *post* hook but hooks like :ref:`rxref <xref lookup>` are able to be used with either *pre* or *post* hooks.

    .. rubric:: Example
    .. code-block:: yaml

      pre_deploy:
        - args:
            key: ${val}

  .. attribute:: data_key
    :type: Optional[str]
    :value: None

    If set, and the hook returns data (a dictionary or ``pydantic.BaseModel``), the results will be stored in :attr:`CfnginContext.hook_data <runway.context.CfnginContext.hook_data>` with the ``data_key`` as its key.

    .. rubric:: Example
    .. code-block:: yaml

      pre_deploy:
        - data_key: example-key

  .. attribute:: enabled
    :type: Optional[bool]
    :value: True

    Whether to execute the hook every CFNgin run.
    This field provides the ability to execute a hook per environment when combined with a variable.

    .. rubric:: Example
    .. code-block:: yaml

      pre_deploy:
        - enabled: ${enable_example_hook}

  .. attribute:: path
    :type: str

    Python importable path to the hook.

    .. rubric:: Example
    .. code-block:: yaml

      pre_deploy:
        - path: runway.cfngin.hooks.command.run_command

  .. attribute:: required
    :type: Optional[bool]
    :value: True

    Whether to stop execution if the hook fails.



----


**************
Built-in Hooks
**************

.. toctree::
  :maxdepth: 1
  :glob:

  **


----



*********************
Writing A Custom Hook
*********************

A custom hook must be in an executable, importable python package or standalone file.
The hook must be importable using your current ``sys.path``.
This takes into account the :attr:`~cfngin.config.sys_path` defined in the :class:`~cfngin.config` file as well as any ``paths`` of :attr:`~cfngin.config.package_sources`.

When executed, the hook will have various keyword arguments passed to it.
The keyword arguments that will always be passed to the hook are ``context`` (:class:`~runway.context.CfnginContext`) and ``provider`` (:class:`~runway.cfngin.providers.aws.default.Provider`).
Anything defined in the :attr:`~cfngin.hook.args` field will also be passed to hook as a keyword argument.
For this reason, it is recommended to use an unpack operator (``**kwargs``) in addition to the keyword arguments the hook requires to ensure future compatibility and account for misconfigurations.

The hook must return ``True`` or a truthy object if it was successful.
It must return ``False`` or a falsy object if it failed.
This signifies to CFNgin whether or not to halt execution if the hook is :attr:`~cfngin.hook.required`.
If a |Dict|, :class:`~runway.utils.MutableMap`, or :class:`pydantic.BaseModel` is returned, it can be accessed by subsequent hooks, lookups, or Blueprints from the context object.
It will be stored as ``context.hook_data[data_key]`` where :attr:`~cfngin.hook.data_key` is the value set in the hook definition.
If :attr:`~cfngin.hook.data_key` is not provided or the type of the returned data is not a |Dict|, :class:`~runway.utils.MutableMap`, or :class:`pydantic.BaseModel`, it will not be added to the context object.

.. important::
  When using a :func:`pydantic.root_validator` or :func:`pydantic.validator` ``allow_reuse=True`` must be passed to the decorator.
  This is because of how hooks are loaded/re-loaded for each usage.
  Failure to do so will result in an error if the hook is used more than once.

If using boto3 in a hook, use :meth:`context.get_session() <runway.context.CfnginContext.get_session>` instead of creating a new session to ensure the correct credentials are used.

.. code-block:: python

  """context.get_session() example."""
  from __future__ import annotations

  from typing import TYPE_CHECKING, Any

  if TYPE_CHECKING:
      from runway.context import CfnginContext


  def do_something(context: CfnginContext, **_kwargs: Any) -> None:
      """Do something."""
      s3_client = context.get_session().client("s3")


Example Hook Function
=====================

.. code-block:: python
  :caption: local_path/hooks/my_hook.py

  """My hook."""
  from typing import Dict, Optional


  def do_something(
      *, is_failure: bool = True, name: str = "Kevin", **_kwargs: str
  ) -> Optional[Dict[str, str]]:
      """Do something."""
      if is_failure:
          return None
      return {"result": f"You are not a failure {name}."}


.. code-block:: yaml
  :caption: local_path/cfngin.yaml

  namespace: example
  sys_path: ./

  pre_deploy:
    - path: hooks.my_hook.do_something
      args:
        is_failure: false


Example Hook Class
==================

Hook classes must implement the interface detailed by the :class:`~runway.cfngin.hooks.protocols.CfnginHookProtocol` |Protocol|.
This can be done implicitly or `explicitly <https://www.python.org/dev/peps/pep-0544/#explicitly-declaring-implementation>`__ (by creating a subclass of :class:`~runway.cfngin.hooks.protocols.CfnginHookProtocol`).

As shown in this example, :class:`~runway.cfngin.hooks.base.HookArgsBaseModel` or it's parent class :class:`~runway.utils.BaseModel` can be used to create self validating and sanitizing data models.
These can then be used to parse the values provided in the :attr:`~cfngin.hook.args` field to ensure they match what is expected.

.. code-block:: python
  :caption: local_path/hooks/my_hook.py

  """My hook."""
  import logging
  from typing import TYPE_CHECKING, Any, Dict, Optional

  from runway.utils import BaseModel
  from runway.cfngin.hooks.protocols import CfnginHookProtocol

  if TYPE_CHECKING:
      from ...context import CfnginContext

  LOGGER = logging.getLogger(__name__)


  class MyClassArgs(BaseModel):
      """Arguments for MyClass hook.

      Attributes:
          is_failure: Force the hook to fail if true.
          name: Name used in the response.

      """

      is_failure: bool = False
      name: str


  class MyClass(CfnginHookProtocol):
      """My class does a thing.

      Keyword Args:
          is_failure (bool): Force the hook to fail if true.
          name (str): Name used in the response.

      Returns:
          Dict[str, str]: Response message is stored in ``result``.

      Example:
      .. code-block:: yaml

          pre_deploy:
            - path: hooks.my_hook.MyClass
              args:
              is_failure: False
              name: Karen

      """

      args: MyClassArgs

      def __init__(self, context: CfnginContext, **kwargs: Any) -> None:
          """Instantiate class.

          Args:
              context: Context instance. (passed in by CFNgin)
              provider: Provider instance. (passed in by CFNgin)

          """
          kwargs.setdefault("tags", {})

          self.args = self.ARGS_PARSER.parse_obj(kwargs)
          self.args.tags.update(context.tags)
          self.context = context

      def post_deploy(self) -> Optional[Dict[str, str]]:
          """Run during the **post_deploy** stage."""
          if self.args["is_failure"]:
              return None
          return {"result": f"You are not a failure {self.args['name']}."}

      def post_destroy(self) -> None:
          """Run during the **post_destroy** stage."""
          LOGGER.error("post_destroy is not supported by this hook")

      def pre_deploy(self) -> None:
          """Run during the **pre_deploy** stage."""
          LOGGER.error("pre_deploy is not supported by this hook")

      def pre_destroy(self) -> None:
          """Run during the **pre_destroy** stage."""
          LOGGER.error("pre_destroy is not supported by this hook")


.. code-block:: yaml
  :caption: local_path/cfngin.yaml

  namespace: example
  sys_path: ./

  pre_deploy:
    - path: hooks.my_hook.MyClass
      args:
        is_failure: False
        name: Karen
