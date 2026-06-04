## Overview

**Identification analysis** answers whether a causal parameter can be
written as a function of the observed data distribution, given a
Graphical Causal Model (GCM) and its assumptions. In `causalinf`,
identification analysis is conducted with the method
[identification~analysis~()](../../..//reference/gcm/DAG/) of a
`gcm.DAG` object.

The analysis is conditional on the graph and on the assumptions
discussed in [Check Assumptions](../assumptions). It does not determine
whether the graph is true. Instead, it answers a conditional question:
*if* the GCM is a defensible representation of the data-generating
process, which causal effects are identified and by which strategy?

The current GCM identification analysis checks the following strategies:

| Strategy | Abbreviation | What it searches for |
|----|----|----|
| Selection on Observables | SoO | Adjustment sets for total and controlled direct effects. |
| Instrumental Variable | IV | Instruments, and any required adjustment variables, for the average causal effect. |
| do-calculus | do | A causal probability expression for the average causal effect. |

The main causal parameters are:

| Parameter | Meaning                                      |
|-----------|----------------------------------------------|
| ACE       | Average Causal Effect                        |
| ACDE      | Average Controlled Direct Effect             |
| cACE      | Conditional Average Causal Effect            |
| cACDE     | Conditional Average Controlled Direct Effect |

## Basic analysis

Consider the front-door example included with the package:

``` {.python exports="both" results="output code" tangle="src-identification.py" cache="yes" noweb="no" session="*Python*" linenums="1"}
from causalinf import gcm
from causalinf import options as opt

opt.set_options(print_assumptions=False, print_assumptions_verbose=False)

G = gcm.examples("Front-door")
print(G)
```

``` python
Graph:
U -> Y
Z -> Y
Z2 -> D
D -> Z
U -> D
Z2 -> Y
Observed: Z, Z2
Exposure: D
Outcome: Y
Latent: U
```

The method `identification_analysis()` runs the identification search.
If `verbose=True` (the default), the result is printed.

``` {.python exports="both" results="output code" tangle="src-identification.py" cache="yes" noweb="no" session="*Python*" linenums="1"}
G.identification_analysis()
```

``` python
Searching for identification by adjustment variables for ACE...done!
Searching for identification by adjustment variables for ACDE...done!
Searching for identification by instrumental variables...done!
Searching for identification by do-calculus...done!

Exposure: D
Outcome: Y        


Average Causal Effect (ACE)
---------------------            
Method: Selection on Observables (SoO)
Identified: False
Not identifiable by adjustment.

Method: do-calculus (do)
Identified: True
Causal probability: p(Y | do(D)) = sum_{Z,Z2} p(Z|D)sum_{D} p(D,Z2)p(Y|Z,D,Z2)

Method: Instrumental Variable (IV)
Identified: False
No instrument available in the DAG.                

Average Controlled Direct Effect (ACDE)
--------------------------------            
Method: Selection on Observables (SoO)
Identified: False
Not identifiable by adjustment.
```

The output reports the exposure, outcome, causal parameters,
identification strategies, and whether each strategy identifies the
parameter.

## Concise output

After running `identification_analysis()`, the result is stored in the
GCM object. Use `G.identification()` or `G.print(what="identification")`
to print the stored result again.

``` {.python exports="both" results="output code" tangle="src-identification.py" cache="yes" noweb="no" session="*Python*" linenums="1"}
G.identification(print="concise")
```

``` python

Exposure: D
Outcome: Y        

==============================================================================
                                              Identified?
Causal Effects*                           SoO  IV   do-calculus 
==============================================================================
Averave Causal Effect (ACE)              No    No        Yes
Averave Controlled Direct Effect (ACDE)  No    NA/NC**    NA/NC**
==============================================================================
Notes:
*  For path effects (indirect effects), use SEM estimation
** NA/NC: Identification analysis not available or not conducted
```

The concise output is useful for quickly checking which causal
parameters are identified by each strategy.

## Detailed output

For more information about a specific strategy and parameter, use
`content="detailed"` through `G.print()`. The argument `strategy`
selects the identification strategy, and `parameter` selects the causal
parameter.

``` {.python exports="both" results="output code" tangle="src-identification.py" cache="yes" noweb="no" session="*Python*" linenums="1"}
G.print(
    what="identification",
    identification={
        "content": "detailed",
        "strategy": "do",
        "parameter": "ACE",
    },
)
```

``` python

Exposure: D
Outcome: Y        

Identification method: do
---------------------            
Parameter: Average Causal Effect (ACE)
  tau_{ACE}(d, d') = E[Yi(d) - Yi(d')]
Identification:
  p(Y | do(D)) = sum_{Z,Z2} p(Z|D)sum_{D} p(D,Z2)p(Y|Z,D,Z2)
Details:
  tau_{ACE}(d, d') = E[Yi | do(Di)=d] - E[Yi | do(Di)=d']
  where
   Yi: Outcome (Y)
   Di: Exposure or treatment (D)
Models:
  Non-parametric: p(Y | do(D)) = sum_{Z,Z2} p(Z|D)sum_{D} p(D,Z2)p(Y|Z,D,Z2)
```

When the effect is identified by do-calculus, the detailed output
includes the causal probability expression. When the effect is
identified by adjustment or by an instrumental variable strategy, the
detailed output includes the corresponding adjustment, formula, and
parameter information.

## Programmatic results

The printed output is convenient for reports, but the identification
results can also be retrieved as Python objects.

The full result is available in `G.identification_dict`.

``` {.python exports="both" results="output code" tangle="src-identification.py" cache="yes" noweb="no" session="*Python*" linenums="1"}
from pprint import pprint

pprint(G.identification_dict)
```

``` python
{'IV': {'ACE': {'adjusted': False,
                'conditional on': None,
                'conducted': True,
                'exposure': ['D'],
                'formulas': {'non-parametric': '', 'parametric': ''},
                'identified': False,
                'latex': {'Non-parametric': '',
                          'Parametric tau': '',
                          'Parametric(*)': '\n'
                                           '(*) Under linearity and no '
                                           'interaction'},
                'outcome': 'Y',
                'result': {},
                'result str': 'No instrument available in the DAG.',
                'text': {'Non-parametric': '',
                         'Parametric tau': '',
                         'Parametric(*)': '\n'
                                          '(*) Under linearity and no '
                                          'interaction'},
                'variables': None,
                'where': ''}},
 'SoO': {'ACDE': {'adjusted': False,
                  'conditional on': None,
                  'conducted': True,
                  'exposure': ['D'],
                  'formulas': {'non-parametric': '', 'parametric': ''},
                  'identified': False,
                  'latex': {'Non-parametric': '',
                            'Parametric tau': '',
                            'Parametric(*)': '\n'
                                             '(*) Under linearity and no '
                                             'interaction'},
                  'outcome': 'Y',
                  'result': None,
                  'result str': 'Not identifiable by adjustment.',
                  'text': {'Non-parametric': '',
                           'Parametric tau': '',
                           'Parametric(*)': '\n'
                                            '(*) Under linearity and no '
                                            'interaction'},
                  'variables': None,
                  'where': ''},
         'ACE': {'adjusted': False,
                 'conditional on': None,
                 'conducted': True,
                 'exposure': ['D'],
                 'formulas': {'non-parametric': '', 'parametric': ''},
                 'identified': False,
                 'latex': {'Non-parametric': '',
                           'Parametric tau': '',
                           'Parametric(*)': '\n'
                                            '(*) Under linearity and no '
                                            'interaction'},
                 'outcome': 'Y',
                 'result': None,
                 'result str': 'Not identifiable by adjustment.',
                 'text': {'Non-parametric': '',
                          'Parametric tau': '',
                          'Parametric(*)': '\n'
                                           '(*) Under linearity and no '
                                           'interaction'},
                 'variables': None,
                 'where': ''}},
 'do': {'ACE': {'adjusted': False,
                'conditional on': None,
                'conducted': True,
                'exposure': ['D'],
                'formulas': {'non-parametric': 'p(Y | do(D)) = sum_{Z,Z2} '
                                               'p(Z|D)sum_{D} '
                                               'p(D,Z2)p(Y|Z,D,Z2)',
                             'parametric': 'p(Y | do(D)) = sum_{Z,Z2} '
                                           'p(Z|D)sum_{D} p(D,Z2)p(Y|Z,D,Z2)'},
                'identified': True,
                'latex': {'Non-parametric': '$p(Y | do(D)) = '
                                            '\\sum_{Z,Z2}\\left(p(Z|D)\\sum_{D}\\left(p(D,Z2)p(Y|Z,D,Z2)\\right)\\right)$',
                          'Parametric tau': '',
                          'Parametric(*)': '$p(Y | do(D)) = '
                                           '\\sum_{Z,Z2}\\left(p(Z|D)\\sum_{D}\\left(p(D,Z2)p(Y|Z,D,Z2)\\right)\\right)$'},
                'outcome': 'Y',
                'result': 'p(Y | do(D)) = sum_{Z,Z2} p(Z|D)sum_{D} '
                          'p(D,Z2)p(Y|Z,D,Z2)',
                'result str': 'Causal probability: p(Y | do(D)) = sum_{Z,Z2} '
                              'p(Z|D)sum_{D} p(D,Z2)p(Y|Z,D,Z2)',
                'text': {'Non-parametric': 'p(Y | do(D)) = sum_{Z,Z2} '
                                           'p(Z|D)sum_{D} p(D,Z2)p(Y|Z,D,Z2)',
                         'Parametric tau': '',
                         'Parametric(*)': 'p(Y | do(D)) = sum_{Z,Z2} '
                                          'p(Z|D)sum_{D} p(D,Z2)p(Y|Z,D,Z2)'},
                'variables': {'Di': ['D'], 'Yi': 'Y'},
                'where': 'where\n'
                         '  Yi: Outcome (Y)\n'
                         '  Di: Exposure or treatment (D)'}}}
```

To retrieve only the strategies that identify each parameter, use
`G.get_identified()`.

``` {.python exports="both" results="output code" tangle="src-identification.py" cache="yes" noweb="no" session="*Python*" linenums="1"}
pprint(G.get_identified())
```

``` python
{'ACE': ['do']}
```

Use `by="strategy"` to group the result by identification strategy
instead of by causal parameter.

``` {.python exports="both" results="output code" tangle="src-identification.py" cache="yes" noweb="no" session="*Python*" linenums="1"}
pprint(G.get_identified(by="strategy"))
```

``` python
{'do': ['ACE']}
```

By default, `get_identified()` omits strategies that do not identify a
parameter. Use `include_all=True` when the non-identifying strategies
should also be shown.

``` {.python exports="both" results="output code" tangle="src-identification.py" cache="yes" noweb="no" session="*Python*" linenums="1"}
pprint(G.get_identified(include_all=True))
```

``` python
{'ACDE': ['SoO'], 'ACE': ['SoO', 'do', 'IV']}
```

## Identification by adjustment

For graphs in which adjustment is sufficient,
`identification_analysis()` reports the valid adjustment set for the ACE
and ACDE.

``` {.python exports="both" results="output code" tangle="src-identification.py" cache="yes" noweb="no" session="*Python*" linenums="1"}
G_adj = gcm.examples("Two confounders")
G_adj.identification_analysis()
```

``` python
Searching for identification by adjustment variables for ACE...done!
Searching for identification by adjustment variables for ACDE...done!
Searching for identification by instrumental variables skipped.
Searching for identification by do-calculus skipped.

Exposure: D
Outcome: Y        


Average Causal Effect (ACE)
---------------------            
Method: Selection on Observables (SoO)
Identified: True
Adjustments: {Z1, Z2}

Method: do-calculus (do)
Identified: False
Not conducted. Identification by adjustment or instrumental variable available.

Method: Instrumental Variable (IV)
Identified: False
Not conducted. Identification by adjustment available.                

Average Controlled Direct Effect (ACDE)
--------------------------------            
Method: Selection on Observables (SoO)
Identified: True
Adjustments: {Z1, Z2}
```

If identification by adjustment succeeds, instrumental-variable and
do-calculus searches are skipped by default when they are not needed. To
force these searches, use `iv="always"` and
`causal_probability="always"`.

``` {.python exports="both" results="output code" tangle="src-identification.py" cache="yes" noweb="no" session="*Python*" linenums="1"}
G_adj.identification_analysis(iv="always", causal_probability="always")
```

``` python
Searching for identification by adjustment variables for ACE...done!
Searching for identification by adjustment variables for ACDE...done!
Searching for identification by instrumental variables...done!
Searching for identification by do-calculus...done!

Exposure: D
Outcome: Y        


Average Causal Effect (ACE)
---------------------            
Method: Selection on Observables (SoO)
Identified: True
Adjustments: {Z1, Z2}

Method: do-calculus (do)
Identified: True
Causal probability: p(Y | do(D)) = sum_{Z1,Z2} p(Z1,Z2)p(Y|D,Z1,Z2)

Method: Instrumental Variable (IV)
Identified: False
No instrument available in the DAG.                

Average Controlled Direct Effect (ACDE)
--------------------------------            
Method: Selection on Observables (SoO)
Identified: True
Adjustments: {Z1, Z2}
```

## Identification by instrumental variables

Instrumental-variable identification is searched for the ACE. It is
especially useful when the exposure and outcome are confounded but the
graph contains a valid instrument.

``` {.python exports="both" results="output code" tangle="src-identification.py" cache="yes" noweb="no" session="*Python*" linenums="1"}
G_iv = gcm.examples("IV with 1 instrument")
G_iv.identification_analysis()
```

``` python
Searching for identification by adjustment variables for ACE...done!
Searching for identification by adjustment variables for ACDE...done!
Searching for identification by instrumental variables...done!
Searching for identification by do-calculus skipped.

Exposure: X
Outcome: Y        


Average Causal Effect (ACE)
---------------------            
Method: Selection on Observables (SoO)
Identified: False
Not identifiable by adjustment.

Method: do-calculus (do)
Identified: False
Not conducted. Identification by adjustment or instrumental variable available.

Method: Instrumental Variable (IV)
Identified: True
Instrument: Z                 

Average Controlled Direct Effect (ACDE)
--------------------------------            
Method: Selection on Observables (SoO)
Identified: False
Not identifiable by adjustment.
```

The IV output reports whether an instrument is available in the DAG. In
examples with multiple instruments, the result can include instruments
that require adjustment.

``` {.python exports="both" results="output code" tangle="src-identification.py" cache="yes" noweb="no" session="*Python*" linenums="1"}
G_iv_multi = gcm.examples("IV with 3 instruments")
G_iv_multi.identification_analysis()
```

``` python
Searching for identification by adjustment variables for ACE...done!
Searching for identification by adjustment variables for ACDE...done!
Searching for identification by instrumental variables...done!
Searching for identification by do-calculus skipped.

Exposure: D
Outcome: Y        


Average Causal Effect (ACE)
---------------------            
Method: Selection on Observables (SoO)
Identified: False
Not identifiable by adjustment.

Method: do-calculus (do)
Identified: False
Not conducted. Identification by adjustment or instrumental variable available.

Method: Instrumental Variable (IV)
Identified: True
Instrument: Z1 (if adjusted by Z2) or 
            Z3  or 
            Z4 (if adjusted by X2, Z2)                

Average Controlled Direct Effect (ACDE)
--------------------------------            
Method: Selection on Observables (SoO)
Identified: False
Not identifiable by adjustment.
```

## Conditional effects

Conditional causal effects can be requested with the argument
`conditional`. The argument can be a string for one conditioning
variable or a list for more than one.

``` {.python exports="both" results="output code" tangle="src-identification.py" cache="yes" noweb="no" session="*Python*" linenums="1"}
G_cond = gcm.examples("Two confounders")
G_cond.identification_analysis(conditional="Z1")
```

``` python
Searching for identification by adjustment variables for cACE...done!
Searching for identification by adjustment variables for cACDE...done!
Searching for identification by instrumental variables skipped.
Searching for identification by do-calculus skipped.
```

For conditional effects, the reported parameters are prefixed with `c`,
such as `cACE` and `cACDE`. Instrumental-variable identification is not
available for conditional average effects in the current implementation.

## Print assumptions

Identification results are conditional on the assumptions encoded in the
GCM. To print the identification result together with the identification
assumptions, set `print_assumptions=True`.

``` {.python exports="both" results="output code" tangle="src-identification.py" cache="yes" noweb="no" session="*Python*" linenums="1"}
G.print(
    what="identification",
    identification={
        "print_assumptions": True,
        "print_assumptions_verbose": True,
    },
)
```

``` python

Exposure: D
Outcome: Y        


Average Causal Effect (ACE)
---------------------            
Method: Selection on Observables (SoO)
Identified: False
Not identifiable by adjustment.

Method: do-calculus (do)
Identified: True
Causal probability: p(Y | do(D)) = sum_{Z,Z2} p(Z|D)sum_{D} p(D,Z2)p(Y|Z,D,Z2)

Method: Instrumental Variable (IV)
Identified: False
No instrument available in the DAG.                

Average Controlled Direct Effect (ACDE)
--------------------------------            
Method: Selection on Observables (SoO)
Identified: False
Not identifiable by adjustment.                

Assumptions for identification:
------------------------------
1. Correct DAG
   - Definition: DAG structure matches the true causal relations: (a) A directed arrow from a variable A to a variable B means that there is a causal effect of A on B, which may or may not be zero; (b) Absence of an arrow from a variable C to a variable D implies certainty that C does not cause D; (c) A bidirected arrow between a variable E and a variable F means that they share a common unobserved or latent cause.
   - Scope: Connection between reality and the DAG model
   - Role: Ensures adjustment sets and do-calculus yield the correct identifiable causal effect.
   - Usage: identification
   - Violation: Biased or invalid causal effect estimates and incorrect adjustment sets.            
2. Causal Markov Condition (CMC)
   - Definition: Each variable is independent of its non-descendants given its parents
   - Scope: Connects the DAG and the conditional distribution of each variable
   - Role: Links d-separation to conditional independencies, grounding do-calculus.
   - Usage: identification, discovery
   - Violation: Graph–distribution link breaks and identification results may be incorrect.            
3. Positivity (Overlap)
   - Definition: Each treatment level has a positive probability of occurring, including at all relevant levels of the adjustment variables if they are used for identification.
   - Scope: Variables' distributions
   - Role: Required for the g-formula, IPW, and many identification and estimation strategies.
   - Usage: identification, estimation, inference
   - Violation: Effects are undefined or non-estimable in certain regions of the covariate space.
```

For a fuller discussion of the assumptions themselves, see [Check
Assumptions](../assumptions).

## Practical workflow

A typical GCM identification workflow is:

1.  Build the graph with the exposure, outcome, observed variables, and
    latent variables.
2.  Check whether the graph represents the intended causal assumptions.
3.  Run `G.identification_analysis()`.
4.  Inspect the default or concise output to see which parameters are
    identified.
5.  Use detailed output for the strategy and parameter that will be
    reported.
6.  Retrieve `G.identification_dict` or `G.get_identified()` when the
    result is needed programmatically.
7.  If an assumption is uncertain, compare the identification result
    with an alternative graph.

## References {#sec-refs}

- Ferrari, D. (forthcoming). The Identification of Causal Effects.
  Cambridge University Press.
- Pearl, J. (2009). Causality: Models, Reasoning and Inference.
  Cambridge University Press.
