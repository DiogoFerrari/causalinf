from pathlib import Path
import pandas as pd
from pandas.api.types import CategoricalDtype

def __categories__(df, cats, ordered=True):
    """Convert objects to categories

    :param df: data
    :type df: pandas DataFrame
    :param cats: keys are the column name and value the categories
    :type cats: {str: list}
    :param ordered: True if categories should be ordered
    :type ordered: boolean

    """
    for col, cats in cats.items():
        df[col] = df[col].astype(CategoricalDtype(cats, ordered=ordered))
    return df


__all__ = (
    "example",
)

data_dir = Path(__file__).parent

cats = {
    "cat": ["c1", 'c2'],
}
example = __categories__(pd.read_csv(data_dir / "example.csv"), cats)
example.__doc__ = f'''
Example dataset

.. rubric:: Description

The data contains information about...

.. rubric:: Format

A data frame with {example.shape[0]} observations on {example.shape[1]} variables.

======  =========================================
Column  Description
======  =========================================
a       Variable a
b       Variable b
cat     Variable with categories
======  =========================================

.. rubric:: Source

Author (year) Paper name
'''


del(cats)
