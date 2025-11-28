## Examples

### Estimate LSEM

Take this GCM example:

``` {.python exports="both" results="silent" tangle="src-scm-estimate.py" cache="yes" noweb="no" session="*Python*" linenums="1" eval="always"}
from causalinf import gcm
from causalinf import scm
from causalinf import simulate

G = gcm.examples('Two confounders')
G.plot()
```

![](./tables-and-figures/gcm-lsem-example.png)

Simulate a data from a LSEM based on that DAG:

``` {.python exports="both" results="output code" tangle="src-scm-estimate.py" cache="yes" noweb="no" session="*Python*" linenums="1" eval="always"}
sim = simulate.lsem(G, seed=10)
df = sim.data
df.head().print()
```

``` python
shape: (5, 4)
┌───────────────────────────────┐
│    Z1      Z2       D       Y │
│   f64     f64     f64     f64 │
╞═══════════════════════════════╡
│  1.33    1.51   -2.58    0.50 │
│  0.72   -0.14   -0.42   -1.39 │
│ -1.55   -0.14    1.08   -0.59 │
│ -0.01    1.18   -0.90   -0.47 │
│  0.62    1.18    0.22    0.07 │
└───────────────────────────────┘
```

Estimat the model:

``` {.python exports="both" results="output code" tangle="src-scm-estimate.py" cache="yes" noweb="no" session="*Python*" linenums="1" eval="always"}
res = scm.estimate(G, data=df)
print(res)
```

``` python
Estimating LSEM...done!

================================================================================
Model: Model 1
Identification: SCM
Outcome: Y
Exposure: D
Formula: 
# LSEM:
D ~ (beta_0D)*1 + (beta_Z1.D)*Z1 + (beta_Z2.D)*Z2
Y ~ (beta_0Y)*1 + (beta_D.Y)*D + (beta_Z1.Y)*Z1 + (beta_Z2.Y)*Z2
# Direct effect:
Direct_effect := (beta_D.Y)
# Total effect:
Total_effect := Direct_effect
Summary:
--------        
 term                  label          estimate    sig  se      lo       hi       statistic  pvalue 
 D ~ 1                 beta_0D        0.3129      ***  0.0312  0.2518   0.374    10.0358    0.0    
 D ~ Z1                beta_Z1.D      -0.8867     ***  0.0333  -0.952   -0.8214  -26.6224   0.0    
 D ~ Z2                beta_Z2.D      -0.9231     ***  0.0314  -0.9847  -0.8616  -29.3942   0.0    
 Y ~ 1                 beta_0Y        -0.2967     ***  0.0333  -0.3619  -0.2315  -8.9172    0.0    
 Y ~ D                 beta_D.Y       0.0179           0.0322  -0.0451  0.081    0.5571     0.5775 
 Y ~ Z1                beta_Z1.Y      -0.0581          0.0443  -0.1449  0.0287   -1.312     0.1895 
 Y ~ Z2                beta_Z2.Y      0.1846      ***  0.0436  0.0991   0.2701   4.2314     0.0    
 D ~~ D                               0.9715      ***  0.0434  0.8863   1.0566   22.3607    0.0    
 Y ~~ Y                               1.0054      ***  0.045   0.9173   1.0935   22.3607    0.0    
 Z1 ~~ Z1                             0.8798           0.0     0.8798   0.8798   --         --     
 Z1 ~~ Z2                             0.0632           0.0     0.0632   0.0632   --         --     
 Z2 ~~ Z2                             0.9896           0.0     0.9896   0.9896   --         --     
 Z1 ~ 1                               -0.0146          0.0     -0.0146  -0.0146  --         --     
 Z2 ~ 1                               -0.0111          0.0     -0.0111  -0.0111  --         --     
 Direct_effect := (be  Direct_effect  0.0179           0.0322  -0.0451  0.081    0.5571     0.5775 
 Total_effect := Dire  Total_effect   0.0179           0.0322  -0.0451  0.081    0.5571     0.5775 
 Model                 --             (footnote)  --   --      --       --       --         --     
 Outcome type          --             (footnote)  --   --      --       --       --         --     
 Estimator             --             ML          --   --      --       --       --         --     
 Std.Error             --             classic     --   --      --       --       --         --     
 N.obs                 --             1000        --   --      --       --       --         --     
 RMSE                  --             0.0         --   --      --       --       --         --     
 AIC                   --             5670.18     --   --      --       --       --         --     
 BIC                   --             5714.35     --   --      --       --       --         --     
 DF (model)            --             0           --   --      --       --       --         --     
================================================================================
*** p<0.001; ** p<0.01; * p<0.05; + p<0.1
Model 1: Endogenous variable types: Continuous (D, Y); Models: Linear (D, Y)
```
