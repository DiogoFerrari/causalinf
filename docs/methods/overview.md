---

hide:
-   toc
---

# Overview

Causal inference methods are available as `causalinf` submodules. To
import a submodule, use:

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

The following methods and their respective submodule names are available
(others may become available in the future):

| Method                                                      | Submodule name | Description                                                                                                                                                                                                                                                                                                                                                                       |
|-------------------------------------------------------------|----------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 1\. [Experimental Design (ED)](../experiment/introduction/) | experiment     | Methods to estimate a variety of causal effect parameters for experimental studies: Average Causal Effects (ACE), Average Conditional Causal Effects (ACCE) Average Causal Mediation Effects (ACME), Average Marginal Component Effect (AMCE) among many others. Parametric models are available for all parameters, and non-parametric models are available for some parameters. |
| 2\. [Graphical Causal Models (GCM)](../gcm/introduction/)   | gcm            | Methods to construct, analyze, and visualize Causal Graphical Models (GCM). Tools to access assumptions are provided.                                                                                                                                                                                                                                                             |
| 3\. [Structural Causal Models (SCM)](../scm/introduction/)  | scm            | Methods to estimate causal effects with GCM using Structural Causal Models (SCM). Parametric and non-parametric models are available.                                                                                                                                                                                                                                             |
| 4\. [Causal Bayesian Networks (CBN)](../cbn/introduction/)  | cbn            | Methods to estimate causal effects with GCM using Causal Bayesian Networks (CBN). Parametric and kernel models are available.                                                                                                                                                                                                                                                     |
| 5\. [Selection on Observables (SoO)](../soo/introduction/)  | soo            | Methods to estimate causal effects using Selection on Observables (SoO). Parametric and non-parametric models are available.                                                                                                                                                                                                                                                      |
| 6\. [Difference-in-Differences (DiD)](../did/introduction/) | did            | Methods to estimate causal effects using Difference-in-Differences (DiD). Estimation for many settings is available, including classic 2-groups-2-periods models and staggered DiD. Tools to access assumptions are provided. Parametric and non-parametric models are available.                                                                                                 |
| 7\. [Regression Discontinuity (RD)](../rd/introduction/)    | rd             | Methods to estimate causal effects using Regression Discontinuity (RD). Estimation for many settings is available, including sharp RD, fuzzy RD, and others. Tools to access assumptions are provided. Parametric and non-parametric models are available.                                                                                                                        |
| 8\. [Instrumental Variable (IV)](../iv/introduction/)       | iv             | Methods to estimate causal effects using Instrumental Variables (IV). Estimation for many settings is available, including single or multiple IVs, and others. Tools to access assumptions are provided. Parametric and non-parametric models are available.                                                                                                                      |

See [Case Studies](../case-studies/overview.md) for applied examples.
