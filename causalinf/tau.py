import re
from textwrap import dedent

__all__ = ["_print2latex",
           "VARIABLES",
           "PARAMETER",
           "IDENTIFICATION",
           ]

def _print2latex(expression, add_alignement_char=False):
    rep_literal = {
        # keep order
        # 
        # LATE-specific
        _LATE('parameter') : "\\displaystyle\\frac{tau_{ZY}(z, z')}{tau_{ZD}(z, z')}",
        _LATE('no adj') : _LATE('no adj'),
        _LATE('adj') : _LATE('adj'),
        'where' : '\\text{where}',
        "for z, z' such that Di(z)=d and Di(z') = d'" : "\\text{for $z, z'$ such that $Di(z)=d$ and $Di(z') = d'$}",
        # 
        'i': '_i',
        "Ex[": '\\mathbb{E}_{X}[',
        'E[': '\\mathbb{E}[',
        '|': '\\mid ',
        '[': '\\left[',
        ']': '\\right]',
        '(': '\\left(',
        ')': '\\right)',
        # 
        'ACE'  : '\\text{ACE}',
        'cACE' : '\\text{cACE}',
        'ACDE' : '\\text{ACDE}',
        'cACDE': '\\text{cACDE}',
        'LATE': '\\text{LATE}',
        # 
        "{IV}": "{\\text{IV}}",
        # 
        'tau'  : '\\tau',
        "Compliers": '\\text{Compliers}',
        "Compl_iers": 'Compliers',
        # 
        "Outcome"                                 : "\\text{Outcome}",
        "Exposure or treatment"                   : "\\text{Exposure or treatment}",
        "Time"                                    : "\\text{Time}",
        "Instrument"                              : "\\text{Instrument}",
        "Controls set by user"                    : "\\text{Controls set by user}",
        "Mediators"                               : "\\text{Mediators}",
        "Adjustments from identification analysis": "\\text{Adjustments from identification analysis}",
        "Assignment Mechanism"                    : "\\text{Assignment Mechanism}",
        "Strata"                                  : "\\text{Strata}",
        #
        # corrections
        "\\m_id"                                   : "\\mid",
        "\\d_isplaystyle"                          : "\\displaystyle",
        "Med_iators"                               : "\\text{Mediators}",
        "T_ime"                                    : "\\text{Time}",
        "Adjustments from _ident_if_icat_ion analys_is": "\\text{Adjustments from identification analysis}",
        "Ass_ignment Mechan_ism"                    : "\\text{Assignment Mechanism}",

    }

    for pattern, rep in rep_literal.items():
        expression = expression.replace(pattern, rep)

    if bool(re.search(pattern='\n', string=expression)):
        expression = f"\\begin{{aligned}}\\displaystyle {expression}\\end{{aligned}}"
        if add_alignement_char:
            expression = re.sub(pattern='\n', repl='\\\\\\\\& ', string=expression)
            expression = re.sub(pattern='\\\\displaystyle', repl='\\\\displaystyle& ', string=expression)
        else:
            expression = re.sub(pattern='\n', repl='\\\\\\\\ ', string=expression)

    expression = f"${expression}$"
    return expression

def _par2id(parameter, strategy):
    return PARAMETER[parameter]['parameter'].replace(f"{{{parameter}}}", f"{{{parameter}}}^{{{strategy}}}")

def _LATE(which):
    if which=='parameter':
        txt = dedent("""\
        tau_{ZY}(z, z')
        ---------------
        tau_{ZD}(z, z')\
        """)
    elif which=='no adj':
        txt = dedent("""\
        where
            tau_{ZY}(z, z') = E[Yi | Zi=z] - E[Yi | Zi=z']
            tau_{ZD}(z, z') = E[Di | Zi=z] - E[Di | Zi=z']
            for z, z' such that Di(z)=d and Di(z') = d'
        """)
    elif which=='adj':
        txt = dedent("""\
        where
            tau_{ZY}(z, z') = Ex[ E[Yi | Zi=z, Xi] ] - Ex[ E[Yi | Zi=z', Xi] ]
            tau_{ZD}(z, z') = Ex[ E[Di | Zi=z, Xi] ] - Ex[ E[Di | Zi=z', Xi] ]
            for z, z' such that Di(z)=d and Di(z') = d'
        """)
    return txt

VARIABLES = {
    'variables' : {
        "Yi" : "Outcome",
        "Di" : "Exposure or treatment", 
        "Ti" : "Time", 
        "Zi" : "Instrument",
        "Ci" : "Controls set by user",
        "Mi" : "Mediators",
        "Xi" : "Adjustments from identification analysis",
        "Wi" : "Assignment Mechanism",
        "Si" : "Strata",
    },
    'values': {
        "y, y'" : 'specific values of Yi',
        "d, d'" : 'specific values of Di',
        "t, t'" : 'specific values of Ti',
        "z, z'" : 'specific values of Zi',
        "c, c'" : 'specific values of Ci',
        "m, m'" : 'specific values of Mi',
        "x, x'" : 'specific values of Xi',
        "w, w'" : 'specific values of Wi',
        "s, s'" : 'specific values of Si',
    }
}

PARAMETER = {
    "ACE" : {
        'name'       : "Average Causal Effect",
        "parameter"  : "tau_{ACE}(d, d')",
        "definition" : "E[Yi(d) - Yi(d')]",
    },
    "cACE" : {
        'name'       : "Conditional Average Causal Effect",
        "parameter"  : "tau_{cACE}(d, d')",
        "definition" : "E[Yi(d) - Yi(d') | Ci]",
    },
    "ACDE" : {
        'name'       : "Average Controlled Direct Effect",
        "parameter"  : "tau_{ACDE}(d, d', m)",
        "definition" : "E[Yi(d, m) - Yi(d', m)]",
    },
    "cACDE" : {
        'name'       : "Conditional Average Controlled Direct Effect",
        "parameter"  : "tau_{cACDE}(d, d', m)",
        "definition" : "E[Yi(d, m) - Yi(d', m) | Ci]",
    },
    "LATE" : {
        'name'       : "Local Average Causal Effect",
        'parameter'  : "tau_{LATE}(d, d')",
        "definition" : "E[Yi(d) - Yi(d') | Si=Compliers]"
    }
}
IDENTIFICATION = {
    "SoO" : {
        'name'  : 'Selection on Observables',
        'identified by': 'Adjustment set',
        'ACE' : {
            'parameter'  : _par2id('ACE', "SoO"),
            False        : "E[Yi | Di=d] - E[Yi | Di=d']",
            True         : "Ex[E[Yi | Di=d, Xi]] - Ex[E[Yi | Di=d', Xi]]",
            'where'      : {False: '', True: ''}
        },
        "cACE" : {
            'parameter'  : _par2id('cACE', "SoO"),
            False        : "E[Yi | Di=d, Ci] - E[Yi | Di=d', Ci]",
            True         : "Ex[E[Yi | Di=d, Ci, Xi]] - Ex[E[Yi | Di=d', Ci, Xi]]",
            'where'      : {False: '', True: ''}
        },
        "ACDE" : {
            'parameter' : _par2id('ACDE', "SoO"),
            False       : "E[Yi | Di=d, Mi=m] - E[Yi | Di=d', Mi=m]",
            True        : "Ex[E[Yi | Di=d, Mi=m, Xi]] - Ex[E[Yi | Di=d', Mi=m, Xi]]",
            'where'     : {False: '', True: ''}
        },
        "cACDE" : {
            'parameter' : _par2id('cACDE', "SoO"),
            False       : "E[Yi | Di=d, Ci, Mi] - E[Yi | Di=d', Ci, Mi]",
            True        : "Ex[E[Yi | Di=d, Ci, Mi, Xi]] - Ex[E[Yi | Di=d', Ci, Mi, Xi]]",
            'where'     : {False: '', True: ''}
        }
    },
    "IV" : {
        'name'         : 'Instrumental Variable',
        'identified by': 'Instrument',
        'ACE' : {
            'parameter' : _par2id('LATE', "IV"),
            False       : _LATE('parameter'),
            True        : _LATE('parameter'),
            'where'     :  {False: _LATE('no adj'), True: _LATE('adj')},
        }
    },
    'do' : {
        'name'  : 'do-calculus',
        'identified by': 'Causal probability',
        'ACE' : {
            'parameter' : _par2id('ACE', "do"),
            False       : "E[Yi | do(Di)=d] - E[Yi | do(Di)=d']",
            True        : "E[Yi | do(Di)=d] - E[Yi | do(Di)=d']",
            'where'     : {False: '', True: ''}
        },
        "cACE" : {
            'parameter' : _par2id('cACE', "do"),
            False       : "E[Yi | do(Di)=d, Ci] - E[Yi | do(Di)=d', Ci]",
            True        : "E[Yi | do(Di)=d, Ci] - E[Yi | do(Di)=d', Ci]",
            'where'     : {False: '', True: ''}
        },
    }
}



