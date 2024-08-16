"""Inverse of :class:`~pydantic.types.StrictStr`."""

from __future__ import annotations

from decimal import Decimal

from pydantic.functional_validators import BeforeValidator


def _handler(value: object | None) -> object | None:
    """Convert the provided value if able."""
    if isinstance(value, (float, int, Decimal)):
        return str(value)
    return value


LaxStr = BeforeValidator(_handler)
"""Custom :class:`~pydantic.functional_validators.BeforeValidator`.

Inverse of :class:`~pydantic.types.StrictStr` that allows additional types to be
accepted as a :class:`str`.

.. rubric:: Example
.. code-block:: python

    from __future__ import annotations

    from typing import Annotated

    from runway.utils import LaxStr

    class MyModel(BaseModel):
        some_field: Annotated[str, LaxStr]
        some_other_field: Annotated[str | None, LaxStr] = None

"""
