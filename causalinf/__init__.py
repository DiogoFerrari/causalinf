

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
