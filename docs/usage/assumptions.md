---

hide:

-   toc

---

All quantitative causal analyses involve two major groups of
assumptions:

1.  **Causal modeling assumptions**
2.  **Statistical modeling assumptions**

Details about each of them can be found in specialized literature
(Ferrari, [2026](#sec-refs)).

Although some checks for **statistical modeling assumptions** are
provided, the `causalinf` module puts emphasis on the first type of
assumptions (**causal modeling assumptions**). The main reasons is that
the initial step in any causal inference analysis is selecting among
various causal inference models. This selection largely hinges on
assessments regarding the validity of the underlying causal modeling
assumptions in the specific context of application. Typically, users of
causal inference methods know the causal assumptions associated with
each causal modeling approach and then select the method whose
assumptions are plausible in the available data. Hence, the emphasis of
`causalinf` on those assumptions.

Users can find functionalities to test statistical modeling assumptions
in various other existing modules outside `causalinf`. They can be used
directly on the output of the estimation object from `causalinf` (see
[Estimation](../estimation)). However, differently from many statistical
modeling assumptions, the **validity of causal modeling assumptions
cannot be tested using typical statistical test procedures.** Instead,
the judgment about their validity depends on three things:

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
of the assessment of causal modeling assumptions. The main function in
all submodules to get that assessment is `check_assumptions()`. For
instance, to check the causal assumptions for a **DiD** application,
use:

``` {.python exports="code" results="silent" tangle="src-overview.py" cache="yes" noweb="no" session="*Python*" linenums="1" eval="always"}
from causalinf import did

did.check_assumptions(<args>)
```

`<args>` vary across submodules depending on the method used. See
[Methods](../methods/overview) for details in each case.

## References {#sec-refs}

-   Ferrari, D. (2026). The Identification of Causal Effects. Cambridge
    Universty Press.
