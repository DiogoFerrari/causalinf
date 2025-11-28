## Examples

The example below shows how to

1.  Create a DAG using a string `dag` and the function `DAG`
2.  Set the nodes\' positions using a dictionary `pos`
3.  Set roles of the nodes (Exposure, Outcome, etc.) using a dictionary
    `roles`
4.  Set labels for nodes using a dictionary `node_labels`, including
    with LaTeX expressions
5.  Set labels for the edges using a dictionary `edge_labels`, including
    with LaTeX expressions

``` {.python exports="both" results="silent" tangle="src-gcm-DAG.py" cache="yes" noweb="no" session="*Python*" linenums="1" eval="always"}
from causalinf import gcm

dag  = '''
D -> {M1, Y}   # Defines two directed edges: D->Y and D->M1
M1 -- M2       # Defines an undirected edge b/w M1 and M2
M2 -> Y        # Defines one directed edge from M2 to Y
M3 -> Y
D <-> Y        # Defines a bidirected edge b/w D and Y
Z -> {D, Y}
'''
pos = {'D': (0,0),
       'Y': (1,0),
       'Z': (.5, -1),
       'M1': (.25, 1),
       'M2': (.75, 1),
       'M3': (1.75, 1),
       }
roles = {'Exposure'    : "D",
         'Outcome'     : "Y",
         "Latent"      : 'Z',
         "The M2 node" : "M2" # arbtiraty roles available
         }
node_labels = {"D": "$\widetilde{D}$",
               'Y': "Outcome"}
edge_labels = {
    # directed edge labels
     ('D', 'M1') : 1,
     ('M2', 'Y') : -1,
     ('M3', 'Y') : 'a',
     ('D', 'Y') : 'AbC',
     ('Z', 'D') : '$\\beta$',
     ('Z', 'Y'): 'asccc',
     # bidirected edge label
     (('D', 'Y'), ('Y', 'D')): '$f(x)=\\alpha$',
     # undirected edge label
     ( 'M1', 'M2' ) : 1234, # 
     ( 'M2', 'M1' ) : 1234, # 
}

G = gcm.DAG(dag, nodes_label=node_labels, nodes_position=pos, edge_label=edge_labels)
G.plot()
```

![](./tables-and-figures/gcm-DAG-with-labels.png)

