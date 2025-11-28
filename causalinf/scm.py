from . import utils as ut
from . import gcm
from .models import lsem
# 
import tidypolars4sci as tp
from collections import defaultdict

__all__ = ['estimate']

class estimate:
    """
    Structural Equation Model (SCM) estimation of Graphical Causal Models (GCM).

    Parameters
    ----------
    G : gcm.DAG
        Causal graph describing relationships among observed and latent
        variables created by ``causalinf.gcm.DAG``.

    model: str
        Models for the functions of the structural causal model.

        * "auto" : use LSEM (default)
        * "LSEM": Estimate (parametric) generalized linear structural equation models. 
        * "NPSEM-IE-BART: Estimate nonparametric structural equation
                    models with independent errors using BART. 
        * "NPSEM-IE-GAM: Estimate nonparametric structural equation
                    models with independent errors using GAM. 

    formula : str or None, optional
        Formula for the functional form of the SCM. The formula depends on the
        model used and defined by the argument ``model``.
        If ``None`` it creates a formula automatically based on the
        ``model`` used. Auto-generated formulas do not include interactions
        between variables in the DAG. 
        If ``model='auto'``, 
        the formula generated includes definitions for direct, indirect,
        and total effect parameters whenever exposure/outcome roles are defined
        in the DAG object provided to the ``G`` argument. To provide custom formulas:

        * If ``model='LSEM'`` or ``model='auto'``: Use the formula format as used for the ``sem()`` function of R's lavaan.
          For additional model-specific documentation, see ``causalinf.models.lsem``.
        * If ``model='NPSEM-IE-BART'``:  TBD
          For additional model-specific documentation, see ``causalinf.models.bart``.
        * If ``model='NPSEM-IE-GAM'``:  TBD
          For additional model-specific documentation, see ``causalinf.models.gam``.

    data : DataFrame-like
        Observational dataset containing all variables referenced by the DAG or
        formula. 

    family : str, optional
        Outcome distribution family. Defaults to ``'auto'``, in which
        case the family is infered from the type of outcome in the data.
    se_cluster : str
        Name of the variable to cluster the std. errors. 
    se : str or None
        Options available depend on the ``model`` used. See comments in
        ``formula`` to find model-specific documentation and model-specific
        options for ``se``. See also ``Notes`` below.
    model_kws : dict, optional
        Additional keyword arguments for the model defined in ``model``.
        The accepted arguments for each respective ``model`` are those accepted
        by the function described in ``formula``. See also ``Notes`` below.
    weights : str or array-like, optional
        Observation weights passed through to the estimator. Defaults to
        ``1`` (equal weights).
    *args :
        Additional positional arguments forwarded to the underlying estimator.
    **kws :
        Additional keyword arguments forwarded to the underlying estimator.


    Notes
    -----
    For documentation of model-specific arguments, see:

    * LSEM: '``causalinf.models.lsem``'
    * NPSEM-IE-BART: '``causalinf.models.bart``'
    * NPSEM-IE-GAM: '``causalinf.models.gam``'

    Attributes
    ----------
    G : gcm.DAG
        Original DAG used in the estimation.
    formula : str
        SEM specification employed during fitting.
    fit : object
        Raw estimator output (e.g., lavaan fit object) when available.
    est : dict
        Summary bundle returned by the selected estimator, including parameter
        tables, fit statistics, and option metadata.

    Examples
    --------
    >>> dag = gcm.DAG("X -> Y")
    >>> data = tp.tibble({'X': [0, 1, 0], 'Y': [1.0, 2.5, 1.2]})
    >>> est = estimate(G=dag, data=data, silent=True)
    >>> est.est['fit']['N_obs']
    3
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
        # """
        # edges    : list of (u, v) directed edges
        # exposure, outcome : compute indirect paths from exposure to outcome
        # parameter_fmt: how to name each coefficient (e.g., 'beta_{u}.{v}' or '(beta_{u}.{v})')
        # returns  : list of (path_nodes, effect_str)
        # """
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
               
