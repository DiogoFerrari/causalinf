---

hide:

-   toc

---

**Sensitivity analysis** is a procedure to evaluate how the conclusions
of causal inference estimation would change if one or more of the
**causal assumptions** (see [Assumptions](./assumptions.md)) were
violated in specific ways. **Sensitivity analysis** is available for
some assumptions of some causal inference methods. Check the
[Methods](../methods/gcm/introduction.md) page to see which options are
available for each method.

The core function across submodules of `causalinf` to run sensitivity
analysis is `sensitivity_analysis(<args>)`. For instance, if one is
using *Selection on Observables* (*SoO*), sensitivity analysis can be
conducted as follows:

``` {.python exports="code" results="silent" tangle="src-overview.py" cache="yes" noweb="no" session="*Python*" linenums="1" eval="always"}
from causalinf import soo

sens = soo.sensitivity_analysis(<args>)
```

`<args>` vary across submodules depending on the method used.
