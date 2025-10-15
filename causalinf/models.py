from .defaults import FitSummary
from . import utils as ut
# 
import re
import numpy as np
import pandas as pd
import tidypolars4sci as tp
from statsmodels.formula.api import wls as lm
# 
# R packages/dependencies
from rpy2.robjects.vectors import StrVector
from tools4sci.cypher import convert
from rpy2.robjects.packages import importr
from rpy2.robjects import NULL
# 
lavaan = importr("lavaan")

__all__ = ['lsem', 'glm']

class lsem:
    """Interface to estimate linear structural equation models via ``lavaan``.

    Parameters
    ----------
    formula : str
        ``lavaan``-compatible model specification passed to :func:`lavaan.sem`.

    data : tidypolars4sci.tibble
        Dataset providing the observed variables referenced in ``formula``.

    estimator : str
       The name of the estimator to use. 
       If 'auto', it uses maximum likelihood ('ML') if estimating
       models with continuous outcomes an diagonally weighted least squares
       ('DWLS') if there are ordinal endogenous variables.
       For other options, see lavaan lavOptions documentation.

    ordinal : str, list, or None
        Used to indicate binary and ordinal endogenous variables in the data 
        A string (list) must be the name(s) of the binary and ordinal
        endogenous variable(s). If 'auto': (Default), auto-detect the
        type and set the estimator type accordingly (see 'estimator')
        If None, use all variables as continuous.

    ordinal_auto_ncat : int
        When ordinal='auto', variables are classified as ordinal if
        they have 'ordinal_auto_ncat' categories or fewer. 

    se : str, bool, or None
        Specification for classical, robust, or bootstrap standard errors. Options:
        - None: use classical standard errors 
        - "robust.huber.white": standard errors are computed based on the 'mlr'
           (aka pseudo ML, Huber-White) approach.
        - "robust.sem": conventional robust standard errors are computed.
        - "robust": either "robust.sem" or"robust.huber.white" is used
           depending on the estimator, the mimic option, and whether
          the data are complete or not.
        - "boot" or "bootstrap": bootstrap standard errors using
           standard bootstrapping 
        
    se_cluster : str or None
        Column name indicating clustering groups for standard errors. If ``None``
        no clustering is requested.

    weights : any
        Optional weights forwarded to :func:`lavaan.sem`.

    silent: bool
       If False, omit estimation progress messages.

    *args, **kws
        Additional positional and keyword arguments passed to :func:`lavaan.sem`.
    """
    def __init__(self, formula, data,
                 estimator='auto',
                 ordinal='auto',
                 ordinal_auto_ncat=5,
                 se=None,
                 se_cluster=None,
                 weights=None,
                 silent=False, *args, **kws):
        assert kws.get("ordered", None) is None, "Unknown argument: 'ordered'. Do you mean ordinal?"
        assert se_cluster is None or isinstance(se_cluster, str), (
            "'se_cluster 'must be None or a string")
        
        self.formula=formula
        self.ordinal_auto_ncat = ordinal_auto_ncat
        self.get_endogenous_types(data)
        self.get_ordered(ordinal) # run before self.get_estimator()
        self.get_estimator(estimator)
        se = 'standard' if se is None and se_cluster is None else se
        se = 'robust' if se is None and se_cluster is not None else se
        se_cluster = NULL if se_cluster is None else se_cluster

        # estimation
        # ----------
        if not silent:
            print('Estimating LSEM...', end='')
            if se=='bootstrap':
                print('(using bootstrap std. errors; it may take a while)...')
        self.fit = lavaan.sem(formula, data=convert().tp2tibble(data),
                              estimator=self.estimator,
                              ordered=StrVector(self.ordinal) if isinstance(self.ordinal, list) else self.ordinal,
                              se = se,
                              cluster = se_cluster,
                              *args, **kws
                              )
        print('done!') if not silent else None

        # summary 
        # -------
        self.est = self.summarize()

        # check 
        # -----
        self.check_fit()

    def summarize(self, alpha=0.05, *args, **kws):
        parameters = convert().rtibble2tp(lavaan.parameterEstimates(self.fit))
        parameters = (parameters
                      .rename({'est':'estimate',
                               'z':'statistic',
                               'ci.lower':'lo',
                               'ci.upper':'hi'})
                      .mutate(sig = tp.map(['pvalue'], lambda p: ut.get_stars(*[p])))
                      .unite("term", ['lhs', 'op', 'rhs'], sep=' ')
                      .mutate(term = tp.str_replace_all('term', '~1', '~ 1'))
                      .mutate(term = tp.str_trim('term'))
                      )

        options = convert().rlist2dict(lavaan.lavInspect(self.fit, what='options'))

        se = options['se']
        se = 'classic' if se == 'standard' else se

        fit_all = convert().rvec2dict(lavaan.fitMeasures(self.fit))
        fit = fit_all | {
            "Model"       : "(footnote)",
            "Outcome_type": "(footnote)",
            'Estimator'   : options.get("estimator", 'NA'),
            'Std_Error'   : se,
            "N_obs"       : int(lavaan.lavInspect(self.fit, what='nobs')[0]),
            "RMSE"        : fit_all.get("rmsea", None), # average RMSE
            "AIC"         : fit_all.get("aic", None),
            "BIC"         : fit_all.get("bic", None),
            "R2"          : fit_all.get("r2", None),
            "R2_adj"      : fit_all.get("r2.adjust", None),
            "DF_resid"    : None,
            "DF_model"    : int(fit_all['df']),
        }

        res = FitSummary(parameters=parameters,
                         fit=fit,
                         se = {'type':se, 'description': f'Standard errors: {se}'},
                         info = (self.get_info_endo_vartype() + "; "+
                                 self.get_info_models(parameters)),
                         options = options
                         )
        return res

    def check_fit(self):
        se = list(self.est.parameters.pull('se'))
        assert se[0] is not None, (
            "Standard errors not computed."+
            " Try to set se='bootstrap'")

    def get_endogenous_types(self, data):
        formulas = self.formula.split('\n')
        contain_tilda = [bool(re.search(pattern='~', string=s)) for s in formulas]
        formulas = [f for keep, f in zip(contain_tilda, formulas) if keep]

        self.endo = [endo.split('~')[0].strip() for endo in formulas]
        self.endo_types = ut.detect_variable_type(data=data,
                                                  variables=self.endo,
                                                  ncats_threshold=self.ordinal_auto_ncat)
        categorical = [var for var, type in self.endo_types.items()  if type=='categorical']
        assert not len(categorical)>0, (
            "Endogeneous variables must be ordinal, binary, or continuous."+
            f" Categorical variables: {', '.join(categorical)}"
        )

    def get_ordered(self, ordinal):
        if ordinal == 'auto':
            ordinal = [endo for endo, endo_type in self.endo_types.items()
                       if endo_type != 'continuous']
        elif isinstance(ordinal, str):
            ordinal = [ordinal]

        if ordinal is None or len(ordinal)==0:
            ordinal = NULL
            
        self.ordinal = ordinal

    def get_estimator(self, estimator):
        if estimator=='auto':
            if isinstance(self.ordinal, list):
                estimator = 'DWLS'
            elif self.ordinal==NULL:
                estimator = 'ML'
        self.estimator=estimator
            
    def get_info_endo_vartype(self):
        endo_vars = ut.invert_dict(self.endo_types)
        var_types = ', '.join([f"{type.title()} ({', '.join(vars)})" 
                               for type, vars  in endo_vars.items()])
        txt = f"Endogenous variable types: {var_types}"
        return txt
    
    def get_info_models(self, parameters):
        # probit
        dep_output_pattern = {
            'Probit': {"sep"  : " | ",
                       "regex": '\\| ?t[0-9]+$'}, # Y | t1, etc.
            "Linear": { "sep"  : " ~ ", # Y ~ 1
                        'regex': " ~ "}
        }
        #
        models = {}
        for model, pattern in dep_output_pattern.items():
            sep = pattern['sep']
            contains = pattern['regex']
            models[model] = list(
                parameters
                .filter(tp.col("term").str.contains(contains))
                .separate('term', into=['dep', 'indep'], sep=sep)
                .mutate(dep = tp.str_trim('dep'),
                        indep = tp.str_trim('indep'),
                        model = 'Probit',
                        )
                .filter(tp.col("dep").is_in(self.endo_types.keys()))
                .distinct('dep')
                .pull('dep')
            )
        # remove doubled counted as Linear (b/c pattern Y~1 appears also in Probit models)
        models['Linear'] = [v for v in models['Linear'] if v not in models['Probit']]
        txt = [f"{model} ({', '.join(vars)})" for model, vars in models.items() if len(vars)>0]
        txt = f"Models: {', '.join(txt)}"
        return txt
        
class glm:
    """
    family : str 
        Defines the family of the outcome variable distribution for
        'auto', 'gaussian', 'logit', 'multinomial'
        If 'auto', it detects the type of the outcome and
        automatically set the distribution family using:
        - binary: logit
        - categorical: multinomial
        - continuous: gaussian
        For linear probability model, set family='gaussian' with
        binary outcomes
        For LSEM, see causalinf.models.lsem documentation.

    """
    # Regression: Gaussian -----------------------------------------------
    def estimate_gaussian(formula, data, se_cluster=None, se_robust=None,
                          weights=1, *args, **kws):
        """
        Fit a Gaussian linear model (OLS) with optional robust or clustered SEs.

        Parameters
        ----------
        formula : str
            Patsy-style formula, e.g., 'y ~ x1 + x2'.
        data : pandas.DataFrame
            Data containing all variables in the formula.
        se_cluster : str or array-like, optional
            Column name in `data` (or array-like of group IDs) for clustered SEs.
            If provided, cluster-robust SEs are used.
            Ignored if se_robust is provided
        se_robust : None or str, optional (default None)
            String with the the type (HC1, HC2, etc.)

        Returns
        -------
        statsmodels.regression.linear_model.RegressionResultsWrapper
            Fitted model results; call .summary() to view.
        """
        assert se_cluster is None or isinstance(se_cluster, str), (
            "'se_cluster 'must be None or a string")

        # weights
        if isinstance(weights, str):
            assert weights in df.names, f"'weights' ({weights}) not found."
            weights = np.array(df.pull(weights))

        # remove NAs
        variables = ut.parse_formula(formula)
        data = data.select(variables['lhs'], variables['terms'], se_cluster).drop_null().to_pandas()

        # Fit vanilla OLS
        res = lm(formula, data=data, weights=weights)

        # Use heteroskedasticity-robust (HC1)
        if se_robust is not None:
            res = res.fit(cov_type=se_robust)

        # Clustered SE takes precedence if provided
        elif se_cluster is not None:
            if isinstance(se_cluster, str):
                groups = data[se_cluster]
            else:
                groups = np.asarray(se_cluster)
            res = res.fit(cov_type="cluster", cov_kwds={'groups': groups})

        # classic SE
        else:
            res = res.fit()

        # Default: conventional OLS SEs
        return res

    def estimate_gaussian_summarize(model):
        """
        Extract tidy summary results and fit statistics from a statsmodels OLS result.

        Parameters
        ----------
        model : statsmodels.regression.linear_model.RegressionResultsWrapper
            Fitted model object from `estimate_gaussian`.

        Returns
        -------
        dict
            Dictionary with:
            - 'coefficients': tidy table with coef, std err, t, pval
            - 'fit_statistics': R2, Adj R2, AIC, BIC, nobs, df_resid, df_model
        """
        # Coefficients table
        coef_df = model.summary2().tables[1].reset_index()
        coef_df.columns = ["term", "estimate", "se", "t", "pvalue", "lo", "hi"]
        coef_df = tp.tibble(coef_df)

        se_type = model.cov_type
        if se_type=="nonrobust":
            se = 'Classic'
        elif se_type=='cluster':
            se = f"Clustered ({model.cov_kwds['groups'].name})"
        elif bool(re.search(pattern="^H", string=se_type)):
            se = f"Robust"
        se_msg = model.cov_kwds['description']

        # Fit statistics
        fit_stats = {
            'Std.Error': se,
            "N.obs": int(model.nobs),
            "RMSE": ut.compute_rmse(residuals=model.resid),
            "AIC": model.aic,
            "BIC": model.bic,
            "R2": model.rsquared,
            "R2 (adj)": model.rsquared_adj,
            "DF (resid)": int(model.df_resid),
            "DF (model)": int(model.df_model),
        }

        return {
            "tidy": coef_df.select(FIT_STATS_CORE),
            "fit_stats": fit_stats,
            "se": {'type':se, 'description':se_msg},
            'options':{}
        }
