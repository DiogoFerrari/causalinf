import re, random, numpy as np, tidypolars4sci as tp
import pandas as pd
import networkx as nx

class LSEM():
    
    def __new__(self, G, coeffs=None, n=1000, seed=None,
                 noise_std=1.0):
        np.random.seed(seed)
        # assert nx.is_directed_acyclic_graph(G.G), "Graph must be a DAG"
        G = G.__create_nx__()

        data = pd.DataFrame(index=range(n))
        ordering = list(nx.topological_sort(G))
        coeffs_dict = {}

        for node in ordering:
            parents = list(G.predecessors(node))
            if not parents:
                data[node] = np.random.normal(loc=0, scale=noise_std, size=n)
                coeffs_dict[node] = {f"beta_{node}": None}
            else:
                # Simple linear model: sum of parents + noise
                coeffs = np.random.uniform(-1, 1, size=len(parents))
                parent_data = data[parents].values
                data[node] = parent_data @ coeffs + np.random.normal(0, noise_std, size=n)
                for pa, beta in zip(parents, coeffs):
                    coeffs_dict[node] = {pa: beta}

        res = [tp.from_pandas(data), coeffs_dict]
        return res


    def __repr__(self, digits=4):
        print(self)

        print("Parameters: ")
        for endo, parents in self.parameters.items():
            hrs = ''
            if list(parents.values())[0] is not None:
                for pa, coef in parents.items():
                    hrs += f"{round(coef, digits)} {pa}"
                print(f"{endo} = {hrs}")
        return ''
