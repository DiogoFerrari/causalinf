## Basic Usage Structure

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

The code syntax of the core functions in `causalinf` is standardized
across methods, which means that the same code pattern can be used to
import a module, check model assumptions, estimate causal effects,
conduct sensitivity analysis, and report results. These core functions
are:

| Task                              | Basic function                       |
|-----------------------------------|--------------------------------------|
| Check causal modeling assumptions | `<submodule>.check_assumptions()`    |
| Estimate causal model             | `<submodule>.estimate()`             |
| Run sensitivity analysis          | `<submodule>.sensitivity_analysis()` |
| Summarize the results             | `<submodule>.summary()`              |

Many other method-specific features are provided. For details on the
implementation of each method, check the method-specific sections.

For brief details of these basic functions, see [Details](#sec-details).

For comprehensive applied examples, see [Case
Studies](../../case-studies/overview).

## Details {#sec-details}

### Causal Model Assumptions

All quantitative causal analyses involve two major groups of
assumptions:

1.  **Causal modeling assumptions**
2.  **Statistical modeling assumptions**

Details about each of them can be found in specialized literature
(Ferrari, [2026](#sec-refs)).

Although some checks for statistical modeling assumptions are provided,
the `causalinf` module puts emphasis on the first type of assumptions
(**causal modeling assumptions**). The reason is that the first step of
any causal inference analysis is the choice between different causal
inference models. This choice ultimately depends on judgments about
whether those assumptions hold in the intended application. Typically,
users of causal inference methods know the causal assumptions each
method requires and then select the method whose assumptions are
satisfied in the available data. Hence, the emphasis of `causalinf` on
those assumptions.

Differently from many statistical modeling assumptions, the **validity
of causal modeling assumptions cannot be tested using typical
statistical test procedures.** Instead, the judgment about their
validity depends on three things:

1.  *Methodological expertise*, which refers to the understanding of
    what the assumptions mean (and do not mean) in terms of the
    relations between the elements (variables) *used* and *omitted* in
    the model. The literature on causal inference methods provides
    guidance in this regard. Ferrari ([2026](#sec-refs)) is the
    reference text used for the `causalinf` implementation.
2.  *Domain knowledge expertise*, which refers to the understanding of
    how the data was generated and whether the assumptions hold for the
    particular intended application.
3.  *Heuristic or suggestive evidence* based on data. That is, for some
    assumptions of specific methods, procedures exist to evaluate
    whether the causal modeling assumptions seem plausible given the
    data.

Whenever possible, the `causalinf` module facilitates that third aspect
of the assessment of causal modeling assumptions. The main method in all
submodules to get that assessment is `check_assumptions()`. For
instance, to check the causal assumptions for a **DiD** application,
use:

``` {.python exports="code" results="silent" tangle="src-overview.py" cache="yes" noweb="no" session="*Python*" linenums="1" eval="always"}
from causalinf import did

did.check_assumptions(<args>)
```

`<args>` vary across submodules depending on the method used.

### Estimation and Inference

The function `<submodule>.estimate(<args>)` can be used in all
submodules to run the estimation and collect inference statistics
(p-value, z-scores, etc.). For instance, to estimate a **DiD** model,
use:

``` {.python exports="code" results="silent" tangle="src-overview.py" cache="yes" noweb="no" session="*Python*" linenums="1" eval="always"}
from causalinf import did

mod = did.estimate(<args>, data=<DataFrame>)
```

`<args>` vary across submodules depending on the method used.

### Sensitivity Analysis

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

### Summary and Reporting

The module `causalinf` provides many functionalities to summarize and
report the results of the assessment of the assumptions, estimation,
inference, and sensitivity analysis.

Results can be exported and saved in `LaTeX`, text, or tabular format
(.csv, .xlsx, etc.).

The method `summary()` is used across methods. Here is an example using
**DiD** to produce a LaTeX table with the estimation results (check
[Case Studies](../../case-studies/overview) for comprehensive examples).

``` {.python exports="code" results="silent" tangle="src-overview.py" cache="yes" noweb="no" session="*Python*" linenums="1" eval="always"}
from causalinf import did

mod = did.estimate(<args>, data=<DataFrame>)
mod.summary(<args>, output="latex")
```

`<args>` vary across submodules depending on the method used.

## References {#sec-refs}

-   Ferrari, D. (2026). The Identification of Causal Effects. Cambridge
    Universty Press.
