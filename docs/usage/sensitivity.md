---

hide:

-   toc

---

The function `<submodule>.estimate(<args>)` can be used in all
submodules to run the estimation and collect inference statistics
(p-value, z-scores, etc.). For instance, to estimate a **DiD** model,
use:

``` {.python exports="code" results="silent" tangle="src-overview.py" cache="yes" noweb="no" session="*Python*" linenums="1" eval="always"}
from causalinf import did

mod = did.estimate(<args>, data=<DataFrame>)
```

`<args>` vary across submodules depending on the method used.

Sensitivity analysis\* is important because it provides information on
how the conclusions of a causal inference study would change if one or
more causal assumptions were violated in specific ways.

The core method across submodules of `causalinf` to run sensitivity
analysis is `sensitivity_analysis(<args>)`. For instance, if one is
using *Selection on Observables* (**SoO**), sensitivity analysis can be
conducted as follows:

``` {.python exports="code" results="silent" tangle="src-overview.py" cache="yes" noweb="no" session="*Python*" linenums="1" eval="always"}
from causalinf import soo

sens = soo.sensitivity_analysis(<args>)
```

`<args>` vary across submodules depending on the method used.
