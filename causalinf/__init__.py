

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
    'synthetic_data',
    'utils',
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

# options
from .options import (
    Options, get_options, set_options, reset_options, option_context
)
