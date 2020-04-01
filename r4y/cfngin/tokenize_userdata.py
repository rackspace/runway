"""Resources to tokenize userdata."""
import re

from troposphere import GetAtt, Ref

HELPERS = {
    "Ref": Ref,
    "Fn::GetAtt": GetAtt
}

SPLIT_STRING = "(" + "|".join([r"%s\([^)]+\)" % h for h in HELPERS]) + ")"
REPLACE_STRING = \
    r"(?P<helper>%s)\((?P<args>['\"]?[^)]+['\"]?)+\)" % '|'.join(HELPERS)

SPLIT_RE = re.compile(SPLIT_STRING)
REPLACE_RE = re.compile(REPLACE_STRING)


def cf_tokenize(raw_userdata):
    """Parse UserData for Cloudformation helper functions.

    http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/user-data.html

    http://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/intrinsic-function-reference.html

    http://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/quickref-cloudformation.html#scenario-userdata-base64

    It breaks apart the given string at each recognized function (see
    ``HELPERS`` global variable) and instantiates the helper function objects
    in place of those.

    Args:
        raw_userdata (str): Unparsed userdata data string.

    Returns:
        List[str]: A list of string parts that is useful when used with
        :func:`troposphere.Join` and :func:`troposphere.Base64` to produce
        userdata.

    Example:
        .. code-block: python

            Base64(Join('', cf_tokenize(userdata_string)))

    """
    result = []
    parts = SPLIT_RE.split(raw_userdata)
    for part in parts:
        cf_func = REPLACE_RE.search(part)
        if cf_func:
            args = [a.strip("'\" ") for a in cf_func.group("args").split(",")]
            result.append(HELPERS[cf_func.group("helper")](*args).data)
        else:
            result.append(part)
    return result
