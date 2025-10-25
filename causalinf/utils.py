from . import utils as ut
# 
import re, os
import numpy as np
import pandas as pd
import polars as pl
import tidypolars4sci as tp
from tools4sci import formulas
from textwrap import dedent
import textwrap 
# 
from .options import get_options


def parse_formula(formula):
    return formulas.extract_variables(formula)

def get_stars(pvalue=None, sig_levels=None, outcome='symbols', latex=False):
    # """
    # Returns the key corresponding to the smallest value in the sig_levels 
    # dictionary larger than each p-value.

    # Parameters
    # ----------
    # pvalues : float
    #     A p-value between 0 and 1.
    # sig_levels : dict
    #     A dictionary mapping symbols to significance levels.
    #     If None, it uses {"***":0.001, "**":0.01, "*":0.05, "+":0.1} 
    # outcome : str
    #     'symbols' returns the corresponding symbols; 'codes' returns
    #     the p-value and their symbol codes
    # latex: bool
    #     Used when outcome='codes'. If True, returns letex-friendly
    #     text

    # Returns
    # -------
    # list
    #     A symbol corresponding to the significance of the p-value.
    # """
    if sig_levels is None: 
        sig_levels = {"***":0.001, "**":0.01, "*":0.05, "+":0.1} 
    sorted_levels = sorted(sig_levels.values())

    if outcome=='codes':
        if not latex:
            res =  "; ".join([f"{star} p<{pvalue}" for star, pvalue in sig_levels.items()])
        else:
            res =  "; ".join([f"{star} $p<{pvalue}$" for star, pvalue in sig_levels.items()])
    else:
        pvalue = pvalue[0]
        if pvalue is not None:
            # Find the index of the smallest level greater than the p-value
            index = np.searchsorted(sorted_levels, pvalue)

            if index == len(sorted_levels):
                symbol = " "  # No symbol if p-value exceeds all levels
            else:
                symbol = next(key for key, value in sig_levels.items() 
                              if value == sorted_levels[index])
        else:
            symbol = ' '
        res = symbol
    return res

def detect_variable_type(data, variables=None, ncats_threshold=5) -> dict:
    # """
    # Classifies all columns in a Polars DataFrame.

    # Args:
    #     data: The input Polars DataFrame.
    #     variables : name of the variables to detect type

    # Returns:
    #     A dictionary mapping column names to their classified types.
    # """
    cols = variables or df.columns
    cols = [cols] if isinstance(cols, str) else cols
    df = data.to_polars()
    classifications = {
        col: detect_variable_type_ancillary(df[col], ncats_threshold=ncats_threshold)
        for col in cols
    }
    return classifications

def detect_variable_type_ancillary(s: pl.Series, ncats_threshold: int = 5) -> str:
    # Create a non-null version of the series to work with

    if s.dtype == pl.Object:
        s = s.map_elements(lambda x: str(x), return_dtype=pl.Utf8)
    s = s.drop_nulls()
    
    # 1. Check for Ordered Categorical type first
    if isinstance(s.dtype, pl.Enum):# and s.dtype.is_ordered():
        return 'ordinal'
    
    # 2. Check for binary columns
    # This captures booleans and any column with exactly two unique values.
    if s.n_unique() == 2:
        return 'binary'
    
    # 3. Check for other categorical types
    # Explicit categoricals, all strings, or integers with few unique values.
    if (
        isinstance(s.dtype, pl.Categorical) or
        s.dtype == pl.Utf8
        # or (s.dtype in pl.INTEGER_DTYPES and s.n_unique() <= ncats_threshold)
    ):
        return 'categorical'
        
    # 4. Check for continuous types
    # Floats or integers that were not caught by the categorical rule above.
    if s.dtype in pl.FLOAT_DTYPES or s.dtype in pl.INTEGER_DTYPES:
        return 'continuous'
        
    return 'unknown'

def get_family(data, outcome):
    outcome_type = _detect_variable_type(data, outcome)[outcome]
    if outcome_type == 'binary':
        family = 'logit'
    elif outcome_type == 'categorical':
        family = 'multinomial'
    elif outcome_type == 'ordinal':
        family = 'probit'
    elif outcome_type == 'continuous':
        family = 'gaussian'
    return family

def data2tibble(data):
    # """
    # Detects if the input data is a pandas, polars, or tidypolars DataFrame.

    # Args:
    #     data: The input dataset to check.

    # Returns:
    #     A string indicating the type: "pandas", "polars", "tidypolars", or "unknown".
    # """
    # The check for Tibble must come before polars.DataFrame
    # because tidypolars.Tibble inherits from polars.DataFrame.
    if isinstance(data, tp.tibble):
        return data
    elif isinstance(data, pl.DataFrame):
        return tp.from_polars(data)
    elif isinstance(data, pd.DataFrame):
        return tp.from_pandas(data)
    else:
        raise('Dataset format unrecognized.')
    
def compute_rmse(residuals=None, y_true=None, y_pred=None):
    # """
    # Compute Root Mean Squared Error (RMSE) from either residuals or (y_true, y_pred).

    # Parameters
    # ----------
    # residuals : array-like, optional
    #     Residuals (y_true - y_pred). If provided, takes precedence.
    # y_true : array-like, optional
    #     True outcome values.
    # y_pred : array-like, optional
    #     Predicted outcome values.

    # Returns
    # -------
    # float
    #     RMSE value.

    # Raises
    # ------
    # ValueError
    #     If neither residuals nor (y_true and y_pred) are provided.
    # """
    if residuals is not None:
        residuals = np.asarray(residuals)
    elif y_true is not None and y_pred is not None:
        y_true = np.asarray(y_true)
        y_pred = np.asarray(y_pred)
        residuals = y_true - y_pred
    else:
        raise ValueError("Provide either residuals or both y_true and y_pred.")

    mse = np.mean(residuals ** 2)
    rmse = np.sqrt(mse)
    return rmse

def printDF(tab, rows=1000, cols=1000, col_width=1000):
    if isinstance(tab, pl.DataFrame):
        with pl.Config(tbl_rows=rows,
                       tbl_cols=cols,
                       tbl_hide_dataframe_shape=True,
                       tbl_hide_column_data_types=True,
                       tbl_width_chars=1000,
                       fmt_str_lengths=col_width,
                       tbl_formatting='NOTHING'
                       ):
            print(tab)
    elif isinstance(tab, pd.DataFrame):
        with pd.option_context('display.max_rows', None, 'display.max_columns', None):  
            print(tab)
    elif isinstance(tab, tp.tibble_df.tibble):
        tab.print()

def copy_docstring(from_func):
    def decorator(to_func):
        to_func.__doc__ = from_func.__doc__
        return to_func
    return decorator

def invert_dict(input_dict):
    inverted = {}
    for key, value in input_dict.items():
        if value not in inverted:
            inverted[value] = []
        inverted[value].append(key)
    return inverted

class summary:
    """
    model (causalinf.<strategy>.estimate)
        An estimate object from causalinf

    compare (dict or list)
        A list of dict of other causalinf estimate objects. The
        estimates will be shown in different columns.
        If a dictionary is used, the keys will be used as the column names.
        For the column name of the object calling the summary, use
        'model_name'.
        If a list is provided, names will be set to "Model 1", "Model 2", etc.

    output (str)
        Format of the output:
        - 'text': returns None and print summary
        - 'tibble': returns a tibble
        - 'latex': returns a latex table
        To save the file, use 'fn'. The output and the saved version
        Are independent. For instance, it is possible to print the
        summary (text) and at the same time save it in latex using
        fn.

    model_name (str)
        Name of the column showing the estimates when output is
        'tibble' of latex. 

    style (str)
        If style='concise', the summary table returns only
        - The parameter name ('term')
        - The confidence interval (if show_ci=True) and the std.errors
          (if show_se=True) and the p-value indicator (if show_sig=True)
        If style='full', the summary table includes all estimation
        statsitics available.
        Defaults:
        - 'full' when compare=None and output='text'
        - 'concise' otherwise

    omit (str)
        A regular expression to match elements in the column terms.
        Matched cases will be omitted.

    save_style  (str)
       Same as 'style', but to save the summary in a files based on
       'fn' and 'save_copies'

    fn (str)
        Path with the filename to save the output in a file. Relative
        paths are alowed. It automatically save the type of output
        based on the filnename extension (tex, xlsx, xls, csv). Copies
        are saved based on 'save_copies'.

    save_copies (list)
        List of strings with the extensions to save copies of the output
        table in the format of the extensions provided. Available are
        xls, xlsx, and csv.
        If None, it will not save copies of the output.
    

    show_fit (bool or list)
        If False, omit fit statistics; If True, shows the stats listed in
        causalinf.estimate.est.fit; else, shows the statistics
        included in the list provided

    show_sig, show_se, show_ci (bool)
        When comparing models, show_* can be used to set which information
        such as standard errors (se), confidence intervals (ci),
        significance level indicators (sig), whenever available,
        appears alongside the parameter estimates. This is ignored
        when output='text' and compare='None'

    digits, digits_fit: (int)
        Digits to show in the estimates and fit statistics, respectively.

    col_width: int
        Length of the column widths in the printed summary

    latex_kws :
        Keywords from tibble.to_latex()

    """

    def __init__(self,
                 model=None,
                 model_name = 'Model 1',
                 compare=None,
                 output = 'text',
                 style = None,
                 omit = None,
                 show_sig = True,
                 show_se =  False,
                 show_ci =  True,
                 show_fit = True,
                 digits = 4,
                 digits_fit = 2,
                 col_width = 1000,
                 col_width_term = 20,
                 # latex args
                 latex_kws=None,
                 fn = None,
                 save_style = 'concise', 
                 save_copies = ['csv', 'xlsx'],
                 *args, **kws
                 ):
        # compare = kws.get("compare", None)
        assert isinstance(latex_kws, dict | None), "'latex_kws' must be None or a dict."
        assert isinstance(save_copies, list | None), "'save_copies' must be None or a list of file extensions."

        self.model_name = model_name
        self.output = output
        self.style = style or self.get_style(compare, output)
        self.omit = omit
        self.digits = digits
        self.digits_fit = digits_fit
        self.show_sig=show_sig
        self.show_se=show_se
        self.show_ci=show_ci
        self.show_fit = show_fit # self.show_fit = kws.get("show_fit", True)
        self.latex_kws = latex_kws or {}
        self.fn = fn
        self.save_style = save_style
        self.save_copies = save_copies
        self.col_width = col_width
        self.col_width_term = col_width_term

        self.outcome = model.outcome
        self.exposure = model.exposure

        self.collect_models(model, model_name, compare)
        self.merge_models()
        self.collect_info()

        # # implicit parameters
        self.id_strategy = kws.get("id_strategy", '')
        self.formula = kws.get("formula", '')
        self.latex_replace = kws.get("latex_replace", None) ## for latex only
        self.estimator = model.est.fit['Estimator']
        self.footnote_added = False # used to avoid duplicating footnote entries

        # keep this order
        self._save(fn=self.fn, silent=False)
        self._save_copies()
        self._output(self.style)

    def collect_models(self, model, model_name, compare):
        assert isinstance(compare, list | dict | None), "'compare' must be a list of dict."
        model = {model_name: {'parameters': self.collect_summary_tidy_formatted(model.est.parameters, model_name),
                              'parameters_full': self.collect_summary_tidy(model.est.parameters),
                              'fit':model.est.fit,
                              'fit_tidy':model.est.fit_tidy(colname=model_name, digits=self.digits_fit),
                              'info':model.est.info
                              }}
        if not compare:
            compare = {}
        else:
            if isinstance(compare, list):
                model_number_init = 2
                model_number_end = model_number_init + len(compare) + 2 # 2 b/c col 'term' (+1) and range(2, k)=[2,k-1] (needs +1)
                model_names = [f"Model {i}" for i in range(model_number_init, model_number_end)] 
                compare = {model_name:model for model_name, model in zip(model_names, compare)}

            compare = {model_name:{'parameters':self.collect_summary_tidy_formatted(model.est.parameters, model_name),
                                   'parameters_full': self.collect_summary_tidy(model.est.parameters),
                                   'fit': model.est.fit,
                                   'fit_tidy':model.est.fit_tidy(colname=model_name, digits=self.digits_fit),
                                   'info':model.est.info
                                   } for model_name, model in compare.items()}

        models = model | compare
        self.models = models

    def collect_summary_tidy(self, parameters):
        parameters = (
            parameters
            .mutate(estimate = tp.col('estimate').round(self.digits),
                    se = tp.round('se', self.digits),
                    lo = tp.round('lo', self.digits),
                    hi = tp.round('hi', self.digits),
                    statistic = tp.round('statistic', self.digits),
                    pvalue = tp.round('pvalue', self.digits),
                    # ci = tp.map(['lo', 'hi'], lambda col: f"({col[0]}, {col[1]})")
                    )
        )
        if self.omit:
            parameters = (
                parameters
                .filter(~tp.col("term").str.contains(self.omit))
            )
        return parameters

    def collect_summary_tidy_formatted(self, parameters, model_name):
        cols_unite = ['estimate']
        if self.show_sig:
            cols_unite += ['sig']
        if self.show_se:
            cols_unite += ['se']
        if self.show_ci:
            cols_unite += ['ci']

        parameters = (
            parameters
            .mutate(estimate = tp.col('estimate').round(self.digits),
                    ci = tp.map(['lo', 'hi'], lambda col:
                                f"({col[0]:.{self.digits}}, {col[1]:.{self.digits}})"),
                    se = tp.map(['se'], lambda col: f"({col[0]:.{self.digits}})"))
            .select('term', cols_unite)
            .unite(model_name, cols_unite, sep=' ')
            .mutate(**{model_name : tp.str_replace_all(model_name, '\(', '\n(')})
            .mutate(**{model_name : tp.str_replace_all(model_name, ' \*', '*')}) 
        )

        return parameters

    def merge_models(self):
        concise_parameter = tp.tibble()
        concise_fit_stats = tp.tibble()
        full = tp.tibble()
        for model_name, summary in self.models.items():
            fit_stats = summary['fit_tidy']
            concise_parameter = self.merge_models_concise(concise_parameter, summary['parameters'])
            concise_fit_stats = self.merge_models_concise(concise_fit_stats, fit_stats)
            full = self.merge_models_full(full, summary['parameters_full'], model_name, fit_stats)
        concise = concise_parameter.bind_rows(concise_fit_stats)
        self.merged = {'concise':concise, 'full':full}

    def merge_models_concise(self, base, to_merge):
        if base.nrow>0:
            base = base.full_join(to_merge, on='term', suffix='_right')
            merged = (base
                      .replace_null({'term':'', 'term_right':''})
                      .mutate(term = tp.case_when(tp.col('term')!=tp.col('term_right'),
                                                  tp.col('term')+tp.col('term_right'),
                                                  True, tp.col('term')
                                                  ))
                      .drop('term_right')
                      )
        else:
            merged = to_merge

        return merged

    def merge_models_full(self, base, to_merge, model_name, fit_stats):
        if self.show_fit:
            to_merge = to_merge.mutate(estimate = tp.as_character('estimate'))
            to_merge = to_merge.bind_rows(fit_stats.rename({model_name:'estimate'}))

        cols = to_merge.names
        to_merge = (to_merge
                    .mutate(Id = model_name)
                    .select('Id', cols)
                    )
        merged = base.bind_rows(to_merge)
        return merged

    def collect_info(self):
        info = []
        for model_name, model_info in self.models.items():
            info += [f"{model_name}: {model_info['info']}"]
        self.info = '; '.join(info)
        
    def _output(self, style):
        self.res_latex = self._output_latex(style)
        self.res_tibble = self._output_tibble(style)

        if self.output=='text':
            self.res = None
            self._output_text(style)
        elif self.output=='tibble':
            self.res = self.res_tibble 
        elif self.output=='latex':
            self.res = self.res_latex 
        
    def _output_text(self, style):
        tab = self.merged[style].to_pandas().fillna('--')
        tab = self.merged[style]
        if 'Id' in tab.names:
            if tab.pull('Id').unique().len()==1:
                tab = tab.drop('Id')

        line = "="*80
        print(dedent(f"""
        {line}
        Model: {self.model_name}
        Identification: {self.id_strategy}
        Outcome: {self.outcome}
        Exposure: {', '.join(self.exposure or 'Not set')}
        Formula: {self.formula}
        Summary:
        --------\
        """))
        tab = tab.mutate(term = tp.map(['term'], lambda col: [*col][0][:self.col_width_term]))
        printDF(tab.to_polars().with_columns(pl.all().cast(pl.Utf8)).fill_null('--'),
                col_width=self.col_width)
        print(line)
        print(get_stars(outcome='codes'))
        if self.info is not None:
            print(textwrap.fill(self.info, 80) )

        return ''

    def _output_tibble(self, style):
        return  self.merged[style]

    def _output_latex(self, style, *args, **kws):
        tab = self.merged[style]
        latex_kws = self.latex_kws

        footnotes = latex_kws.get("footnotes", {'l':[]})
        for align, note in footnotes.items():
            note = note if isinstance(note, list) else [note]
            if align=='l' and not self.footnote_added:
                footnotes[align] =  note + [self.info] + [ut.get_stars(outcome='codes', latex=True)]
            self.footnote_added = True
        latex_kws['footnotes'] = footnotes 

        if not latex_kws.get("align", None):
            ncols = tab.ncol
            latex_kws['align'] = f"l{'c'*(ncols-1)}"

        if self.latex_replace:
            tab = tab.replace({'term':self.latex_replace}, regex=True)
        
        tab = tp.from_polars(tab.to_polars().with_columns(pl.all().cast(pl.Utf8)))
        tab = tab.rename({"term": ' '}).to_latex(**latex_kws)
        return tab

    def get_style(self, compare, output):
        if compare is None and output == 'text':
            res = 'full'
        else:
            res = 'concise'
        return res

    def _save(self, fn, silent=False, *args, **kws):
        excel = ['.xls', '.xlsx']
        if fn:
            self._output(self.save_style)
            _, ext = os.path.splitext(fn)
            fn = os.path.expanduser(fn)

            assert ext, "The file name in 'fn' is missing the extension."

            print(f"Saving summary in {ext} ...", end="") if not silent else None
            if ext=='.tex':
                tab = self.res_latex
                with open(fn , 'w', encoding='utf-8') as file:
                    file.write(tab)

            elif ext in excel:
                tab = self.res_tibble.rename({"term": ' '})
                tab.to_excel(fn)

            elif ext == '.csv':
                tab = self.res_tibble.rename({"term": ' '})
                tab.to_csv(fn)

            print('done!')  if not silent else None

    def _save_copies(self):
        copies = self.save_copies
        if copies and self.fn:
            for ext in copies:
                print(f"Saving copy of summary in .{ext} ...", end="")
                fn, _ = os.path.splitext(self.fn)
                fn = os.path.expanduser(f"{fn}.{ext}")
                self._save(fn=fn, silent=True)
                print('done!')

    def __repr__(self):
        return ''
