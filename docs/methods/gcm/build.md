## Creating GCM {#sec-creating-dags}

Suppose we want to create the following Graphical Causal Model (GCM).

![](./tables-and-figures/01-creating.gcm.png)

The graph object can be created using a string describing the graph and
the class `scm.DAG()` from the module `scm` of `causalinf`. There are
many options to use for the string syntax. Any combination of the syntax
options below will work.

``` {.python exports="both" results="output code" tangle="src-scm.py" cache="yes" noweb="no" session="*Python*" linenums="1"}
from causalinf import scm

# option 1: group the parents of each node
# --------
dag = """
Y <- {X1, X2, D}
D <- {X1, Z}
Z <- X2
"""
# option 2: group the children of each node
# --------
dag = """
Z -> D
X1 -> {D, Y}
X2 -> {Z, Y}
D -> Y
"""
# option 3: one or more arrows per line
# --------
dag = """
Y <- X2 -> Z -> D -> Y
D <- X1 -> Y
"""
# or
dag = """
Y <- X2 -> Z -> D -> Y
X1 -> Y
X1 -> D
"""

G = scm.DAG(dag)
print(G)

```

``` python
Graph:
Z -> D
X2 -> Z
D -> Y
X1 -> Y
X1 -> D
X2 -> Y
Observed: X2, D, Z, Y, X1
```

If no further information is provided, all variables (nodes) are assumed
to be observed.

``` {.python exports="both" results="output code" tangle="src-scm.py" cache="yes" noweb="no" session="*Python*" linenums="1"}
from causalinf import scm 
dag = """
Y <- {X1, X2, D}
D <- {X1, Z}
Z <- X2
"""
G = scm.DAG(dag)
print(G)
```

``` python
Graph:
Z -> D
X2 -> Z
D -> Y
X1 -> Y
X1 -> D
X2 -> Y
Observed: X2, D, Z, Y, X1
```

There are different ways to set the type of variable as *Exposure*,
*Outcome*, or *Latent* using a dictionary.

``` {.python exports="both" results="output code" tangle="src-scm.py" cache="yes" noweb="no" session="*Python*" linenums="1"}
var_types = {
    "Exposure": "D",
    "Outcome": "Y",
    "Latent": "X1"
}
# set when when creating the DAG:
G = scm.DAG(dag, nodes_role=var_types)

# or using the set_nodes_role()
G = G.set_nodes_role(var_types)

print(G)
```

``` python
Graph:
Z -> D
X2 -> Z
D -> Y
X1 -> Y
X1 -> D
X2 -> Y
Observed: X2, Z
Exposure: D
Outcome: Y
Latent: X1
```

But note that resetting the variable types changes all of them, and
omitted information assumes that the variables is of the *Observed*
type. For instance:

``` {.python exports="both" results="output code" tangle="src-scm.py" cache="yes" noweb="no" session="*Python*" linenums="1"}
# or using the set_nodes_role()
G = G.set_nodes_role({"Outcome": "D"})

print(G)
```

``` python
Graph:
Z -> D
X2 -> Z
D -> Y
X1 -> Y
X1 -> D
X2 -> Y
Observed: X2, Z, Y, X1
Outcome: D
```

Arbitraty types can be used. These are used only for plotting. For
analysis (identification and estimation), only the four basic ones
(*Outcome*, *Exposure*, *Latent*, and *Observed*) are used.

``` {.python exports="both" results="output code" tangle="src-scm.py" cache="yes" noweb="no" session="*Python*" linenums="1"}
# or using the set_nodes_role()
G = G.set_nodes_role({"My favorite var": "D"})

print(G)
```

``` python
Graph:
Z -> D
X2 -> Z
D -> Y
X1 -> Y
X1 -> D
X2 -> Y
Observed: X2, Z, Y, X1
My favorite var: D
```

## Bidirected/undirected edges

It is possible to define *undirected* and *bidirected* edges as well
with `--` and `<->`. *Bidirected edges* in the context of causal
inference with DAGs indicate an omitted common cause between the
variables connected by the bidirected arrow. *Undirected edges*, on the
other hand, in the context of causal inference with DAGs, are used to
represent the skeleton of the DAG or observationally equivalent edges.
That is, they are edges whose direction cannot be decided inferentially
using observational data unless other parametric assumptions are
adopted.

``` {.python exports="both" results="output code" tangle="src-scm.py" cache="yes" noweb="no" session="*Python*" linenums="1"}
from causalinf import scm 
dag = """
Y <- {X1, X2, D}
D <- {X1, Z}
Z <- X2
Z2 <-> X2
X1 -- Y
"""
G = scm.DAG(dag)
print(G)
```

``` python
Graph:
Z -> D
X2 -> Z
D -> Y
X1 -> Y
X1 -> D
X2 -> Y
Z2 <-> X2
Y -- X1
Observed: Z2, X2, D, Z, Y, X1
```

## GCM Object

The Graphical Causal Model (SCM) object has many useful properties.

``` {.python exports="both" results="output code" tangle="src-creating.py" cache="yes" noweb="no" session="*Python*" linenums="1"}
from causalinf import scm 
dag = """
Y <- {X1, X2, D}
D <- {X1, Z}
Z <- X2
Z2 <-> X2
X1 -- Y
"""
G = scm.DAG(dag)
print(f"""
Nodes:
{G.nodes}
Nodes info:
{G.nodes_info}
Directed edges:
{G.directed}
Bidirected edges:
{G.bidirected}
Undirected edges:
{G.undirected}
""")
```

``` python

Nodes:
{'Z2', 'X2', 'D', 'Z', 'Y', 'X1'}
Nodes info:
{'Z2': {'role': 'Observed', 'label': 'Z2'}, 'X2': {'role': 'Observed', 'label': 'X2'}, 'D': {'role': 'Observed', 'label': 'D'}, 'Z': {'role': 'Observed', 'label': 'Z'}, 'Y': {'role': 'Observed', 'label': 'Y'}, 'X1': {'role': 'Observed', 'label': 'X1'}}
Directed edges:
[('Z', 'D'), ('X2', 'Z'), ('D', 'Y'), ('X1', 'Y'), ('X1', 'D'), ('X2', 'Y')]
Bidirected edges:
[(('Z2', 'X2'), ('X2', 'Z2'))]
Undirected edges:
[{'Y', 'X1'}]
```
