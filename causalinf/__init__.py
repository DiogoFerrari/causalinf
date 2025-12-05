

__all__ = [
    'experiment',
    # 
    'gcm',
    'scm',
    'cbn',
    'soo',
    'did',
    'rd',
    'iv',
    # 
    'simulate',
    # 'utils',
]

__all_labels__ = {
    'experiment': "Experimental Design (ED)",  
    'gcm': "Graphical Causal Models (GCM)",  
    'scm': "Structural Causal Models (SCM)",  
    'cbn': "Causal Bayesian Networks (CBN)",  
    'soo': "Selection on Observables (SoO)",  
    'did': "Difference-in-Differences (DiD)",  
    'rd': "Regression Discontinuity (RD)",  
    'iv': "Instrumental Variable (IV)",
}


__description__ = {
    'experiment': ("Methods to estimate a variety of causal effect parameters " +
                   "for experimental studies: " +
                   "Average Causal Effects (ACE), Average Conditional Causal Effects (ACCE) " +
                   "Average Causal Mediation Effects (ACME), Average Marginal Component Effect (AMCE) " +
                   "among many others. Parametric models are available for all parameters, and " +
                   "non-parametric models are available for some parameters."
                   ),
    
    'gcm': ("Methods to construct, analyze, and visualize Causal Graphical Models (GCM). " +
            "Tools to access assumptions are provided."),
    
    'scm': ("Methods to estimate causal effects with GCM using Structural Causal Models (SCM). " +
            "Parametric and non-parametric models are available."),
    
    'cbn': ("Methods to estimate causal effects with GCM using Causal Bayesian Networks (CBN). " +
            "Parametric and kernel models are available."),
    
    'soo': ("Methods to estimate causal effects using Selection on Observables (SoO). " +
            "Parametric and non-parametric models are available."),  

    'iv': ("Methods to estimate causal effects using Instrumental Variables (IV). " +
            "Estimation for many settings is available, including single or multiple IVs, " +
            "and others. " +
            "Tools to access assumptions are provided. " +
            "Parametric and non-parametric models are available."),
    
    'did': ("Methods to estimate causal effects using Difference-in-Differences (DiD). " +
            "Estimation for many settings is available, including classic 2-groups-2-periods " +
            "models and staggered DiD. " +
            "Tools to access assumptions are provided. " +
            "Parametric and non-parametric models are available."),
    
    'rd': ("Methods to estimate causal effects using Regression Discontinuity (RD). " +
            "Estimation for many settings is available, including sharp RD, fuzzy RD, " +
            "and others. " +
            "Tools to access assumptions are provided. " +
            "Parametric and non-parametric models are available."),  
}


API_labels = __all_labels__ | {
    # 'experiment': "Experimental Design (ED)",  
    # 'gcm'       : "Graphical Causal Models",  
    # 'scm'       : "Structural Causal Models",  
    # 'cbn'       : "Causal Bayesian Networks (CBN)",  
    # 'soo'       : "Selection on Observables (SoO)",  
    # 'did'       : "Difference-in-Differences (DiD)",  
    # 'rd'        : "Regression Discontinuity (RD)",  
    # 'iv'        : "Instrumental Variable (IV)",
    'models'    : "Models",
    'utils'     : 'Utils',
    'simulate'  : 'Simulate Data',
}

# options
from .options import (
    Options, get_options, set_options, reset_options, option_context
)
