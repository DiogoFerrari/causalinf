import re
import numpy as np

def _parse_formula(formula):
    lhs, rhs = formula.split('~')
    lhs = lhs.strip()
    rhs = rhs.strip()

    # collect terms in the rhs
    all_terms = []
    terms = re.split(r'\s*\+\s*', rhs)
    for term in terms:
        # Split on '*' to get interactions
        interactions = re.split(r'\s*\*\s*', term)
        all_terms.extend(interactions)
    all_terms = list(set(term.strip() for term in all_terms if term.strip()))
    
    # collect interactions
    interactions = []
    terms = rhs.split('+')
    for term in terms:
        if '*' in term:
            interactions.append(term.strip())
    
    return {'lhs':lhs, 'rhs':rhs,
            "interactions":interactions, 'terms':all_terms}

def _get_stars(pvalues, sig_levels=None, outcome='symbols'):
    """
    Returns the key corresponding to the smallest value in the sig_levels 
    dictionary larger than each p-value.

    Parameters
    ----------
    pvalues : list or numpy.ndarray
        A vector of p-values between 0 and 1.
    sig_levels : dict
        A dictionary mapping symbols to significance levels.
        If None, it uses {"***":0.001, "**":0.01, "*":0.05, "+":0.1} 
    outcome : str
        'symbols' returns the corresponding symbols; 'codes' returns
        the p-value and their symbol codes

    Returns
    -------
    list
        A list of symbols corresponding to the significance of each p-value.
    """
    if sig_levels is None: 
        sig_levels = {"***":0.001, "**":0.01, "*":0.05, "+":0.1} 

    sorted_levels = sorted(sig_levels.values())
    symbols = []

    for p_value in pvalues:
        # Find the index of the smallest level greater than the p-value
        index = np.searchsorted(sorted_levels, p_value)

        if index == len(sorted_levels):
            symbol = " "  # No symbol if p-value exceeds all levels
        else:
            symbol = next(key for key, value in sig_levels.items() 
                          if value == sorted_levels[index])
        symbols.append(symbol)

    if outcome=='codes':
        res =  "; ".join([f"{star} p<{pvalue}" for star, pvalue in sig_levels.items()])
    else:
        res = symbols
    return res

