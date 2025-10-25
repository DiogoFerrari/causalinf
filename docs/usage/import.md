---

hide:

-   toc

---

The `causalinf` module provides implementations, through different
submodules, of many **causal identification strategies**, that is,
(causal) **models** used to recover causal effects in quantitative
analyses. *Experiments* are treated as a particular case of an
identification strategy. The following submodules are available (other
methods may be added in the future):

``` org
1. Experimental Design (ED)          (submodule name: *experiment*)
2. Graphical Causal Models (GCM)     (submodule name: *gcm*)
3. Structural Causal Models (SCM)    (submodule name: *scm*)
4. Causal Bayesian Networks (CBN)    (submodule name: *cbn*)
5. Selection on Observables (SoO)    (submodule name: *soo*)
6. Difference-in-Differences (DiD)   (submodule name: *did*)
7. Regression Discontinuity (RD)     (submodule name: *rd*)
8. Instrumental Variable (IV)        (submodule name: *iv*)
```

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
