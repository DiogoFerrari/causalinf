import re, random, numpy as np, tidypolars4sci as tp
import pandas as pd
import networkx as nx

class lsem():
    """Linear structural equation model simulator with discrete support options.

    Parameters
    ----------
    G : object
        Graph object exposing ``__graph_list__`` with edges for constructing a
        :class:`networkx.DiGraph`.
    coeffs : dict, optional
        Placeholder for externally supplied coefficients. Currently unused.
    n : int, default 1000
        Number of observations to simulate.
    seed : int, optional
        Random seed passed to :func:`numpy.random.seed`.
    noise : float or dict, default 1.0
        Standard deviation of Gaussian noise. When a dictionary, it must map
        variable names to their respective noise levels; unspecified variables
        default to 1.0.
    binary : str or iterable of str, optional
        Variables that should be simulated as Bernoulli outcomes using a
        logistic transformation of the latent variable.
    ordinal : dict, optional
        Maps variable names to ``[lower, upper]`` integer bounds. Values are
        generated as integers within the inclusive range, ordered by the latent
        Gaussian variable.
    categorical : dict, optional
        Maps variable names to a non-empty list of category labels. Latent
        Gaussian variables are discretised to these categories in the supplied
        order.

    Notes
    -----
    Variables not specified as binary, ordinal, or categorical remain
    continuous and are simulated as Gaussian variables according to the linear
    structural equations defined by the graph.
    """

    def __init__(self, G, coeffs=None, n=1000, seed=None, noise=1.0,
                 binary=None, ordinal=None, categorical=None):
        np.random.seed(seed)

        G = nx.DiGraph(G.__graph_list__)
        variables = list(G.nodes)

        if binary is None:
            binary_vars = set()
        elif isinstance(binary, str):
            binary_vars = {binary}
        elif isinstance(binary, (list, tuple, set)):
            binary_vars = set(binary)
        else:
            raise TypeError("'binary' must be None, a string, or an iterable of strings.")

        if not all(isinstance(v, str) for v in binary_vars):
            raise TypeError("'binary' variable names must be strings.")

        missing = binary_vars - set(variables)
        if missing:
            raise ValueError(f"'binary' variables not found in graph: {missing}.")

        if ordinal is None:
            ordinal_specs = {}
        elif isinstance(ordinal, dict):
            ordinal_specs = {}
            for var, bounds in ordinal.items():
                if not isinstance(var, str):
                    raise TypeError("'ordinal' variable names must be strings.")
                if not isinstance(bounds, (list, tuple)) or len(bounds) != 2:
                    raise ValueError("'ordinal' bounds must be an iterable of two integers.")
                lower, upper = bounds
                if not isinstance(lower, int) or not isinstance(upper, int):
                    raise TypeError("'ordinal' bounds must be integers.")
                if lower > upper:
                    raise ValueError("Lower bound in 'ordinal' must not exceed upper bound.")
                ordinal_specs[var] = list(range(lower, upper + 1))
        else:
            raise TypeError("'ordinal' must be None or a dictionary.")

        missing = set(ordinal_specs) - set(variables)
        if missing:
            raise ValueError(f"'ordinal' variables not found in graph: {missing}.")

        if categorical is None:
            categorical_specs = {}
        elif isinstance(categorical, dict):
            categorical_specs = {}
            for var, categories in categorical.items():
                if not isinstance(var, str):
                    raise TypeError("'categorical' variable names must be strings.")
                if not isinstance(categories, (list, tuple)) or len(categories) == 0:
                    raise ValueError("'categorical' categories must be a non-empty iterable of strings.")
                if not all(isinstance(cat, str) for cat in categories):
                    raise TypeError("All 'categorical' categories must be strings.")
                categorical_specs[var] = list(dict.fromkeys(categories))
        else:
            raise TypeError("'categorical' must be None or a dictionary.")

        missing = set(categorical_specs) - set(variables)
        if missing:
            raise ValueError(f"'categorical' variables not found in graph: {missing}.")

        overlap = binary_vars & set(ordinal_specs)
        if overlap:
            raise ValueError(f"Variables cannot be both binary and ordinal: {overlap}.")

        overlap = binary_vars & set(categorical_specs)
        if overlap:
            raise ValueError(f"Variables cannot be both binary and categorical: {overlap}.")

        overlap = set(ordinal_specs) & set(categorical_specs)
        if overlap:
            raise ValueError(f"Variables cannot be both ordinal and categorical: {overlap}.")

        e = {}
        if not isinstance(noise, dict):
            e = {v:noise for v in variables}
        elif isinstance(noise, dict):
            for v in variables:
                if v not in noise.keys():
                    e[v] = 1.0
                else:
                    e[v] = noise[v]
        else:
            raise("'noise' must be a dict or a number.")
                
        data = pd.DataFrame(index=range(n))
        ordering = list(nx.topological_sort(G))
        coeffs_dict = {}

        def map_latent_to_levels(latent, levels):
            latent = np.asarray(latent)
            num_levels = len(levels)
            if num_levels == 1:
                return np.asarray([levels[0]] * latent.shape[0])
            latent = np.clip(latent, -709, 709)
            scaled = 1 / (1 + np.exp(-latent))
            indices = np.floor(scaled * num_levels).astype(int)
            indices = np.clip(indices, 0, num_levels - 1)
            return np.asarray(levels)[indices]

        var_types = {var: 'continuous' for var in variables}
        for var in binary_vars:
            var_types[var] = 'binary'
        for var in ordinal_specs:
            var_types[var] = 'ordinal'
        for var in categorical_specs:
            var_types[var] = 'categorical'

        for node in ordering:
            parents = list(G.predecessors(node))
            node_type = var_types[node]
            noise_scale = e[node]
            if not parents:
                draws = np.random.normal(loc=0, scale=noise_scale, size=n)
                if node_type == 'binary':
                    logits = np.clip(draws, -709, 709)
                    probs = 1 / (1 + np.exp(-logits))
                    data[node] = np.random.binomial(1, probs)
                elif node_type == 'ordinal':
                    data[node] = map_latent_to_levels(draws, ordinal_specs[node])
                elif node_type == 'categorical':
                    data[node] = map_latent_to_levels(draws, categorical_specs[node])
                else:
                    data[node] = draws
                coeffs_dict[node] = {}
            else:
                # Simple linear model: sum of parents + noise
                coeffs = np.random.uniform(-1, 1, size=len(parents))
                parent_data = data[parents].values
                beta0 = np.random.uniform(-1, 1, size=1)[0]
                signal = beta0 + parent_data @ coeffs
                noise_term = np.random.normal(0, noise_scale, size=n)
                latent = signal + noise_term
                if node_type == 'binary':
                    logits = np.clip(latent, -709, 709)
                    probs = 1 / (1 + np.exp(-logits))
                    data[node] = np.random.binomial(1, probs)
                elif node_type == 'ordinal':
                    data[node] = map_latent_to_levels(latent, ordinal_specs[node])
                elif node_type == 'categorical':
                    data[node] = map_latent_to_levels(latent, categorical_specs[node])
                else:
                    data[node] = latent
                coeffs_dict[node] = {'1': beta0}
                for pa, beta in zip(parents, coeffs):
                    coeffs_dict[node] |= {pa: float(beta)}

        self.data = tp.from_pandas(data)
        self.parameters = coeffs_dict
        self.binary = tuple(sorted(binary_vars))
        self.ordinal = {var: (levels[0], levels[-1]) for var, levels in ordinal_specs.items()}
        self.categorical = {var: tuple(levels) for var, levels in categorical_specs.items()}
        self._parameters_tidy()

    def __repr__(self, digits=4):

        print("Linear Structural Equation Model (LSEM): ")
        for endo, parents in self.parameters.items():
            rhs = []
            if parents:
                for pa, coef in parents.items():
                    if pa=='1':
                        rhs += [f"({round(coef, digits)})"]
                    else:
                        rhs += [f"({round(coef, digits)})*{pa}"]
                rhs = ' + '.join(rhs)
                print(f"{endo} = {rhs}")
        print(self.data)
        return ''

    def _parameters_tidy(self):
        par_tidy = tp.tibble()
        for endo, pa in self.parameters.items():
            if pa:
                for pa_name, pa_value in pa.items():
                    tmp = tp.tibble({'lhs':endo, 'op':"~", 'rhs':pa_name,
                                     'term': f"{endo} ~ {pa_name}",
                                     'true':pa_value})
                    par_tidy = par_tidy.bind_rows(tmp)
        self.parameters_tidy = par_tidy
