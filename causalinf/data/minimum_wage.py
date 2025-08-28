from pathlib import Path
from tidypolars4sci.io import read_data
from tidypolars4sci.tibble_df import tibble

DATA_DIR = Path(__file__).parent

def __load_minimum_wage__():
    mw = read_data(fn=DATA_DIR / "minimum_wage.csv", sep=';', silently=True)

    # documentation
    mw.__codebook__ = codebook()
    mw.__doc__ = f"""
    Card and Krueger (1994) minimum wage data

    ## Description

    Data used by Card and Krueger (1994) about a policy intervention
    that raised the minimum wage was investigated. In 1992, the New
    Jersey (NJ) government increased the minimum wage in the state,
    but the neighboring state Pennsylvania (PA) didn’t adopt that policy.
    The data contain information on fast food restaurants for both
    states in February of 1992, before the policy was adopted in NJ,
    and in November of 1992, after the minimum wage policy was adopted in NJ.

    ## Format

    A data frame with {mw.nrow} observations on {mw.ncol} variables.

    ┌──────────────────────────────────────────────────────────────────┐
    │ Variable      Description                                        │
    │ str           str                                                │
    ╞══════════════════════════════════════════════════════════════════╡
    │ bonus         1 if cash bounty for new workers                   │
    │ chain         chain 1=bk; 2=kfc; 3=roys; 4=wendys                │
    │ co_owned      1 if company owned                                 │
    │ empft         Number of full-time employees                      │
    │ emppt         Number of part-time employees                      │
    │ firstinc      usual amount of first raise ($/hr)                 │
    │ hrsopen       number hrs open per day                            │
    │ inctime       months to usual first raise                        │
    │ meals         free/reduced price code (See below)                │
    │ ncalls        number of call-backs; 0 if contacted on first call │
    │ nmgrs         Number of managers/ass't managers                  │
    │ nregs         number of cash registers in store                  │
    │ nregs11       number of registers open at 11:00 am               │
    │ observation   Period of the measurement                          │
    │ open          hour of opening                                    │
    │ pctaff        % employees affected by new minimum                │
    │ pentree       price of entree, including tax                     │
    │ pfry          price of small fries, including tax                │
    │ psoda         price of medium soda, including tax                │
    │ region        Region of the city                                 │
    │ sheet         sheet number (unique store id)                     │
    │ special       1 if special program for new workers               │
    │ state         1 if NJ; 0 if Pa                                   │
    │ status        status of second interview    : see below          │
    │ type2         type 2nd interview 1=phone; 2=personal             │
    │ wage_st       starting wage ($/hr)                               │
    │ emptot        Total number of employees                          │
    │ pct_fte       % full time employees                              │
    └──────────────────────────────────────────────────────────────────┘

    ## Source

    https://davidcard.berkeley.edu/data_sets.html

    ## References
    
    Card, D., & Krueger, A. B. (1994). Minimum Wages and Employment:
       a Case Study of the Fast-Food Industry in New Jersey and Pennsylvania.
       The American Economic Review, 84(4), 772–793.

    """
    return mw

def codebook():
    variables = {
        "bonus"      : "1 if cash bounty for new workers",
        "chain"      : "Burger King (bk); kfc; roys; wendys",
        "co_owned"   : "1 if company owned",
        "empft"      : "Number of full-time employees",
        "emppt"      : "Number of part-time employees",
        "firstinc"   : "usual amount of first raise ($/hr)",
        "hrsopen"    : "number hrs open per day",
        "inctime"    : "months to usual first raise",
        "meals"      : "free/reduced price code (See below)",
        "ncalls"     : "number of call-backs; 0 if contacted on first call",
        "nmgrs"      : "Number of managers/ass't managers",
        "nregs"      : "number of cash registers in store",
        "nregs11"    : "number of registers open at 11:00 am",
        "observation": "Period: February 1992 or November 1992",
        "open"       : "hour of opening",
        "pctaff"     : "% employees affected by new minimum",
        "pentree"    : "price of entree, including tax",
        "pfry"       : "price of small fries, including tax",
        "psoda"      : "price of medium soda, including tax",
        "region"     : "Region of the city",
        "sheet"      : "sheet number (unique store id)",
        "special"    : "1 if special program for new workers",
        "state"      : "New Jersey or Pennsylvania",
        "status"     : "status of second interview    : see below",
        "type2"      : "type 2nd interview 1=phone; 2=personal",
        "wage_st"    : "starting wage ($/hr)",
        "emptot"     : "Total number of employees",
        "pct_fte"    : "% full time employees"
    }
    codebook = tibble({"Variable": variables.keys(),
                       'Description': variables.values()})
    return codebook
