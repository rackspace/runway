"""Tests for terraform module."""
from runway.module.terraform import update_env_vars_with_tf_var_values


def test_update_env_vars_with_tf_var_values():
    """Test update_env_vars_with_tf_var_values."""
    result = update_env_vars_with_tf_var_values({}, {'foo': 'bar',
                                                     'list': ['foo', 1, True],
                                                     'map': sorted({  # python 2
                                                         'one': 'two',
                                                         'three': 'four'
                                                     })})
    expected = {
        'TF_VAR_foo': 'bar',
        'TF_VAR_list': '["foo", 1, true]',
        'TF_VAR_map': '{ one = "two", three = "four" }'
    }

    assert sorted(result) == sorted(expected)  # sorted() needed for python 2
