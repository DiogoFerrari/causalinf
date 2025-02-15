import polars as pl
from linearmodels.iv import IV2SLS as ivreg
from statsmodels.stats.diagnostic import het_breuschpagan
import scipy.stats as stats
from textwrap import dedent
from tabulate import tabulate
from .utils import (
    _parse_formula,
    _get_stars
)


class estimate():
    
    def __init__(self, stage1, stage2, data,
                 cov_type:str='robust', clusters:list=None):
        """
        Fit instrumental variable (IV) model

        Parameters
        ----------
        formula : str
            A formula that specifies the model.

        Returns
        -------
        IV
            Object of class IV.
        """
        self.__cov_type__ = cov_type
        self.__clusters__ = clusters
        self.__collect_info__(stage1, stage2)
        self.__estimate__(data)
        self.__get_diagnostics__()

    def summary(self):
        """
        Summarize IV estimation 

        Returns
        -------
        None
        """        
        print(self.formula)
        return None

    def formula(self):
        print(dedent(f"""
        Stage 1: {self.__info__['stage1']}
        Stage 2: {self.__info__['stage2']}

        Instrument(s): {" ,".join(self.__info__['exogenous'])}
        Endogenous variable: {self.__info__['endogenous']}
        """))

    def get_diagnostics(self, sig_levels=None):
        bp = pd.DataFrame(self.__diagnostics__['Breusch-Pagan'])
        wh = pd.DataFrame(self.__diagnostics__['Wu-Hausman'])
        sa = pd.DataFrame(self.__diagnostics__['Sargan'])
        wi = pd.DataFrame(self.__diagnostics__['Weak instrument'])
        res = pd.concat([wi.drop('fit', axis=1),
                         wh.drop('fit', axis=1),
                         sa.drop('fit', axis=1),
                         bp.drop('fit', axis=1),
                         ])\
                .filter(['Test', 'H0', 'Statistic', 'Value','p-value'])\
                .assign(sig = lambda p: _get_stars(p['p-value'], sig_levels))
        return pl.from_pandas(res)

    def diagnostics(self, digits=4, sig_levels=None):
        res = self.get_diagnostics().to_pandas()
        # Replace row value with ' ' if it repeats the info in the previous row
        res['Test'] = res['Test'].where(res['Test'].ne(res['Test'].shift()), other=" ")
        res['H0'] = res['H0'].where(res['H0'].ne(res['H0'].shift()), other=" ")
        res = res.rename(columns={'sig':' '})
        print("Diagnostics:")
        print(tabulate(res, headers='keys', tablefmt='simple',
                       showindex=False, floatfmt=f".{digits}f"))
        print("----")
        print(_get_stars([0], outcome='codes', sig_levels=sig_levels))

    def __estimate__(self, data):
        covariance = {'cov_type':self.__cov_type__}
        if self.__clusters__ is not None:
            covariance['clusters'] = data[self.__clusters__]

        stage1 = self.__info__['stage1']
        stage2 = self.__info__['stage2']
        endog  = self.__info__['endogenous']
        formula = stage2.replace(endog, f"1 + [{stage1}]")

        if isinstance(data, pl.DataFrame):
            self.__ivreg__ = ivreg.from_formula(formula, data=data.to_pandas()).fit(**covariance)
        else:
            self.__ivreg__ = ivreg.from_formula(formula, data=data).fit(**covariance)
        
    def __get_diagnostics__(self):
        self.__diagnostic_breusch_pagan__()
        self.__diagnostic_wu_hausman__()
        self.__diagnostic_sargan__()
        # self.__diagnostic_weak_instrument_classic__()
        return None

    def __diagnostic_breusch_pagan__(self):
        residuals = self.__ivreg__.resids
        # endogenous variables
        endo_vars = ", ".join(self.__info__['endogenous'])
        endo_data = self.__ivreg__.model.endog.pandas.assign(Intercept=1)
        bp_test = het_breuschpagan(residuals, endo_data)
        bp_endo = {'Test'     : ['Breusch-Pagan']*2,
                   'H0'       : [f"No heteroskedasticity ({endo_vars})"]*2,
                   'Statistic': ['Lagrange', 'F'],      
                   'Value'    : [bp_test[0] , bp_test[2]],
                   'p-value'  : [bp_test[1] , bp_test[3]],
                   'fit'      : [bp_test, bp_test]
                   }
        # exogenous
        exog_vars = ", ".join(self.__info__['exogenous'])
        exog_data = self.__ivreg__.model.exog.pandas.assign(Intercept=1)
        bp_test = het_breuschpagan(residuals, exog_data)
        bp_exog = {'Test'     : ['Breusch-Pagan']*2,
                   'H0'       : [f"No heteroskedasticity ({exog_vars})"]*2,
                   'Statistic': ['Lagrange', 'F'],      
                   'Value'    : [bp_test[0] , bp_test[2]],
                   'p-value'  : [bp_test[1] , bp_test[3]],
                   'fit'      : [bp_test, bp_test]
                   }
        bp_test = {k: bp_endo[k] + bp_exog[k] for k in bp_endo.keys() & bp_exog.keys()}
        self.__diagnostics__ = {'Breusch-Pagan':bp_test }

    def __diagnostic_wu_hausman__(self):
        res = self.__ivreg__.wu_hausman()
        res = {'Test': 'Wu-Hausman',
               'H0'  : res.null,
               'Statistic': "F",
               'Value':res.stat,
               'p-value':float(res.pval),
               'fit': [res],
               }
        self.__diagnostics__['Wu-Hausman'] = res
    
    def __diagnostic_sargan__(self):
        res = self.__ivreg__.sargan
        res = {'Test': 'Sargan',
               'H0'  : res.null,
               'Statistic': "chisq",
               'Value':res.stat,
               'p-value':float(res.pval),
               'fit':[res]
         }
        self.__diagnostics__['Sargan'] = res

    def __diagnostic_weak_instrument_classic__(self):
        # wrong implementation in linearmodels
        # 
        # f_stat = self.__ivreg__.first_stage.diagnostics['f.stat']
        # df1 = self.__ivreg__.df_model - 2
        # df2 = self.__ivreg__.df_resid - 1
        # pvalue = 1 - stats.f.cdf(f_stat.iloc[0], dfn=df1, dfd=df2)
        # res = {'Test': 'Weak instrument',
        #        'H0'  : 'Instruments are jointly weak',
        #        'Statistic': "F",
        #        'Value':f_stat,
        #        'p-value':float(pvalue),
        #        'fit':[self.__ivreg__.first_stage.diagnostics]
        #        }
        # self.__diagnostics__['Weak instrument'] = res
        pass

    def __repr__(self):
        print(self.__ivreg__)
        return ""
        
    def __collect_info__(self, stage1, stage2):
        info = {}
        info['stage1'] = stage1
        info['stage2'] = stage2
        stage1 = _parse_formula(stage1)
        stage2 = _parse_formula(stage2)
        info['stage1 parsed'] = stage1
        info['stage2 parsed'] = stage2
        info['outcome'] = stage2['lhs']
        info['endogenous'] = stage1['lhs']
        info['instruments'] = info['endogenous']
        info['exogenous'] = list(set(stage1['terms']).difference(set(stage2['terms'])))
        info['adjustments'] = list(set(stage2['terms']).difference(set(stage1['lhs'])))

        self.__info__ = info
        

