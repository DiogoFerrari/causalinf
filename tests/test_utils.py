import pandas as pd
import polars as pl
import tidypolars4sci as tp

from causalinf.utils import detect_variable_type


def test_detect_variable_type_defaults_to_all_columns():
    data = tp.tibble(
        {
            "continuous": [1.0, 2.0, 3.0],
            "binary": [0, 1, 0],
            "categorical": ["a", "b", "c"],
        }
    )

    assert detect_variable_type(data) == {
        "continuous": "continuous",
        "binary": "binary",
        "categorical": "categorical",
    }


def test_detect_variable_type_accepts_common_dataframe_inputs():
    expected = {"x": "binary"}

    assert detect_variable_type(pd.DataFrame({"x": [0, 1, 0]}), variables="x") == expected
    assert detect_variable_type(pl.DataFrame({"x": [0, 1, 0]}), variables="x") == expected
