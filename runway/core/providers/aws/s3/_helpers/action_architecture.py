"""Action architecture.

.. Derived from software distributed by Amazon.com, Inc - http://aws.amazon.com/apache2.0/
   https://github.com/aws/aws-cli/blob/83b43782dd/awscli/customizations/s3/subcommands.py

"""
from __future__ import annotations

import logging
from queue import Queue
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from typing_extensions import Literal, TypedDict

from ......compat import cached_property
from .comparator import Comparator
from .file_generator import FileGenerator
from .file_info_builder import FileInfoBuilder
from .filters import Filter
from .format_path import FormatPath
from .s3handler import S3TransferHandlerFactory
from .sync_strategy.base import MissingFileSync, NeverSync, SizeAndLastModifiedSync
from .transfer_config import RuntimeConfig

if TYPE_CHECKING:
    import boto3
    from botocore.session import Session
    from mypy_boto3_s3.client import S3Client

    from .format_path import FormatPathResult
    from .parameters import ParametersDataModel
    from .s3handler import S3TransferHandler
    from .sync_strategy.base import BaseSync
    from .transfer_config import TransferConfigDict

LOGGER = logging.getLogger(__name__.replace("._", "."))


_InstructionTypeDef = Literal[
    "comparator",
    "file_generator",
    "file_info_builder",
    "filters",
    "s3_handler",
    "setup",
]


class _CommandDictTypeDef(TypedDict):
    """Type definition for command_dict."""

    comparator: List[Comparator]
    file_generator: List[FileGenerator]
    file_info_builder: List[FileInfoBuilder]
    filters: List[Any]
    s3_handler: List[S3TransferHandler]
    setup: List[FormatPathResult]


class ActionArchitecture:
    """Drives the action.

    An action is performed in two steps. First a list of instructions is generated.
    This list of instructions identifies which type of components are required
    based on the name of the command and the parameters passed to the command line.
    After the instructions are generated the second step involves using the
    list of instructions to wire together an assortment of generators to
    perform the command.

    """

    def __init__(
        self,
        session: boto3.Session,
        botocore_session: Session,
        action: Literal["sync"],
        parameters: ParametersDataModel,
        runtime_config: Optional[TransferConfigDict] = None,
    ) -> None:
        """Instantiate class."""
        self.botocore_session = botocore_session
        self.session = session
        self.action = action
        self.parameters = parameters
        self._runtime_config = runtime_config or RuntimeConfig.defaults()
        self._source_client = None

    @cached_property
    def client(self) -> S3Client:
        """Boto3 S3 client."""
        return self.session.client("s3")

    @cached_property
    def instructions(self) -> List[_InstructionTypeDef]:
        """Create the instructions based on the command name and parameters.

        Note that all commands must have an s3_handler instruction in the
        instructions and must be at the end of the instruction list because it
        sends the request to S3 and does not yield anything.

        """
        result: List[_InstructionTypeDef] = ["file_generator"]
        if self.parameters.exclude or self.parameters.include:
            result.append("filters")
        if self.action == "sync":
            result.append("comparator")
        result.append("file_info_builder")
        result.append("s3_handler")
        return result

    def choose_sync_strategies(self) -> Dict[str, BaseSync]:
        """Determine the sync strategy for the command.

        It defaults to the default sync strategies but a customizable sync
        strategy can override the default strategy if it returns the instance
        of its self when the event is emitted.

        """
        sync_strategies: Dict[str, BaseSync] = {
            "file_at_src_and_dest_sync_strategy": SizeAndLastModifiedSync(),
            "file_not_at_dest_sync_strategy": MissingFileSync(),
            "file_not_at_src_sync_strategy": NeverSync(),
        }

        # Determine what strategies to override if any.
        responses: Optional[List[Tuple[Any, BaseSync]]] = self.botocore_session.emit(
            "choosing-s3-sync-strategy", params=self.parameters
        )
        if responses is not None:
            for response in responses:
                override_sync_strategy = response[1]
                if override_sync_strategy is not None:
                    sync_type = override_sync_strategy.sync_type
                    sync_type += "_sync_strategy"
                    sync_strategies[sync_type] = override_sync_strategy

        return sync_strategies

    def run(self):
        """Wire together all of the generators and completes the action.

        First a dictionary is created that is indexed first by
        the action name. Then using the instruction, another dictionary
        can be indexed to obtain the objects corresponding to the
        particular instruction for that action. To begin the wiring,
        either a ``FileFormat`` or ``TaskInfo`` object, depending on the
        action, is put into a list. Then the function enters a while loop
        that pops off an instruction. It then determines the object needed
        and calls the call function of the object using the list as the input.
        Depending on the number of objects in the input list and the number
        of components in the list corresponding to the instruction, the call
        method of the component can be called two different ways. If the
        number of inputs is equal to the number of components a 1:1 mapping of
        inputs to components is used when calling the call function. If the
        there are more inputs than components, then a 2:1 mapping of inputs to
        components is used where the component call method takes two inputs
        instead of one. Whatever files are yielded from the call function
        is appended to a list and used as the input for the next repetition
        of the while loop until there are no more instructions.

        """
        paths_type = self.parameters.paths_type
        files = FormatPath.format(self.parameters.src, self.parameters.dest)
        rev_files = FormatPath.format(self.parameters.dest, self.parameters.src)

        action_translation = {
            "locals3": "upload",
            "s3s3": "copy",
            "s3local": "download",
            "s3": "delete",
        }
        result_queue: "Queue[Any]" = Queue()
        operation_name = action_translation[paths_type]

        file_generator = FileGenerator(
            client=self.client,
            operation_name=operation_name,
            follow_symlinks=self.parameters.follow_symlinks,
            page_size=self.parameters.page_size,
            result_queue=result_queue,
            request_parameters=self._get_file_generator_request_parameters_skeleton(),
        )
        rev_generator = FileGenerator(
            client=self.client,
            operation_name="",
            follow_symlinks=self.parameters.follow_symlinks,
            page_size=self.parameters.page_size,
            result_queue=result_queue,
            request_parameters=self._get_file_generator_request_parameters_skeleton(),
        )
        file_info_builder = FileInfoBuilder(
            client=self.client, parameters=self.parameters
        )
        s3_transfer_handler = S3TransferHandlerFactory(
            config_params=self.parameters, runtime_config=self._runtime_config
        )(self.client, result_queue)

        sync_strategies = self.choose_sync_strategies()

        command_dict: _CommandDictTypeDef
        if self.action == "sync":
            command_dict = {
                "setup": [files, rev_files],
                "file_generator": [file_generator, rev_generator],
                "filters": [
                    Filter.parse_params(self.parameters),
                    Filter.parse_params(self.parameters),
                ],
                "comparator": [Comparator(**sync_strategies)],
                "file_info_builder": [file_info_builder],
                "s3_handler": [s3_transfer_handler],
            }
        else:
            raise NotImplementedError("only sync is supported")

        files = command_dict["setup"]
        while self.instructions:
            instruction = self.instructions.pop(0)
            file_list = []
            components = command_dict[instruction]
            for index, comp in enumerate(components):
                if len(files) > len(components):
                    file_list.append(comp.call(*files))  # type: ignore
                else:
                    file_list.append(comp.call(files[index]))  # type: ignore
            files = file_list
        # This is kinda quirky, but each call through the instructions
        # will replaces the files attr with the return value of the
        # file_list.  The very last call is a single list of
        # [s3_handler], and the s3_handler returns the number of
        # tasks failed and the number of tasks warned.
        # This means that files[0] now contains a namedtuple with
        # the number of failed tasks and the number of warned tasks.
        # In terms of the RC, we're keeping it simple and saying
        # that > 0 failed tasks will give a 1 RC and > 0 warned
        # tasks will give a 2 RC.  Otherwise a RC of zero is returned.
        return_code: int = 0
        if files[0].num_tasks_failed > 0:  # type: ignore
            return_code = 1
        elif files[0].num_tasks_warned > 0:  # type: ignore
            return_code = 2
        return return_code

    @staticmethod
    def _get_file_generator_request_parameters_skeleton() -> Dict[str, Dict[str, Any]]:
        return {"HeadObject": {}, "ListObjects": {}, "ListObjectsV2": {}}
