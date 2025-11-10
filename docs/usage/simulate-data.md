---

hide:

-   toc

---

# Simulate Data

The submodule `simulate` contains many classes that allow simulating
data from specific models. For details, see
[Documentation](../../api/#synthetic-data).

The object with the simulated data contains additional information, such
as the parameter values used in the simulation. Below is an example of
simulated data from a Graphical Model. Here is the graph:

``` {.python exports="both" results="silent" tangle="src-simulate-data.py" cache="yes" noweb="no" session="*Python*" linenums="1" eval="always"}
from causalinf import simulate
from causalinf import gcm

G = gcm.examples(which='Pearl Example 1.1 (a)')
G.plot()
```

![](./tables-and-figures/example-simulated-data.png.png)

To simulate data from a linear structure model based on that graph, use:

``` {.python exports="code" results="silent" tangle="src-simulate-data.py" cache="yes" noweb="no" session="*Python*" linenums="1" eval="always"}
sim = simulate.lsem(G)
```

Here are the data and some relevant pieces of information stored in the
`sim` object:

``` {.python exports="both" results="output code" tangle="src-simulate-data.py" cache="yes" noweb="no" session="*Python*" linenums="1" eval="yes"}
print(sim.data.head())
print(sim.parameters_tidy)
print(sim.parameters)

```

``` python
shape: (5, 6)
┌─────────────────────────────────────────────────┐
│     X       W   ('Z',…       Z   ('X',…       Y │
│   f64     f64      f64     f64      f64     f64 │
╞═════════════════════════════════════════════════╡
│ -2.60    0.06     0.87   -1.27     1.58   -0.80 │
│  0.46   -0.02    -1.63    1.83     1.50    0.85 │
│  0.40   -1.68     0.99   -1.27     0.03   -2.05 │
│ -0.74    1.53    -0.62   -1.28     2.16   -1.81 │
│ -1.35    0.43    -0.12   -0.19     1.44   -1.07 │
└─────────────────────────────────────────────────┘
shape: (9, 5)
┌──────────────────────────────────┐
│ lhs   op    rhs   term      true │
│ str   str   str   str        f64 │
╞══════════════════════════════════╡
│ Z     ~     1     Z ~ 1    -0.20 │
│ Z     ~     W     Z ~ W    -0.38 │
│ X     ~     1     ('X',…    0.97 │
│ …     …     …     …            … │
│ Y     ~     1     Y ~ 1    -0.62 │
│ Y     ~     X     Y ~ X    -0.44 │
│ Y     ~     Z     Y ~ Z     0.79 │
└──────────────────────────────────┘
{'X': {}, 'W': {}, ('Z', 'X'): {}, 'Z': {'1': np.float64(-0.2024944618202431), 'W': -0.37573497645208564}, ('X', 'Z'): {'1': np.float64(0.9734059307825849), ('Z', 'X'): -0.1936054264816005}, 'Y': {'1': np.float64(-0.6247919169071756), 'X': -0.44048502113238275, 'Z': 0.7874038243315458}}
```
