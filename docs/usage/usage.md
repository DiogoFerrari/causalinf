## Basic usage

causalinf provides submodules based on the identification strategy
required by the problem. For instance, for DiD estimation, one can use:

``` {.python exports="both" results="output code" tangle="usage.py" cache="yes" noweb="no" session="*Python-Org*"}
from causalinf import did
from causalinf.data import minimum_wage as df

```

``` python
```
