## Basic plot

The function [plot()](../../../api/#causalinf.scm.DAG.plot) plots the
graph using `matplotlib` and `networkx` in the background. The position
of the nodes can be set using a dictionary; otherwise, the positions are
calculated automatically. If the type of nodes (*Exposure*, *Outcome*,
.etc) were set (see [Creating DAGs](../creating/)), by default the plot
includes a legend with the node types. There are many options for
customization. Check the documentation of
[plot()](../../../api/#causalinf.scm.DAG.plot) for a comprehensive list
of options.

``` {.python exports="both" results="silent" cache="yes" noweb="no" session="*Python*" tangle="src-scm.py" linenums="1"}
from causalinf import gcm
dag = """
Y <- {X1, X2, D}
D <- {X1, Z}
Z <- X2
"""
pos = {'D': (0, 0),
       'Y': (1, 0),
       'Z': (-1, 0),
       'X2': (0.5, -1),
       'X1': (0.5, 1)}
var_types = {"Exposure":"Y", "Outcome":"D"}
G = gcm.DAG(dag, nodes_role=var_types, nodes_position=pos)
G.plot()
```

*Bidirected edges* are represented by default in the plot with dashed
curved lines. In the context of causal inference with DAGs, by
convention these arrows (often called \"arcs\") indicate a latent or
unobserved common cause between the variables connected by the
bidirected arrow. Alternatively, these variables can be included
explicitly when creating the DAG.

*Undirected edges*, on the other hand, in the context of causal
inference with DAGs, are used to represent the skeleton of the DAG or
observationally equivalent edges. That is, they are edges whose
direction cannot be decided inferentially using observational data
unless other parametric assumptions are adopted.

Here is an example (the example is just for illustration; the types of
edges have no meaning in the example):

``` {.python exports="both" results="silent" tangle="src-scm.py" cache="yes" noweb="no" session="*Python*" linenums="1"}
from causalinf import scm
dag = """
Y <- {X1, X2, D}
D <- X1
Z <- X2
D -- Z
Y <-> X2
"""
pos = {'D': (0, 0),
       'Y': (1, 0),
       'Z': (-1, 0),
       'X2': (0.5, -1),
       'X1': (0.5, 1)}
var_types = {"Exposure":"Y", "Outcome":"D"}
G = scm.DAG(dag, nodes_role=var_types, nodes_position=pos)
G.plot()
```

![](./tables-and-figures/02-plotting-gcm-bidirected-and-undirected.png)

## Graph Styles

### Default

There are some default styles provided by the package.

``` {.python exports="both" results="silent" tangle="src-scm.py" cache="yes" noweb="no" session="*Python*" linenums="1"}
from causalinf import scm
dag = """
Y <- {X1, X2, D}
D <- {X1, Z}
Z <- X2
"""
pos = {'D': (0, 0),
       'Y': (1, 0),
       'Z': (-1, 0),
       'X2': (0.5, -1),
       'X1': (0.5, 1)}
var_types = {"Exposure":"Y", "Outcome":"D"}
G = scm.DAG(dag, nodes_role=var_types, nodes_position=pos)
G.plot() # this is the default style, equivalent to G.plot(graph_style="default")
```

![](./tables-and-figures/02-plotting-style-default.png)

### Rectangular

Retangular style gives more space for labels. But see also [Node
style](#sec-node-style).

``` {.python exports="both" results="silent" tangle="src-scm.py" cache="yes" noweb="no" session="*Python*" linenums="1"}
G.plot(graph_style="rectangle", nodes_label={'D':'Treatment'}) 
```

![](./tables-and-figures/02-plotting-style-rectangle.png)

### Pearl

The \"pearl\" style uses the design adopted in [Pearl
(2009)](#sec-plot-styles-refs). The position of the node label needs to
be adjusted manually. The label positions can be adjusted in block using
a float or individually using a dictionary. For instance,
`node_label_adj_y={"Z":.1}` adjusts only the `y` position of node $Z$,
while `node_label_adj_y=.1` adjusts it for all nodes.

``` {.python exports="both" results="silent" tangle="src-scm.py" cache="yes" noweb="no" session="*Python*" linenums="1"}
G.plot(graph_style="pearl", node_label_adj_y=.1) 
```

![](./tables-and-figures/02-plotting-style-pearl.png)

## [TODO]{.todo .TODO} Plot sub-DAG {#plot-sub-dag}

## [TODO]{.todo .TODO} Nodes {#nodes}

### Node label

It is possible to use labels for the nodes. Labels accept LaTeX
mathematical expressions. For instance, to use subscripts for some
variables, we can set the labels as follows:

``` {.python exports="code" results="silent" tangle="src-scm.py" cache="yes" noweb="no" session="*Python*" eval="no-export" linenums="1"}
from causalinf import scm
dag = """
Y <- {X1, X2, D}
D <- {X1, Z}
Z <- X2
"""
pos = {'D': (0, 0),
       'Y': (1, 0),
       'Z': (-1, 0),
       'X2': (0.5, -1),
       'X1': (0.5, 1)}
labels = {
    "X2" : "$X_2$",
    "X1" : "$X_1$"
}
var_types = {"Exposure":"Y", "Outcome":"D"}

G = scm.DAG(dag, nodes_role=var_types, nodes_label=labels, nodes_position=pos)
G.plot()
```

![](./tables-and-figures/02-plotting-gcm-nodes-label.png)

### [TODO]{.todo .TODO} Node style {#sec-node-style}

## [TODO]{.todo .TODO} Edges {#edges}

### Edge style

## References {#sec-refs}

-   Pearl, J. (2009). Causality: Models, Reasoning and Inference. :
    Cambridge University Press.
