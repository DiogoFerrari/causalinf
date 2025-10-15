from . import utils as ut
from .models import glm
from .options import get_options
# 
import tidypolars4sci as tp
from textwrap import dedent

MODELS = ['GLM']
GLM_FAMILY = ['auto', 'gaussian']

class estimate:
    """
    model : (str, default: GLM)
        Statistical model to use.
        Available models: check soo.MODELS

    family : (str, default: gaussian)
        Used when GLMs are used. It is the distribution family of the outcome variable
        Available: check soo.GLM_FAMILY
        Option 'auto' automatically guess the family based on the type of the
        outcome variable.
        Logistic models are used when family='binary' or family='auto' and the
        outcome is binary. To use *Linear probability models* (LPMs), set
        family='gaussian' with binary outcomes.
    """

    def __init__(self,
                 formula=None,
                 data=None,
                 model='GLM',
                 family='auto',
                 outcome=None,
                 exposure=None,
                 adjustments=None,
                 se_cluster=None,
                 se_robust=None,
                 weights=1,
                 *args,
                 **kws):
        assert formula or (exposure and outcome), (
            "Either 'formula' or both 'exposure' and 'outcome' must be provided.")
        assert data is not None, "'data' must be provided."

        self.formula = formula
        self.formula_parsed = ut.parse_formula(formula) if formula else formula
        self.exposure = exposure 
        self.outcome = outcome or self.formula_parsed['lhs']

        self.model = model
        self.family = family
        self.se_cluster = se_cluster
        self.se_robust = se_robust

        self._estimate(data=data)

    def __repr__(self):
        self.summary()
        return ""
        
    def summary(self, print_fit_stats=None, *args, **kws):

        if print_fit_stats is None:
            print_fit_stats = get_options()["print_fit_stats"]

        line = "="*80
        print(dedent(f"""
        {line}
        Identification strategy: SoO
        Exposure: {', '.join(self.exposure or 'Not set')}
        Outcome: {self.outcome}
        Formula: {self.formula}

        Summary:
        --------\
        """))
        ut.printDF(self.res['tidy'].to_pandas())
        if print_fit_stats:
            print(dedent("""
            Fit statistics:
            ---------------\
            """))
            for stat, value in self.res['fit_stats'].items():
                value = f"{value:.4f}" if isinstance(value, float) else value
                print(dedent(f"""\
                {stat}: {value}\
                """))
        print(line)
        print(self.res['se']['description'])
        return None
    
    def _estimate(self, data):
        if self.family=='gaussian':
            self.fit = glm.estimate_gaussian(formula=self.formula,
                                             data=data,
                                             se_robust=self.se_robust,
                                             se_cluster=self.se_cluster)
            self.res = glm.estimate_gaussian_summarize(self.fit)

    def get_data(self):
        dep_values = self.fit.model.endog
        dep_name = self.fit.model.endog_names

        indep_values = self.fit.model.exog
        indep_names = self.fit.model.exog_names

        df = tp.tibble(indep_values)
        names = {old:new for old, new in zip(df.names, indep_names)}
        df = df.rename(names).mutate(**{dep_name : dep_values}).drop('Intercept')

        return df

