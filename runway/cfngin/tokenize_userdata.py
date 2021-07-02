"""Resources to tokenize userdata."""
import re
from typing import List

from troposphere import GetAtt, Ref

HELPERS = {"Ref": Ref, "Fn::GetAtt": GetAtt}

SPLIT_STRING = "(" + "|".join(fr"{h}\([^)]+\)" for h in HELPERS) + ")"
REPLACE_STRING = fr"(?P<helper>{'|'.join(HELPERS)})\((?P<args>['\"]?[^)]+['\"]?)+\)"

SPLIT_RE = re.compile(SPLIT_STRING)
REPLACE_RE = re.compile(REPLACE_STRING)


def cf_tokenize(raw_userdata: str) -> List[str]:
    """Parse UserData for Cloudformation helper functions.

    http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/user-data.html

    http://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/intrinsic-function-reference.html

    It breaks apart the given string at each recognized function (see
    ``HELPERS`` global variable) and instantiates the helper function objects
    in place of those.

    Args:
        raw_userdata: Unparsed userdata data string.

    Returns:
        A list of string parts that is useful when used with
        :func:`troposphere.Join` and :func:`troposphere.Base64` to produce
        userdata.

    Example:
        .. code-block: python

            Base64(Join('', cf_tokenize(userdata_string)))

    """
    result: List[str] = []
    parts = SPLIT_RE.split(raw_userdata)
    for part in parts:
        cf_func = REPLACE_RE.search(part)
        if cf_func:
            args = [a.strip("'\" ") for a in cf_func.group("args").split(",")]
            result.append(HELPERS[cf_func.group("helper")](*args).data)
        else:
            result.append(part)
    return result
