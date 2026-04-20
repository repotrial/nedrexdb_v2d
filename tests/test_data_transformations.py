import pytest
import numpy as np
import pandas as pd
from nedrexdb.db.mongo_to_neo import flatten, determine_series_type

def test_flatten():
    nested = {
        "a": 1,
        "b": {
            "c": 2,
            "d": {
                "e": 3
            }
        },
        "f": [1, 2, 3]
    }
    expected = {
        "a": 1,
        "b.c": 2,
        "b.d.e": 3,
        "f": [1, 2, 3]
    }
    assert flatten(nested) == expected

def test_determine_series_type_simple():
    s = pd.Series([1, 2, 3, np.nan])
    assert determine_series_type(s) == "double" # numpy int types might be seen as float/double if nan is present

    s2 = pd.Series(["a", "b", "c"])
    assert determine_series_type(s2) == "string"

    s3 = pd.Series([True, False, True])
    assert determine_series_type(s3) == "boolean"

def test_determine_series_type_lists():
    s = pd.Series([[1, 2], [3, 4], []])
    assert determine_series_type(s) == "int[]" # lists of ints without NaNs are ints

    s2 = pd.Series([["a", "b"], ["c"], []])
    assert determine_series_type(s2) == "string[]"

def test_determine_series_type_mixed():
    s = pd.Series([1, "a"])
    assert determine_series_type(s) == False

def test_determine_series_type_empty():
    s = pd.Series([np.nan, np.nan])
    # The code says if len(s) == 1 return s.pop() else False.
    # If all items are skipped, s (set) will be empty.
    # Actually if s is empty, it returns False because len(s) != 1.
    assert determine_series_type(s) == False
