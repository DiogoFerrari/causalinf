import re
from typing import Iterable, Optional, Union, Dict, Any
import pandas as pd
import numpy as np

class estimate:
    """
    Estimate p(Y=y | do(D=d)) (or E[Y | do(D=d)] when Y is binary in {0,1})
    from a user-supplied adjustment formula string of the form:

        p(Y | do(D)) = sum_{Z1} p(Z1) p(Y | D, Z1)
        p(Y | do(D)) = sum_{Z,X1,X2} p(Z, X1, X2) p(Y | D, Z, X1, X2)

    Parameters
    ----------
    laplace : float, default 0.0
        Additive (Laplace) smoothing for probability estimates. Use a small value
        like 1e-6 if you want minor smoothing; use 1.0 for classic Laplace.
    drop_na : bool, default True
        Drop rows with NA in any variable referenced by the formula.
    """
    _SUM_RE = re.compile(
        r"sum_\{\s*([A-Za-z0-9_,\s]+)\s*\}\s*p\(\s*([A-Za-z0-9_,\s]+)\s*\)\s*p\(\s*Y\s*\|\s*D\s*,\s*([A-Za-z0-9_,\s]+)\s*\)",
        flags=re.IGNORECASE
    )

    def __init__(self, laplace: float = 0.0, drop_na: bool = True):
        self.laplace = float(laplace)
        self.drop_na = bool(drop_na)

    @staticmethod
    def _clean_list(s: str) -> list:
        return [v.strip() for v in s.split(",") if v.strip()]

    def parse(self, formula: str) -> Dict[str, Any]:
        """
        Parse a restricted adjustment formula string. Returns dict with keys:
            'sum_vars' (list), 'joint_vars' (list), 'cond_vars' (list)
        Validates that joint_vars == sum_vars and cond_vars == ['D'] + sum_vars.
        """
        # Normalize spaces
        rhs = formula.split("=")[-1]
        rhs = rhs.replace("\n", " ")
        rhs = re.sub(r"\s+", " ", rhs).strip()

        m = self._SUM_RE.search(rhs)
        if not m:
            raise ValueError(
                "Could not parse RHS. Expected pattern like: "
                "sum_{Z1,...,Zk} p(Z1,...,Zk) p(Y | D, Z1,...,Zk)"
            )
        sum_vars = self._clean_list(m.group(1))
        joint_vars = self._clean_list(m.group(2))
        cond_tail = self._clean_list(m.group(3))

        if joint_vars != sum_vars:
            raise ValueError(f"p(·) joint vars {joint_vars} must match sum_{{·}} vars {sum_vars}.")
        if cond_tail != ["D"] + sum_vars:
            raise ValueError(f"p(Y|·) must have D followed by the sum vars: found {cond_tail}.")

        return {"sum_vars": sum_vars, "joint_vars": joint_vars, "cond_vars": ["D"] + sum_vars}

    def _prep_data(
        self, df: pd.DataFrame, vars_needed: Iterable[str]
    ) -> pd.DataFrame:
        df2 = df.copy()
        missing = [v for v in vars_needed if v not in df2.columns]
        if missing:
            raise KeyError(f"DataFrame missing variables: {missing}")
        if self.drop_na:
            df2 = df2.dropna(subset=list(vars_needed))
        return df2

    def _empirical_joint(self, df: pd.DataFrame, vars_list: list) -> pd.Series:
        """
        Returns Series indexed by tuples of levels for vars_list with probabilities.
        """
        if len(vars_list) == 0:
            return pd.Series([1.0], index=[()], dtype=float)

        counts = df.groupby(vars_list, dropna=False).size()
        if self.laplace > 0:
            # Additive smoothing across the full cartesian product of observed levels
            levels = {v: df[v].astype("category").cat.categories for v in vars_list}
            # Build full index
            multi_index = pd.MultiIndex.from_product(levels.values(), names=vars_list)
            counts = counts.reindex(multi_index, fill_value=0.0)
            counts = counts + self.laplace
            denom = counts.sum()
        else:
            denom = len(df)
        probs = counts / denom
        probs.name = "p_joint"
        return probs

    def _empirical_conditional_y_given_d_z(
        self,
        df: pd.DataFrame,
        y: str,
        d: str,
        d_val: Any,
        z_vars: list,
        y_value: Optional[Any],
    ) -> pd.Series:
        """
        Returns Series over tuples of z_vars with p(Y=y_value | D=d_val, Z=z)
        or E[Y | D=d_val, Z=z] when y is binary numeric and y_value is None.
        """
        use_cols = [y, d] + z_vars
        dfc = df[use_cols].copy()

        # Group by Z for denominators within D=d_val
        mask_d = dfc[d] == d_val
        df_d = dfc[mask_d]

        if len(z_vars) == 0:
            # No Z: return a single scalar as Series indexed by ()
            if y_value is None and pd.api.types.is_numeric_dtype(df_d[y]):
                # mean
                denom = len(df_d)
                if denom == 0:
                    return pd.Series([np.nan], index=[()], dtype=float)
                num = df_d[y].mean()
                return pd.Series([float(num)], index=[()], dtype=float)
            else:
                # categorical prob
                denom = len(df_d)
                if denom == 0:
                    return pd.Series([np.nan], index=[()], dtype=float)
                if self.laplace > 0:
                    # Smoothed: count_y + a / (denom + a*K). K unknown w/out categories; use observed K
                    K = dfc[y].nunique(dropna=True)
                    count_y = (df_d[y] == y_value).sum()
                    p = (count_y + self.laplace) / (denom + self.laplace * K)
                else:
                    p = (df_d[y] == y_value).mean()
                return pd.Series([float(p)], index=[()], dtype=float)

        # With Zs:
        grouped = df_d.groupby(z_vars, dropna=False)

        if y_value is None and pd.api.types.is_numeric_dtype(df_d[y]):
            # mean outcome per Z
            means = grouped[y].mean()
            return means
        else:
            # categorical Y prob per Z
            denom = grouped.size()
            num = grouped.apply(lambda g: (g[y] == y_value).sum())
            if self.laplace > 0:
                # Smoothing per Z cell
                K = dfc[y].nunique(dropna=True)
                p = (num + self.laplace) / (denom + self.laplace * K)
            else:
                with np.errstate(invalid="ignore", divide="ignore"):
                    p = num / denom
            p.name = "p_y_given_dz"
            return p

    def estimate(
        self,
        df: pd.DataFrame,
        formula: str,
        outcome: str,
        treatment: str,
        treatment_value: Union[Any, Iterable[Any], None] = None,
        y_value: Optional[Any] = None,
        return_components: bool = False,
    ) -> Union[Dict[Any, float], float, Dict[str, Any]]:
        """
        Estimate p(Y=y_value | do(D=treatment_value)) or E[Y | do(D=treatment_value)].

        If treatment_value is None, computes results for all observed D values.

        Returns either:
          - scalar (if a single d provided), or
          - dict {d: value} (if d is None or an iterable), or
          - dict with components if return_components=True
        """
        parsed = self.parse(formula)
        sum_vars = parsed["sum_vars"]  # adjustment set Z
        vars_needed = set([outcome, treatment] + sum_vars)
        dfx = self._prep_data(df, vars_needed)

        # Joint p(Z)
        pz = self._empirical_joint(dfx, sum_vars)

        # Which D values?
        if treatment_value is None:
            d_values = list(dfx[treatment].dropna().unique())
        elif isinstance(treatment_value, (list, tuple, set)):
            d_values = list(treatment_value)
        else:
            d_values = [treatment_value]

        results = {}
        components = {}

        # Align conditional and joint on identical MultiIndex (tuples of Z)
        if len(sum_vars) == 0:
            index_target = pd.Index([()], name=None)
        else:
            # Build full index from observed levels of Z in df
            levels = [dfx[z].astype("category").cat.categories for z in sum_vars]
            index_target = pd.MultiIndex.from_product(levels, names=sum_vars)

        pz = pz.reindex(index_target, fill_value=0.0)

        for d_val in d_values:
            py_dz = self._empirical_conditional_y_given_d_z(
                dfx, outcome, treatment, d_val, sum_vars, y_value
            ).reindex(index_target)

            # Weighted sum over Z cells
            val = float((pz * py_dz).sum(skipna=True))
            results[d_val] = val

            if return_components:
                components[d_val] = {
                    "pZ": pz,
                    "pY_given_DZ": py_dz,
                    "cells": pd.DataFrame({"pZ": pz, "pY|DZ": py_dz, "weight": pz * py_dz}),
                }

        if return_components:
            return {"results": results, "components": components, "parsed": parsed}

        # Return scalar if only one d
        if len(results) == 1:
            return list(results.values())[0]
        return results
