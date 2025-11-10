---

hide:

-   toc

---

# Examples

Pre-defined examples are available in the `causalinf` package for some
methods. They can be accessed with the function `examples()`. If no
argument is provided, it lists all examples available for the method.
The general structure is:

``` {.python exports="code" results="silent" tangle="src-examples.py" cache="yes" noweb="no" session="*Python*" linenums="1" eval="never"}
from causalinf import <submodule>

<submodule>.examples()

```

For instance, to list the examples available for the Graphical Causal
Models (**GCM**) submodule, use:

``` {.python exports="both" results="output code" tangle="src-examples.py" cache="yes" noweb="no" session="*Python*" linenums="1" eval="always"}
from causalinf import gcm

gcm.examples()
```

``` python

List of available examples:
--------------------------        
1. Not identifiable
2. One confounder
3. Two confounders
4. Front-door
5. IV with 1 instrument
6. IV with 3 instruments
7. SoO, IV, and do identified with 1 confounder
8. Mediation: 2 sequential 1 confounder
9. Pearl Example 1.1 (a)
10. Pearl Example 1.1 (b)
11. Pearl Example 1.2
12. Pearl Example 1.3 (a)
13. Pearl Example 1.3 (b)
14. Pearl Example 3.1
15. Pearl Example 3.4
16. Pearl Example 3.5

Usage: examples(which='<example name>')
Example: G = examples(which='Pearl Example 3.5')
Note: To print the associated DAG of each example, use examples(print_DAG=True)
```

As described in the last lines of the output above, to use one of the
examples, say Pearl Example 1.1, which is based on example 1.1 from
Pearl ([2009](#sec-refs)), run:

``` {.python exports="both" results="silent" cache="yes" noweb="no" session="*Python*" tangle="src-scm.py" linenums="1"}
G = gcm.examples(which='Pearl Example 1.1 (a)')
G.plot()
```

![](./tables-and-figures/example.png.png)

See [Simulate Data](./simulate-data.md) to generate synthetic data from
the graph.

## References {#sec-refs}

-   Pearl, J. (2009). Causality: Models, Reasoning and Inference. :
    Cambridge Univ Press.
