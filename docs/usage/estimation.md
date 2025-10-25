## Overview

The function `<submodule>.estimate(<args>)` can be used in all
submodules to run the estimation and collect inference statistics
(p-value, z-scores, etc.). For instance, to estimate a **DiD** model,
use:

``` {.python exports="code" results="silent" tangle="src-overview.py" cache="yes" noweb="no" session="*Python*" linenums="1" eval="never"}
from causalinf import did

mod = did.estimate(<args>, data=<DataFrame>)
```

`<args>` vary across submodules depending on the method used.

The object created by `estimate()` is method-specific, but it contains
some key information about the estimation procedure, including the `fit`
statistics, the `statistical model` (e.g., logit, linear model,
non-parametric difference in averages, etc.) used to compute the
parameter(s), the estimated `parameters`, `standard errors`, and
additional `options` used by the statistical model. The way the
information is stored in the `estimate()` object is standardized across
causal models.

## Example

Let us use a Structural Causal Model (SCM) to illustrate the
`estimate()` object, with an example (see [Examples](../examples)) with
simulated data (see [Simulate Data](../simulate-data)) from a Linear
Structural Equation Model (LSEM) created from the SCM (see
[SCM](../../methods/scm/#estimation/)).

``` {.python exports="code" results="silent" tangle="src-estimation.py" cache="yes" noweb="no" session="*Python*" linenums="1" eval="always"}
from causalinf import simulate
from causalinf import gcm
from causalinf import scm

# get the example
G = gcm.examples('Two confounders')
# simulate the data from LSEM
sim = simulate.lsem(G, seed=1)

G.plot()
```

![](./tables-and-figures/estimation-scm-example-1.png)

Here is the data:

``` {.python exports="both" results="output code" tangle="src-estimation.py" cache="yes" noweb="no" session="*Python*" linenums="1" eval="always"}

df = sim.data
print(df)

```

``` python
shape: (1_000, 4)
┌───────────────────────────────┐
│    Z2      Z1       D       Y │
│   f64     f64     f64     f64 │
╞═══════════════════════════════╡
│  1.62   -0.15    2.03   -1.17 │
│ -0.61   -2.43   -0.03    0.76 │
│ -0.53    0.51    0.97    1.02 │
│     …       …       …       … │
│ -0.07   -0.92    1.25    1.95 │
│  0.35    0.65   -0.13    0.08 │
│ -0.19    1.39    0.76   -1.21 │
└───────────────────────────────┘
```

## Estimate

The model estimation is (for details of the default options to estimate
SCM using `estimate()`, see [here](../../methods/scm/#estimation/)):

``` {.python exports="both" results="output code" tangle="src-estimation.py" cache="yes" noweb="no" session="*Python*" linenums="1" eval="always"}
mod = scm.estimate(G, data=df)
```

``` python
Estimating LSEM...done!
```

It produces the estimated object which in the code above was in `mod`:

``` {.python exports="both" results="output code" tangle="src-estimation.py" cache="yes" noweb="no" session="*Python*" linenums="1" eval="always"}
print(mod.__class__)
```

``` python
<class 'causalinf.scm.estimate'>
```

## Properties

The main pieces of information that can be directly extracted from the
`estimate()` object are (the same `estimate()` object properties are
used in all other causal inference methods):

``` {.python exports="both" results="output code" tangle="src-estimation.py" cache="yes" noweb="no" session="*Python*" linenums="1" eval="always"}
mod.est.parameters.print() # mod.est.parameters is an dataframe from tidypolars4sci

print(mod.est.se)

print(mod.est.fit)

print(mod.est.fit_extra)

print(mod.est.options)
```

``` python
shape: (16, 9)
┌────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ term                            label           estimate   sig     se      lo      hi   statistic   pvalue │
│ str                             str                  f64   str    f64     f64     f64         f64      f64 │
╞════════════════════════════════════════════════════════════════════════════════════════════════════════════╡
│ D ~ 1                           beta_0D             0.42   ***   0.03    0.35    0.48       13.27     0.00 │
│ D ~ Z1                          beta_Z1.D          -0.68   ***   0.03   -0.74   -0.62      -22.50     0.00 │
│ D ~ Z2                          beta_Z2.D           0.73   ***   0.03    0.66    0.79       22.75     0.00 │
│ Y ~ 1                           beta_0Y            -0.27   ***   0.03   -0.34   -0.20       -7.84     0.00 │
│ Y ~ Z1                          beta_Z1.Y          -0.36   ***   0.04   -0.43   -0.28       -9.47     0.00 │
│ Y ~ D                           beta_D.Y           -0.22   ***   0.03   -0.29   -0.16       -6.97     0.00 │
│ Y ~ Z2                          beta_Z2.Y          -0.89   ***   0.04   -0.97   -0.81      -22.40     0.00 │
│ D ~~ D                                              0.98   ***   0.04    0.89    1.06       22.36     0.00 │
│ Y ~~ Y                                              1.00   ***   0.04    0.91    1.09       22.36     0.00 │
│ Z1 ~~ Z1                                            1.06         0.00    1.06    1.06        null     null │
│ Z1 ~~ Z2                                            0.02         0.00    0.02    0.02        null     null │
│ Z2 ~~ Z2                                            0.96         0.00    0.96    0.96        null     null │
│ Z1 ~ 1                                              0.03         0.00    0.03    0.03        null     null │
│ Z2 ~ 1                                              0.04         0.00    0.04    0.04        null     null │
│ Direct_effect := (beta_D.Y)     Direct_effect      -0.22   ***   0.03   -0.29   -0.16       -6.97     0.00 │
│ Total_effect := Direct_effect   Total_effect       -0.22   ***   0.03   -0.29   -0.16       -6.97     0.00 │
└────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
{'type': 'classic', 'description': 'Standard errors: classic'}
{'Model': '(footnote)', 'Outcome_type': '(footnote)', 'Estimator': 'ML', 'Std_Error': 'classic', 'N_obs': 1000, 'RMSE': 0.0, 'AIC': 5670.735569404551, 'BIC': 5714.90536691539, 'R2': None, 'R2_adj': None, 'DF_resid': None, 'DF_model': 0}
{'npar': 9.0, 'fmin': 4.440892098500626e-16, 'chisq': 8.881784197001252e-13, 'df': 0.0, 'pvalue': nan, 'baseline.chisq': 1467.3085145359757, 'baseline.df': 5.0, 'baseline.pvalue': 0.0, 'cfi': 0.9999999999999994, 'tli': 1.0, 'nnfi': 1.0, 'rfi': 1.0, 'nfi': 1.0, 'pnfi': 0.0, 'ifi': 0.9999999999999993, 'rni': 0.9999999999999994, 'logl': -2826.3677847022755, 'unrestricted.logl': -2826.3677847022745, 'aic': 5670.735569404551, 'bic': 5714.90536691539, 'ntotal': 1000.0, 'bic2': 5686.320864466223, 'rmsea': 0.0, 'rmsea.ci.lower': 0.0, 'rmsea.ci.upper': 0.0, 'rmsea.ci.level': 0.9, 'rmsea.pvalue': nan, 'rmsea.close.h0': 0.05, 'rmsea.notclose.pvalue': nan, 'rmsea.notclose.h0': 0.08, 'rmr': 1.3290420955907656e-16, 'rmr_nomean': 1.5725438145225752e-16, 'srmr': 4.261310602042481e-17, 'srmr_bentler': 4.261310602042481e-17, 'srmr_bentler_nomean': 5.042050700450315e-17, 'crmr': 8.233634315563857e-17, 'crmr_nomean': 1.0629576194313574e-16, 'srmr_mplus': 6.401670237871737e-17, 'srmr_mplus_nomean': 7.368340834761536e-17, 'cn_05': 1.0, 'cn_01': 1.0, 'gfi': 1.0, 'agfi': 1.0, 'pgfi': 0.0, 'mfi': 0.9999999999999996, 'ecvi': 0.018000000000000887}
{'model.type': 'sem', 'mimic': 'lavaan', 'meanstructure': True, 'int.ov.free': True, 'int.lv.free': False, 'marker.int.zero': False, 'conditional.x': False, 'fixed.x': True, 'orthogonal': False, 'orthogonal.x': False, 'orthogonal.y': False, 'std.lv': False, 'correlation': False, 'effect.coding': '', 'ceq.simple': False, 'parameterization': 'delta', 'auto.fix.first': True, 'auto.fix.single': True, 'auto.var': True, 'auto.cov.lv.x': True, 'auto.cov.y': True, 'auto.th': True, 'auto.delta': True, 'auto.efa': True, 'rotation': 'geomin', 'rotation.se': 'bordered', 'rotation.args': {'orthogonal': False, 'row.weights': 'none', 'std.ov': True, 'geomin.epsilon': 0.001, 'orthomax.gamma': 1.0, 'cf.gamma': 0.0, 'oblimin.gamma': 0.0, 'promax.kappa': 4.0, 'target': [], 'target.mask': [], 'rstarts': 30, 'algorithm': 'gpa', 'reflect': True, 'order.lv.by': 'index', 'gpa.tol': 1e-05, 'tol': 1e-08, 'warn': False, 'verbose': False, 'jac.init.rot': True, 'max.iter': 10000}, 'std.ov': False, 'missing': 'listwise', 'sampling.weights.normalization': 'total', 'samplestats': True, 'sample.cov.rescale': True, 'sample.cov.robust': False, 'sample.icov': True, 'ridge': False, 'ridge.constant': 'default', 'group.label': None, 'group.equal': [], 'group.partial': [], 'group.w.free': False, 'level.label': None, 'estimator': 'ML', 'estimator.orig': 'ML', 'estimator.args': [], 'likelihood': 'normal', 'link': 'default', 'representation': 'LISREL', 'do.fit': True, 'bounds': 'none', 'rstarts': 0, 'se': 'standard', 'test': 'standard', 'information': ['expected', 'expected'], 'h1.information': ['structured', 'structured'], 'observed.information': ['hessian', 'hessian'], 'information.meat': 'first.order', 'h1.information.meat': 'structured', 'omega.information': 'expected', 'omega.h1.information': 'unstructured', 'omega.information.meat': 'first.order', 'omega.h1.information.meat': 'unstructured', 'scaled.test': 'standard', 'ug2.old.approach': False, 'bootstrap': 1000, 'gamma.n.minus.one': False, 'gamma.unbiased': False, 'control': [], 'optim.method': 'nlminb', 'optim.attempts': 4, 'optim.force.converged': False, 'optim.gradient': 'analytic', 'optim.init_nelder_mead': False, 'optim.var.transform': 'none', 'optim.parscale': 'none', 'optim.partrace': False, 'optim.dx.tol': 0.001, 'optim.bounds': {'lower': [], 'upper': []}, 'em.iter.max': 10000, 'em.fx.tol': 1e-08, 'em.dx.tol': 0.0001, 'em.zerovar.offset': 0.0001, 'em.h1.iter.max': 500, 'em.h1.tol': 1e-05, 'em.h1.warn': True, 'optim.gn.iter.max': 200, 'optim.gn.stephalf.max': 10, 'optim.gn.tol.x': 1e-05, 'integration.ngh': 21, 'parallel': 'no', 'ncpus': 7, 'cl': None, 'iseed': None, 'zero.add': [0.5, 0.0], 'zero.keep.margins': True, 'zero.cell.warn': False, 'cat.wls.w': True, 'start': 'default', 'check.start': True, 'check.post': True, 'check.gradient': True, 'check.vcov': True, 'check.lv.names': True, 'check.lv.interaction': True, 'h1': True, 'baseline': True, 'baseline.conditional.x.free.slopes': True, 'implied': True, 'loglik': True, 'store.vcov': 'default', 'parser': 'new', 'categorical': False, '.categorical': False, '.clustered': False, '.multilevel': False}
```
