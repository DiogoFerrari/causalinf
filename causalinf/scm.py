from . import utils as ut
from . import gcm
from .models import lsem
# 
import tidypolars4sci as tp
from collections import defaultdict

__all__ = ['estimate']

class estimate:
    """
    Estimate a structural causal model.


    formula : str or None (optional)
        A structural equation model
           Ex: y ~ d + x1 + z1
               x2 ~ z1 + z2
        where y, d, Z's, and X's are variables in the data

    model: str
        Used only if formula is not provided
        'auto' : use LSEM
        'LSEM': use linear structural equation models. 
        'GLSEM': use generalied linear structural equation models
        'NPSEM': uses nonparametric structural equation estimation
                 In this case, it uses GAM.
    
    se_cluster : str
        Name of the variable to cluster the std. errors. 

    se : str or None
       See the documentation of the specific model used. Example:
       causalinf.models.lsem (for LSEM)

    Specific models
    ---------------
    For documentation of model-specific arguments, see models. Example:
    - causalinf.models.lsem (for LSEM)
    """
    def __init__(self,
                 G,
                 formula=None,
                 data=None,
                 model='auto',
                 family = 'auto',
                 se_cluster=None,
                 se=None,
                 # 
                 model_kws={},
                 sem=None,
                 # 
                 weights=1,
                 *args,
                 **kws
                 ):
        assert data is not None, 'Data must be provided.'
        data = ut.data2tibble(data)
        self.model = "LSEM" if model=='auto' else model
        self.formula = formula or self._graph2sem(G)
        self.family = family
        # 
        self.G = G
        self.outcome = G.outcome[0]
        self.exposure =G.exposure
        #
        self.se_cluster = se_cluster
        self.se = se

        if self.model in 'LSEM':
            self._lsem(G, data=data, weights=weights, *args, **kws)

    @ut.copy_docstring(lsem)
    def _lsem(self, G, data, weights, *args, **kws):
        est =  lsem(formula=self.formula,
                    data=data,
                    weights=weights,
                    se=self.se,
                    se_cluster=self.se_cluster,
                    *args, **kws)
        self.fit = est.fit
        self.est = est.est

    @property
    def causalinf(self):
        print(self)
        
    @ut.copy_docstring(ut.summary)
    def summary(self, *args, **kws):
        formula = ("\n" + self.formula).replace('\n', '\n        ')
        kws |= {'formula': kws.get("formula", formula)}

        latex_replace = {"~~": "\\\\leftrightarrow ", "~" : "\\\\leftarrow "}
        kws |= {'latex_replace': kws.get("latex_replace", latex_replace)}
                                              
        res = ut.summary(
            model = self,
            id_strategy='SCM',
            *args, **kws
        )
        return res.res
        
    def get_fit_statsitics(self, stats):
        res = self.est['fit_stats'].get(stats, None)
        if res is None:
            print(f'Statistics {stats} not available.')
        return res

    @ut.copy_docstring(gcm.DAG.plot)
    def plot(self, *args, **kws):
        self.G.plot(estimates=self, *args, **kws)

    def _graph2sem(self, G, parameter_fmt="(beta_{cause}.{effect})"):
        # regression lines
        reg = ''
        for y, pa_y in G.nodes_parents.items():
            pa_y = " + ".join([f"(beta_{v}.{y})*{v}" for v in pa_y])
            reg += f"{y} ~ (beta_0{y})*1 + {pa_y}\n"
        reg = f"# LSEM:\n{reg}"

        # correlations
        corr = "\n".join([f"{n1[0]} ~~ {n2[0]}" for n1, n2 in G.bidirected])
        corr += "\n".join([f"{n1} ~~ {n2}" for n1, n2 in G.undirected])
        if corr:
            corr = f"# Correlations:\n{corr}"

        # indirect effects
        if G.exposure and G.outcome:
            ind = self._graph2sem_indirect_and_total_effects(G, parameter_fmt)
        else:
            ind = ''
        
        sem = f"{reg}{corr}{ind}"
        return sem

    def _graph2sem_indirect_and_total_effects(self, G, parameter_fmt):
        """
        edges    : list of (u, v) directed edges
        exposure, outcome : compute indirect paths from exposure to outcome
        parameter_fmt: how to name each coefficient (e.g., 'beta_{u}.{v}' or '(beta_{u}.{v})')
        returns  : list of (path_nodes, effect_str)
        """
        # build adjacency
        edges = G.directed
        exposure = G.exposure[0]
        outcome = G.outcome[0]

        adj = defaultdict(list)
        for u, v in edges:
            adj[u].append(v)

        dir_effect = []
        tot_effect = []
        ind_effects = []

        # direct effect
        if outcome in adj[exposure]:
            dir_effect = parameter_fmt.format(cause=exposure, effect=outcome)

        # enumerate simple paths (DFS) recursive function
        def dfs(node, visited, path):
            if node == outcome and len(path) >= 3:  # indirect: at least 2 edges
                # build product beta terms for edges along the path
                terms = [parameter_fmt.format(cause=path[i], effect=path[i+1]) for i in range(len(path)-1)]
                ind_effects.append( (path[:], " * ".join(terms)) )
                return
            for nxt in adj[node]:
                if nxt in visited:       # avoid cycles
                    continue
                visited.add(nxt)
                path.append(nxt)
                dfs(nxt, visited, path)
                path.pop()
                visited.remove(nxt)
        # this wil fill in the info and save it in the variable ind_effects
        dfs(exposure, {exposure}, [exposure])

        res = ''
        ind_effect_str = ''
        if ind_effects:
            for i, ind in enumerate(ind_effects):
                parameter = f"Indirect_effect_{i+1}" # f"beta_{'.'.join(ind[0])}"
                ind_effect_str += f"{parameter} := {ind[1]}\n"
                tot_effect += [parameter]
            res += f"# Indirect effects:\n{ind_effect_str}"
        if dir_effect:
            parameter = "Direct_effect"
            res += f"# Direct effect:\n{parameter} := {dir_effect}"
            tot_effect += [parameter]
        if tot_effect:
            res += f"\n# Total effect:\nTotal_effect := {' + '.join(tot_effect)}"

        return res

    def __repr__(self):
        self.summary(style="full")
        return ''
               
