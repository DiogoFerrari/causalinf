---

hide:

-   toc

---

The `causalinf` module provides the implementation of many causal
inference methods. Each method is available as a `causalinf` submodule.
To import a submodule, use:

``` {.python exports="code" results="silent" tangle="src-overview.py" cache="yes" noweb="no" session="*Python*" linenums="1" eval="never"}
from causalinf import <submodule name>
```

Here are some examples:

``` {.python exports="code" results="silent" tangle="src-overview.py" cache="yes" noweb="no" session="*Python*" linenums="1" eval="never"}
from causalinf import did # (1)!
from causalinf import gcm # (2)!
from causalinf import iv  # (3)!
```

1.  Load the Difference-in-Differences (DiD) module
2.  Load the Causal Graphical Models (GCM) module
3.  Load the Instrumental Variable (IV) module

See [Methods](../methods/overview.md) for details of the submodules
(i.e., methods) available.
