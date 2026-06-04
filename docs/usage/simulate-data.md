# Simulate Data

The submodule `simulate` creates synthetic data from causal models. This
is useful for examples, tutorials, simulation studies, checking
estimators, and building reproducible workflows before using real data.

The basic structure to simulate data is `simulate.<model name>`. For
instance, `simulate.lsem()` simulates data from a **Linear Structural
Equation Model** (LSEM) implied by a Graphical Causal Model (GCM). In
this case, the simulator uses the graph to determine the order of the
variables and which variables are parents of each node. For each
endogenous variable, it generates a linear equation using randomly drawn
coefficients and Gaussian noise.

The object returned by `simulate.<model>` stores both the simulated data
and the true parameters used to generate them. This is useful because
the true data-generating process is known.

## Basic example

Start with a GCM. Here, we use one of the built-in examples:

``` {.python exports="both" results="silent" tangle="src-simulate-data.py" cache="yes" noweb="no" session="*Python*" linenums="1" eval="always"}
from causalinf import simulate
from causalinf import gcm

G = gcm.examples(which='Two confounders')
G.plot()
```

![](./tables-and-figures/example-simulated-data.png)

To simulate data from a linear structural equation model based on that
graph, use:

``` {.python exports="both" results="output code" tangle="src-simulate-data.py" cache="yes" noweb="no" session="*Python*" linenums="1" eval="always"}
sim = simulate.lsem(G, seed=1)
print(sim)
```

``` python
Linear Structural Equation Model (LSEM): 
D = (0.4071) + (0.7584)*Z2 + (-0.6624)*Z1
Y = (-0.2731) + (-0.3515)*Z1 + (-0.2122)*Z2 + (-0.8772)*D
shape: (1_000, 4)
┌───────────┬───────────┬───────────┬───────────┐
│ Z1        ┆ Z2        ┆ D         ┆ Y         │
│ ---       ┆ ---       ┆ ---       ┆ ---       │
│ f64       ┆ f64       ┆ f64       ┆ f64       │
╞═══════════╪═══════════╪═══════════╪═══════════╡
│ 1.624345  ┆ -0.153236 ┆ -0.495579 ┆ 0.528705  │
│ -0.611756 ┆ -2.432509 ┆ -2.621482 ┆ 2.393703  │
│ -0.528172 ┆ 0.507984  ┆ 2.445209  ┆ -1.126385 │
│ -1.072969 ┆ -0.324032 ┆ -0.193344 ┆ -0.736317 │
│ 0.865408  ┆ -1.511077 ┆ -1.235186 ┆ -0.484971 │
│ …         ┆ …         ┆ …         ┆ …         │
│ -0.116444 ┆ 0.188583  ┆ 0.911065  ┆ -1.6025   │
│ -2.277298 ┆ 0.560918  ┆ 3.063715  ┆ -0.866042 │
│ -0.069625 ┆ -0.921659 ┆ 0.040004  ┆ 2.018582  │
│ 0.35387   ┆ 0.647375  ┆ 0.288054  ┆ 0.076519  │
│ -0.186955 ┆ 1.386826  ┆ 2.995921  ┆ -3.579248 │
└───────────┴───────────┴───────────┴───────────┘
```

The argument `seed` makes the simulation reproducible. If `seed` is
omitted, a new random simulation is drawn each time.

## Simulated data

The simulated data are stored in `sim.data`. The object is a dataframe
from `tidypolars4sci`.

``` {.python exports="both" results="output code" tangle="src-simulate-data.py" cache="yes" noweb="no" session="*Python*" linenums="1" eval="always"}
print(sim.data.head())
```

``` python
shape: (5, 4)
┌───────────┬───────────┬───────────┬───────────┐
│ Z1        ┆ Z2        ┆ D         ┆ Y         │
│ ---       ┆ ---       ┆ ---       ┆ ---       │
│ f64       ┆ f64       ┆ f64       ┆ f64       │
╞═══════════╪═══════════╪═══════════╪═══════════╡
│ 1.624345  ┆ -0.153236 ┆ -0.495579 ┆ 0.528705  │
│ -0.611756 ┆ -2.432509 ┆ -2.621482 ┆ 2.393703  │
│ -0.528172 ┆ 0.507984  ┆ 2.445209  ┆ -1.126385 │
│ -1.072969 ┆ -0.324032 ┆ -0.193344 ┆ -0.736317 │
│ 0.865408  ┆ -1.511077 ┆ -1.235186 ┆ -0.484971 │
└───────────┴───────────┴───────────┴───────────┘
```

The number of observations is controlled by the argument `n`.

``` {.python exports="both" results="output code" tangle="src-simulate-data.py" cache="yes" noweb="no" session="*Python*" linenums="1" eval="always"}
sim_small = simulate.lsem(G, n=5, seed=1)
print(sim_small.data)
```

``` python
shape: (5, 4)
┌───────────┬───────────┬───────────┬───────────┐
│ Z1        ┆ Z2        ┆ D         ┆ Y         │
│ ---       ┆ ---       ┆ ---       ┆ ---       │
│ f64       ┆ f64       ┆ f64       ┆ f64       │
╞═══════════╪═══════════╪═══════════╪═══════════╡
│ 1.624345  ┆ -2.301539 ┆ 1.453514  ┆ 1.564702  │
│ -0.611756 ┆ 1.744812  ┆ -1.841985 ┆ -0.359266 │
│ -0.528172 ┆ -0.761207 ┆ 0.938394  ┆ -1.402515 │
│ -1.072969 ┆ 0.319039  ┆ -1.399277 ┆ 1.431886  │
│ 0.865408  ┆ -0.24937  ┆ 1.095344  ┆ -0.449383 │
└───────────┴───────────┴───────────┴───────────┘
```

## True parameters

The simulator stores the true coefficients in two formats:

1.  `sim.parameters`, a nested dictionary keyed by endogenous variable
    and parent variable.
2.  `sim.parameters_tidy`, a tidy dataframe with one row per parameter.

``` {.python exports="both" results="output code" tangle="src-simulate-data.py" cache="yes" noweb="no" session="*Python*" linenums="1" eval="always"}
print(sim.parameters)
```

``` python
{'Z1': {}, 'Z2': {}, 'D': {'1': np.float64(0.40709546440285704), 'Z2': 0.758397121073191, 'Z1': -0.6623996198448128}, 'Y': {'1': np.float64(-0.2731382139476062), 'Z1': -0.3514895517458223, 'Z2': -0.21224372445969886, 'D': -0.8771756918836713}}
```

``` {.python exports="both" results="output code" tangle="src-simulate-data.py" cache="yes" noweb="no" session="*Python*" linenums="1" eval="always"}
print(sim.parameters_tidy)
```

``` python
shape: (7, 5)
┌─────┬─────┬─────┬────────┬───────────┐
│ lhs ┆ op  ┆ rhs ┆ term   ┆ true      │
│ --- ┆ --- ┆ --- ┆ ---    ┆ ---       │
│ str ┆ str ┆ str ┆ str    ┆ f64       │
╞═════╪═════╪═════╪════════╪═══════════╡
│ D   ┆ ~   ┆ 1   ┆ D ~ 1  ┆ 0.407095  │
│ D   ┆ ~   ┆ Z2  ┆ D ~ Z2 ┆ 0.758397  │
│ D   ┆ ~   ┆ Z1  ┆ D ~ Z1 ┆ -0.6624   │
│ Y   ┆ ~   ┆ 1   ┆ Y ~ 1  ┆ -0.273138 │
│ Y   ┆ ~   ┆ Z1  ┆ Y ~ Z1 ┆ -0.35149  │
│ Y   ┆ ~   ┆ Z2  ┆ Y ~ Z2 ┆ -0.212244 │
│ Y   ┆ ~   ┆ D   ┆ Y ~ D  ┆ -0.877176 │
└─────┴─────┴─────┴────────┴───────────┘
```

The true parameters can be compared with estimates from the
corresponding causal model. See [Estimation](./estimation) and [Summary
and Reporting](./summary-and-reporting) for examples of estimation and
reporting workflows.

## Noise

The argument `noise` controls the standard deviation of the Gaussian
disturbance terms. A single number sets the same noise level for all
variables.

``` {.python exports="both" results="output code" tangle="src-simulate-data.py" cache="yes" noweb="no" session="*Python*" linenums="1" eval="always"}
sim_low_noise = simulate.lsem(G, seed=1, noise=0.25)
print(sim_low_noise.data.head())
```

``` python
shape: (5, 4)
┌───────────┬───────────┬───────────┬───────────┐
│ Z1        ┆ Z2        ┆ D         ┆ Y         │
│ ---       ┆ ---       ┆ ---       ┆ ---       │
│ f64       ┆ f64       ┆ f64       ┆ f64       │
╞═══════════╪═══════════╪═══════════╪═══════════╡
│ 0.406086  ┆ -0.038309 ┆ 0.181427  ┆ -0.340498 │
│ -0.152939 ┆ -0.608127 ┆ -0.350049 ┆ 0.125751  │
│ -0.132043 ┆ 0.126996  ┆ 0.916624  ┆ -0.754271 │
│ -0.268242 ┆ -0.081008 ┆ 0.256985  ┆ -0.656754 │
│ 0.216352  ┆ -0.377769 ┆ -0.003475 ┆ -0.593917 │
└───────────┴───────────┴───────────┴───────────┘
```

Use a dictionary to set variable-specific noise levels. Variables not
included in the dictionary use the default value `1.0`.

``` {.python exports="both" results="output code" tangle="src-simulate-data.py" cache="yes" noweb="no" session="*Python*" linenums="1" eval="always"}
sim_custom_noise = simulate.lsem(
    G,
    seed=1,
    noise={"D": 0.25, "Y": 2.0},
)
print(sim_custom_noise.data.head())
```

``` python
shape: (5, 4)
┌───────────┬───────────┬───────────┬───────────┐
│ Z1        ┆ Z2        ┆ D         ┆ Y         │
│ ---       ┆ ---       ┆ ---       ┆ ---       │
│ f64       ┆ f64       ┆ f64       ┆ f64       │
╞═══════════╪═══════════╪═══════════╪═══════════╡
│ 1.624345  ┆ -0.153236 ┆ -0.712708 ┆ 1.624715  │
│ -0.611756 ┆ -2.432509 ┆ -1.429734 ┆ 0.984361  │
│ -0.528172 ┆ 0.507984  ┆ 1.46796   ┆ 0.944635  │
│ -1.072969 ┆ -0.324032 ┆ 0.605727  ┆ -2.51593  │
│ 0.865408  ┆ -1.511077 ┆ -1.292906 ┆ -1.746182 │
└───────────┴───────────┴───────────┴───────────┘
```

## Binary, ordinal, and categorical variables

By default, all variables are simulated as continuous. The arguments
`binary`, `ordinal`, and `categorical` can be used to discretize
selected variables.

Use `binary` for Bernoulli variables. The argument can be a string or a
list of variable names.

``` {.python exports="both" results="output code" tangle="src-simulate-data.py" cache="yes" noweb="no" session="*Python*" linenums="1" eval="always"}
sim_binary = simulate.lsem(G, seed=1, binary="Y")

print(sim_binary.binary)
print(sim_binary.data.head())
```

``` python
('Y',)
shape: (5, 4)
┌───────────┬───────────┬───────────┬─────┐
│ Z1        ┆ Z2        ┆ D         ┆ Y   │
│ ---       ┆ ---       ┆ ---       ┆ --- │
│ f64       ┆ f64       ┆ f64       ┆ i64 │
╞═══════════╪═══════════╪═══════════╪═════╡
│ 1.624345  ┆ -0.153236 ┆ -0.495579 ┆ 1   │
│ -0.611756 ┆ -2.432509 ┆ -2.621482 ┆ 1   │
│ -0.528172 ┆ 0.507984  ┆ 2.445209  ┆ 0   │
│ -1.072969 ┆ -0.324032 ┆ -0.193344 ┆ 0   │
│ 0.865408  ┆ -1.511077 ┆ -1.235186 ┆ 0   │
└───────────┴───────────┴───────────┴─────┘
```

Use `ordinal` to create ordered integer variables. The dictionary values
set the lower and upper bounds.

``` {.python exports="both" results="output code" tangle="src-simulate-data.py" cache="yes" noweb="no" session="*Python*" linenums="1" eval="always"}
sim_ordinal = simulate.lsem(G, seed=1, ordinal={"Y": [1, 5]})

print(sim_ordinal.ordinal)
print(sim_ordinal.data.head())
```

``` python
{'Y': (1, 5)}
shape: (5, 4)
┌───────────┬───────────┬───────────┬─────┐
│ Z1        ┆ Z2        ┆ D         ┆ Y   │
│ ---       ┆ ---       ┆ ---       ┆ --- │
│ f64       ┆ f64       ┆ f64       ┆ i64 │
╞═══════════╪═══════════╪═══════════╪═════╡
│ 1.624345  ┆ -0.153236 ┆ -0.495579 ┆ 4   │
│ -0.611756 ┆ -2.432509 ┆ -2.621482 ┆ 5   │
│ -0.528172 ┆ 0.507984  ┆ 2.445209  ┆ 2   │
│ -1.072969 ┆ -0.324032 ┆ -0.193344 ┆ 2   │
│ 0.865408  ┆ -1.511077 ┆ -1.235186 ┆ 2   │
└───────────┴───────────┴───────────┴─────┘
```

Use `categorical` to create variables with named categories.

``` {.python exports="both" results="output code" tangle="src-simulate-data.py" cache="yes" noweb="no" session="*Python*" linenums="1" eval="always"}
sim_categorical = simulate.lsem(
    G,
    seed=1,
    categorical={"Y": ["low", "medium", "high"]},
)

print(sim_categorical.categorical)
print(sim_categorical.data.head())
```

``` python
{'Y': ('low', 'medium', 'high')}
shape: (5, 4)
┌───────────┬───────────┬───────────┬────────┐
│ Z1        ┆ Z2        ┆ D         ┆ Y      │
│ ---       ┆ ---       ┆ ---       ┆ ---    │
│ f64       ┆ f64       ┆ f64       ┆ str    │
╞═══════════╪═══════════╪═══════════╪════════╡
│ 1.624345  ┆ -0.153236 ┆ -0.495579 ┆ medium │
│ -0.611756 ┆ -2.432509 ┆ -2.621482 ┆ high   │
│ -0.528172 ┆ 0.507984  ┆ 2.445209  ┆ low    │
│ -1.072969 ┆ -0.324032 ┆ -0.193344 ┆ low    │
│ 0.865408  ┆ -1.511077 ┆ -1.235186 ┆ medium │
└───────────┴───────────┴───────────┴────────┘
```

A variable can only use one of these types. For example, the same
variable cannot be both binary and ordinal in the same simulation.

## Use simulated data for estimation

Simulated data can be passed directly to an estimator. For example, the
data generated from a GCM can be used to estimate a Structural Causal
Model (SCM):

``` {.python exports="both" results="output code" tangle="src-simulate-data.py" cache="yes" noweb="no" session="*Python*" linenums="1" eval="always"}
from causalinf import scm

G_scm = gcm.examples("Two confounders")
sim_scm = simulate.lsem(G_scm, seed=1)
mod = scm.estimate(G_scm, data=sim_scm.data)
```

``` python
Estimating LSEM...done!
```

The estimated parameters can then be compared with the true simulation
parameters.

``` {.python exports="both" results="output code" tangle="src-simulate-data.py" cache="yes" noweb="no" session="*Python*" linenums="1" eval="always"}
print(sim_scm.parameters_tidy)
mod.est.parameters.print()
```

``` python
shape: (7, 5)
┌─────┬─────┬─────┬────────┬───────────┐
│ lhs ┆ op  ┆ rhs ┆ term   ┆ true      │
│ --- ┆ --- ┆ --- ┆ ---    ┆ ---       │
│ str ┆ str ┆ str ┆ str    ┆ f64       │
╞═════╪═════╪═════╪════════╪═══════════╡
│ D   ┆ ~   ┆ 1   ┆ D ~ 1  ┆ 0.407095  │
│ D   ┆ ~   ┆ Z2  ┆ D ~ Z2 ┆ 0.758397  │
│ D   ┆ ~   ┆ Z1  ┆ D ~ Z1 ┆ -0.6624   │
│ Y   ┆ ~   ┆ 1   ┆ Y ~ 1  ┆ -0.273138 │
│ Y   ┆ ~   ┆ Z1  ┆ Y ~ Z1 ┆ -0.35149  │
│ Y   ┆ ~   ┆ Z2  ┆ Y ~ Z2 ┆ -0.212244 │
│ Y   ┆ ~   ┆ D   ┆ Y ~ D  ┆ -0.877176 │
└─────┴─────┴─────┴────────┴───────────┘
shape: (16, 9)
┌──────────────┬─────────────┬──────────┬─────┬──────┬───────┬───────┬───────────┬────────┐
│ term         ┆ label       ┆ estimate ┆ sig ┆ se   ┆ lo    ┆ hi    ┆ statistic ┆ pvalue │
│ ---          ┆ ---         ┆ ---      ┆ --- ┆ ---  ┆ ---   ┆ ---   ┆ ---       ┆ ---    │
│ str          ┆ str         ┆ f64      ┆ str ┆ f64  ┆ f64   ┆ f64   ┆ f64       ┆ f64    │
╞══════════════╪═════════════╪══════════╪═════╪══════╪═══════╪═══════╪═══════════╪════════╡
│ Y ~ 1        ┆ beta_0Y     ┆ -0.27    ┆ *** ┆ 0.03 ┆ -0.34 ┆ -0.20 ┆ -7.84     ┆ 0.00   │
│ Y ~ Z1       ┆ beta_Z1.Y   ┆ -0.38    ┆ *** ┆ 0.04 ┆ -0.46 ┆ -0.30 ┆ -9.69     ┆ 0.00   │
│ Y ~ D        ┆ beta_D.Y    ┆ -0.89    ┆ *** ┆ 0.03 ┆ -0.95 ┆ -0.83 ┆ -27.75    ┆ 0.00   │
│ Y ~ Z2       ┆ beta_Z2.Y   ┆ -0.20    ┆ *** ┆ 0.04 ┆ -0.28 ┆ -0.13 ┆ -5.22     ┆ 0.00   │
│ D ~ 1        ┆ beta_0D     ┆ 0.42     ┆ *** ┆ 0.03 ┆ 0.35  ┆ 0.48  ┆ 13.27     ┆ 0.00   │
│ D ~ Z1       ┆ beta_Z1.D   ┆ -0.70    ┆ *** ┆ 0.03 ┆ -0.76 ┆ -0.63 ┆ -21.84    ┆ 0.00   │
│ D ~ Z2       ┆ beta_Z2.D   ┆ 0.74     ┆ *** ┆ 0.03 ┆ 0.68  ┆ 0.80  ┆ 24.32     ┆ 0.00   │
│ Y ~~ Y       ┆             ┆ 1.00     ┆ *** ┆ 0.04 ┆ 0.91  ┆ 1.09  ┆ 22.36     ┆ 0.00   │
│ D ~~ D       ┆             ┆ 0.98     ┆ *** ┆ 0.04 ┆ 0.89  ┆ 1.06  ┆ 22.36     ┆ 0.00   │
│ Z1 ~~ Z1     ┆             ┆ 0.96     ┆     ┆ 0.00 ┆ 0.96  ┆ 0.96  ┆ null      ┆ null   │
│ Z1 ~~ Z2     ┆             ┆ 0.02     ┆     ┆ 0.00 ┆ 0.02  ┆ 0.02  ┆ null      ┆ null   │
│ Z2 ~~ Z2     ┆             ┆ 1.06     ┆     ┆ 0.00 ┆ 1.06  ┆ 1.06  ┆ null      ┆ null   │
│ Z1 ~ 1       ┆             ┆ 0.04     ┆     ┆ 0.00 ┆ 0.04  ┆ 0.04  ┆ null      ┆ null   │
│ Z2 ~ 1       ┆             ┆ 0.03     ┆     ┆ 0.00 ┆ 0.03  ┆ 0.03  ┆ null      ┆ null   │
│ Direct_effec ┆ Direct_effe ┆ -0.89    ┆ *** ┆ 0.03 ┆ -0.95 ┆ -0.83 ┆ -27.75    ┆ 0.00   │
│ t :=         ┆ ct          ┆          ┆     ┆      ┆       ┆       ┆           ┆        │
│ (beta_D.Y)   ┆             ┆          ┆     ┆      ┆       ┆       ┆           ┆        │
│ Total_effect ┆ Total_effec ┆ -0.89    ┆ *** ┆ 0.03 ┆ -0.95 ┆ -0.83 ┆ -27.75    ┆ 0.00   │
│ := Direct_ef ┆ t           ┆          ┆     ┆      ┆       ┆       ┆           ┆        │
│ fect         ┆             ┆          ┆     ┆      ┆       ┆       ┆           ┆        │
└──────────────┴─────────────┴──────────┴─────┴──────┴───────┴───────┴───────────┴────────┘
```

## Practical checklist

When using simulated data, record:

1.  The graph used to define the data-generating process.
2.  The number of observations `n`.
3.  The random seed.
4.  The noise level.
5.  Which variables, if any, were simulated as binary, ordinal, or
    categorical.
6.  The true parameters stored in `sim.parameters` or
    `sim.parameters_tidy`.

These details make the simulation reproducible and make it easier to
compare estimators against the known data-generating process.
