import tidypolars4sci as tp
from dataclasses import dataclass, field
from typing import Any, Mapping, TypedDict, Optional, Tuple, Iterable, Literal, List


__all__ = ["TIDY_COLS", "FitSummary"]

# Fit statistics 
# --------------
# constants
TIDY_COLS = ["term", 'label', "estimate", 'sig', "se", 'lo', 'hi', "statistic", "pvalue"]

# 1) Schema
class FitDict(TypedDict):
    Model: Optional[str]
    Outcome_type: Optional[str]
    Estimator: Optional[str]
    Std_Error: Optional[str]
    N_obs: Optional[int]
    RMSE: Optional[float]
    AIC: Optional[float]
    BIC: Optional[float]
    R2: Optional[float]
    R2_adj: Optional[float]
    DF_resid: Optional[int]
    DF_model: Optional[int]

class StdErrorDict(TypedDict):
    type: str
    description: str

def fit_defaults() -> FitDict:
    # All required keys present; values start as None
    # Note: cannot go inside the class FitSummary
    return {
        "Model": None,
        'Outcome_type':None,
        "Estimator": None,
        "Std_Error": None,
        "N_obs": None,
        "RMSE": None,
        "AIC": None,
        "BIC": None,
        "R2": None,
        "R2_adj": None,
        "DF_resid": None,
        "DF_model": None,
    }

# 2) Coercion / validation helpers 
# 3) Dataclass
@dataclass
class FitSummary:
    parameters: tp.tibble_df.tibble
    se        : StdErrorDict = field(default_factory=dict)
    fit       : FitDict = field(default_factory=fit_defaults)
    fit_extra : dict[str, Any] = field(default_factory=dict) # automatically filled
    options   : dict[str, Any] = field(default_factory=dict)
    info      : str = ''

    def __post_init__(self) -> None:
        self.parameters = self.parameters_validate()
        coerced, extras = self.fit_normalize()

        self.fit = coerced
        self.fit_extra = {**self.fit_extra, **extras}

    def fit_tidy(self,
                    *,
                    colname = 'estimate',
                    include_none: bool = False,
                    include_extras: bool = False,
                    term_prefix: str = "",
                    extras_prefix: str = "",
                    digits = 2,
                    ) -> tp.tibble_df.tibble:
        """
        Return a two-column tibble with columns: 'term', 'estimate'.

        estimate_dtype:
          - "auto": lets Polars infer (mixed → Utf8)
          - "float": coerce numbers to Float64, drop non-numeric rows
          - "str": stringify everything (Utf8)
        """
        # Collect (term, value) pairs
        items = []
        for k, v in self.fit.items():
            if include_none or v is not None:
                items.append((f"{term_prefix}{k}", v))
        if include_extras:
            for k, v in self.fit_extra.items():
                if include_none or v is not None:
                    items.append((f"{extras_prefix}{k}", v))

        if not items:
            res = tp.tibble({"term": pl.Series([], dtype=pl.Utf8),
                             colname: pl.Series([], dtype=pl.Utf8)})
        else:
            terms, values = zip(*items)
            values = [round(v, digits) if isinstance(v, float) else v for v in values]
            res = tp.tibble({"term": terms,
                             colname: [None if v is None else str(v) for v in values]})
            res = res.replace({"Outcome_type":"Outcome type",
                               'N_obs':"N.obs",
                               'Std_Error':'Std.Error',
                               "R2_adj":'R2 (adj)',
                               'DF_model':'DF (model)',
                               'DF_resid':'DF (resid)',
                               })

        return res

    def fit_normalize(self) -> Tuple[FitDict, dict[str, Any]]:
        """
        Coerce an incoming mapping into the FitDict schema.
        - Ensures all required keys exist (filling with None)
        - Keeps only known keys in `fit` (coerced), unknowns go to `extras`.
        - Does lightweight type coercion where obvious (e.g., ints/floats from strings).
        """
        fit_like = self.fit
        base = fit_defaults()
        extras: dict[str, Any] = {}

        if not fit_like:
            return base, extras

        def coerce(name: str, value: Any) -> Any:
            if value is None:
                return None
            try:
                if name in {"Estimator", "Std_Error"}:
                    return str(value)
                if name in {"N_obs", "DF_resid", "DF_model"}:
                    return int(value)
                if name in {"RMSE", "AIC", "BIC", "R2", "R2_adj"}:
                    return float(value)
            except (TypeError, ValueError):
                # If coercion fails, fall back to None
                return None
            return value

        for k, v in fit_like.items():
            if k in base:
                base[k] = coerce(k, v)
            else:
                extras[k] = v

        return base, extras

    def parameters_validate(self) -> tp.tibble:
        """
        Ensure `tidy` is a Polars DataFrame with required columns.
        - Adds missing required columns with None.
        - Raises if extra columns are present.
        - Casts numeric columns to float.
        """
        df = self.parameters
        if not isinstance(df, (tp.tibble_df.tibble)):
            raise TypeError("`tidy` must be a tibble.")

        # Check for unexpected columns
        extras = [c for c in df.names if c not in TIDY_COLS]
        if extras:
            raise ValueError(f"Unexpected columns in tidy DataFrame: {extras}")

        # Add missing required columns as None (or null)
        for col in TIDY_COLS:
            if col not in df.names:
                df = df.mutate(**{col:None})

        # Reorder columns to canonical order
        df = df.select(TIDY_COLS)

        return df


