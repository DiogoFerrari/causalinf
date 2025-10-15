import re, random, numpy as np, tidypolars4sci as tp
import pandas as pd
import networkx as nx

class lsem():
    
    def __init__(self, G, coeffs=None, n=1000, seed=None, noise=1.0, binary=None):
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

        for node in ordering:
            parents = list(G.predecessors(node))
            node_is_binary = node in binary_vars
            noise_scale = e[node]
            if not parents:
                draws = np.random.normal(loc=0, scale=noise_scale, size=n)
                if node_is_binary:
                    logits = np.clip(draws, -709, 709)
                    probs = 1 / (1 + np.exp(-logits))
                    data[node] = np.random.binomial(1, probs)
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
                if node_is_binary:
                    logits = np.clip(signal + noise_term, -709, 709)
                    probs = 1 / (1 + np.exp(-logits))
                    data[node] = np.random.binomial(1, probs)
                else:
                    data[node] = signal + noise_term
                coeffs_dict[node] = {'1': beta0}
                for pa, beta in zip(parents, coeffs):
                    coeffs_dict[node] |= {pa: float(beta)}

        self.data = tp.from_pandas(data)
        self.parameters = coeffs_dict
        self.binary = tuple(sorted(binary_vars))
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
