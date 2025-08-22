import tidypolars4sci as tp
import networkx as nx
import re, itertools, math, inspect
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from collections import defaultdict
# R packages/dependencies
from tools4sci.cypher import convert
from rpy2.robjects.packages import importr
from rpy2.robjects import NULL
# 
dagitty = importr("dagitty")
dosearch = importr("dosearch")


class DAG():
    
    def __init__(self,
                 graph=None,
                 data=None,
                 # nodes
                 nodes_role=None,
                 nodes_label=None,
                 nodes_position=None,
                 # edges
                 edge_label=None
                 ):
        """
        graph: (str, dict, list)
            A string with the a graph, or a list or dictionary with the edges

            If string, it can have different formats
            Example:
            '''
            X1 -> Y
            X1 -> Z -> Y
            X1 <- X2
            # This is equivalent to directed edges: X3 -> A and X -> B
            # and X4 -> C and X4 -> D
            X3 -> {A, B}
            {C, D} <- X4
            # Bidirected edges (this is a comment, which is also allowed)
            X3 <-> X4
            # Undirected edges 
            X3 -- X4
            # Mixing
            X5 -- X6 -> X7
            '''

             If list, the edge types will be parsed based on their format:
             [
                 ('X', 'Y'),                    # becomes X -> Y  (directed edge)
                 {'X', 'Z'},                    # becomes X -- Y  (undirected edge)
                 (('X1', 'X2'), ('X2', 'X1')),  # becomes X <-> Y (bidirected edge)
             ]

            If dictionary, it must contains the edges as elements and the
            edge type (directed, undirected, bidirected) as keys 
            Example:
            {'directed'  : [('X', 'Y'), ...],  # list of tuples
             'undirected': [{'X1', 'X2'}, ...] # list of dictionaries
             'bidirected': [ (('X1', 'X2'), ('X2', 'X1')), ...] # list of 2-tuple tuples
             }

        SEM: a string with the structural equation model (SEM).
             Parameter and path effects definition are allowed in the
             SEM string. If parameters are provided,
             they are used as 'edge_labels', except if the later is also
             provided. 
             See examples below.
        """
        assert graph, "'graph' must be provided."
        assert nodes_position is None or isinstance(nodes_position, dict), (
            "nodes_position must be None or dict")
        assert nodes_label is None or isinstance(nodes_label, dict), (
            "nodes_label must be None or dict")


        # graph
        self.__graph_list__ = []
        self.__graph_dict__ = {}
        self.__graph_str_original__ = None
        self.__graph_str_parsed__ = None
        self.__dagitty__ = None
        # edges 
        self.__edges_str_allowed__ = ['->', '<-', '<->', "--"]
        self.edge_label = edge_label or {}
        self.directed = []
        self.bidirected = []
        self.undirected = []
        # nodes 
        self.nodes = set()
        self.nodes_parents = {}
        self.exposure = []
        self.outcome = []
        self.latent = []
        self.observed = []
        self.nodes_role = {}
        self.nodes_position = {}
        self.nodes_label = {}
        self.nodes_info = {}
        # keep this order:
        self.__build_graph__(graph)
        self.__collect_info__(nodes_role, nodes_position, nodes_label)
        # dagitty
        self.__create_dagitty__()
        # others
        self.data = data

    # building graph --------------------------------
    def __build_graph__(self, graph):
        # Always convert to dict first, and from dict to other formats
        # dict -> list
        # dict -> str
        # str -> dict -> list
        # list-> dict -> str
        if isinstance(graph, str):
            self.__graph_str_parse__(graph)
            self.__graph_str2dict__()
            self.__graph_dict2list__()
        elif isinstance(graph, dict):
            self.__graph_dict_parse__(graph)
            self.__graph_dict2str__()
            self.__graph_dict2list__()
        elif isinstance(graph, list):
            self.__graph_list_parse__(graph)
            self.__graph_list2dict__()
            self.__graph_dict2str__()

    def __graph_list_parse__(self, graph):
        for e in graph:
            if e not in self.__graph_list__:
                self.__graph_list__ += [e]
        
    def __graph_dict_parse__(self, graph):
        self.__graph_dict__ = {'directed':[], 'bidirected':[], 'undirected':[]}
        for edge_type, edges in graph.items():
            for edge in edges:
                if edge not in self.__graph_dict__[edge_type]:
                    self.__graph_dict__[edge_type] += [edge]

    def __graph_str_parse__(self, graph):
        self.__graph_str_original__ = graph
        edges_type = "|".join(self.__edges_str_allowed__)
        # edges_type = '|'.join(sorted(map(re.escape, self.__edges_str_allowed__), key=len, reverse=True))

        self.__graph_str_parsed__ = []
        regex = re.compile(rf"(\w+|\{{[^}}]*\}})\s*({edges_type})\s*(\w+|\{{[^}}]*\}})")

        graph = self.__graph_str_parse_inline_paths__(graph)
        for ln in graph.strip().splitlines():
            ln = ln.strip()

            # collect if not a comment
            if not bool(re.search(pattern="^ ?#", string=ln)):
                m = regex.match(ln) 
                if m:
                    nodes1, edge, nodes2 = m.groups()

                    nodes1 = re.sub(pattern='\\{|\\}', repl='', string=nodes1)
                    nodes1 = re.split(r"[,\s]+", nodes1.strip())

                    nodes2 = re.sub(pattern='\\{|\\}', repl='', string=nodes2)
                    nodes2 = re.split(r"[,\s]+", nodes2.strip())

                    for n1, n2 in itertools.product(nodes1, nodes2):
                        self.__graph_str_parsed__.append(f"{n1} {edge} {n2}")
                else:
                    raise ValueError(f"Unrecognized line format: '{ln}'")

        self.__graph_str_parsed__ = "\n".join(self.__graph_str_parsed__)
        return None

    def __graph_str_parse_inline_paths__(self, dag):
        # Split the path string by spaces to separate nodes and arrows
        lines = dag.split("\n")
        edges_type = '|'.join(sorted(map(re.escape, self.__edges_str_allowed__), key=len, reverse=True))

        res = []
        for path in lines:
            delimiter_pattern = re.compile(rf'({edges_type})')
            unique_edges = set()

            # Split the path by the arrow delimiters
            components_raw = delimiter_pattern.split(path)

            # Clean the list: remove empty strings and strip whitespace from each part
            components = [c.strip() for c in components_raw if c and c.strip()]

            # Iterate through the components, taking 3 at a time to form an edge
            for i in range(0, len(components) - 1, 2):
                node1 = components[i]
                arrow = components[i+1]
                node2 = components[i+2]

                # Re-format the edge with standard spacing for consistent output
                edge = f"{node1} {arrow} {node2}"
                unique_edges.add(edge)
            res += ["\n".join(unique_edges)]

        res = "\n".join(res)
        res = res.replace("<- >", "<->")
        return res

    def __graph_str2dict__(self):
        """
        Parse DAG string to properties of the graph: nodes, directed, 
        bidirected, and undirected edges. 
        """
        DAG = self.__graph_str_parsed__
        directed, undirected, bidirected = [], [], []

        # One regex to handle all edge types
        pattern = re.compile(r"^\s*(\w+)\s*(->|<-|<->|--)\s*(\w+)\s*$")

        lines = DAG.strip().splitlines()
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue  # skip empty/comment lines

            m = pattern.match(line)
            if not m:
                raise ValueError(f"\nUnrecognized format: '{line}'")

            lhs, op, rhs = m.groups()
            if op == "->":
                a, b = lhs, rhs
                directed.append((a, b))

            elif op == "<-":
                a, b = rhs, lhs   # normalize as parent=a -> child=b
                directed.append((a, b))

            elif op == "<->":
                a, b = lhs, rhs
                bidirected.append( ((a, b), (b, a)) )

            elif op == "--":
                a, b = lhs, rhs
                undirected.append({a, b})

            # single place to update the node set
            self.nodes.update({a, b})

        # eliminate duplicates
        directed = list(set(directed))
        bidirected = list(set(bidirected))
        undirected = list(set([tuple(g) for g in undirected]))
        undirected = [set(g) for g in undirected]

        self.__graph_dict__ = {"directed"  : directed,
                               'bidirected': bidirected,
                               'undirected': undirected}

    def __graph_list2dict__(self):
        self.__graph_dict__ = {'directed':[], 'bidirected':[], 'undirected':[]}
        for edge in self.__graph_list__:
            edge_type = self.__edge_type__(edge)
            self.__graph_dict__[edge_type] += [edge]

    def __graph_dict2list__(self):
        self.__graph_list__ = []
        for type, edges in self.__graph_dict__.items():
            self.__graph_list__ += [edges]
        # flatten
        self.__graph_list__ = list(itertools.chain.from_iterable(self.__graph_list__))
            
    def __graph_dict2str__(self):
        self.__graph_str_parsed__ = ''
        for type, edges in self.__graph_dict__.items():
            for nodes in edges:
                if type=='directed':
                    edge = '->'
                if type=='bidirected':
                    edge = '<->'
                    nodes = nodes[0]
                if type=='undirected':
                    edge = '--'
                    nodes = list(nodes)
                self.__graph_str_parsed__ += f"{nodes[0]} {edge} {nodes[1]}\n" 
        self.__graph_str_original__ = self.__graph_str_parsed__
        
    # collect info
    def __collect_info__(self, nodes_role, nodes_position, nodes_label):
        # collect info (keep order)
        self.__collect_nodes__()
        self.__collect_nodes_parents__()
        self.__collect_nodes_role__(nodes_role)
        self.__collect_nodes_position__(nodes_position)
        self.__collect_nodes_label__(nodes_label)
        # 
        self.nodes_info = {node:{} for node in self.nodes}
        self.__collect_info_nodes_role__()
        self.__collect_info_nodes_position__()
        self.__collect_info_nodes_label__()
        # 
        self.__collect_edges_properties__()
        
    def __collect_nodes__(self):
        nodes = set()
        for edge_type, edges in self.__graph_dict__.items():
            for edge in edges:
                for node in edge:
                    if edge_type=='bidirected':
                        node = node[0]
                    nodes = nodes.union([node])
        self.nodes = nodes

    def __collect_nodes_parents__(self):
        self.nodes_parents = defaultdict(set)  # child -> {parents}
        for n1, n2 in self.__graph_dict__['directed']:
            self.nodes_parents[n2].update([n1])
        self.nodes_parents = dict(self.nodes_parents)
        
    def __collect_edges_properties__(self):
        self.directed   = self.__graph_dict__['directed']
        self.bidirected = self.__graph_dict__['bidirected']
        self.undirected = self.__graph_dict__['undirected']

    def __collect_info_nodes_role__(self):
        res = {}
        for role, nodes in self.nodes_role.items():
            for node in nodes:
                self.nodes_info[node]['role'] = role

    def __collect_info_nodes_position__(self):
        res = {}
        for node, position in self.nodes_position.items():
            self.nodes_info[node]['position'] = position

    def __collect_info_nodes_label__(self):
        res = {}
        for node, label in self.nodes_label.items():
            self.nodes_info[node]['label'] = label

    def __collect_nodes_label__(self, nodes_label):
        nodes_label = nodes_label or {}
        for node in self.nodes:
            self.nodes_label[node] = nodes_label.get(node, None) or node

    def __collect_nodes_position__(self, nodes_position):
        if nodes_position:
            self.nodes_position = {}
            for node, pos in nodes_position.items():
                if node in self.nodes:
                    self.nodes_position[node] = pos

    def __collect_nodes_role__(self, nodes_role):
        nodes_role = nodes_role or {}
        self.nodes_role['Observed'] = [] # keep this here
        nodes_with_role_already_set = []

        for role, node in nodes_role.items() :
            if role=='Outcome':
                if isinstance(node, list) and len(node)==1:
                    node = node[0]
                assert isinstance(node, str), "Check nodes_role. Node 'Outcome' must be a string"

            else:
                assert isinstance(node, str) or isinstance(node, list), \
                    "Check nodes_role. Nodes 'Exposure' and 'Latent' must be strings or lists"
            node = node if isinstance(node, list) else [node]
            self.nodes_role[role] = [n for n in node if n in self.nodes]
            nodes_with_role_already_set += node

        # set observed as default if role of node is not provided
        for node in self.nodes:
            if node not in nodes_with_role_already_set:
                self.nodes_role['Observed'] += [node]

        self.exposure = self.nodes_role.get('Exposure', None)
        self.outcome  = self.nodes_role.get('Outcome', None)
        self.latent   = self.nodes_role.get('Latent', None)
        self.observed = self.nodes_role.get('Observed', None)

    # R dagitty
    def __create_dagitty__(self):
        # # Convert to dagitty string: "dag { A -> B; B -> C; ... }"
        # edges = [f"{u} -> {v}" for u, v in self.G.edges()]
        # edges = '; '.join(edges)

        roles = ''
        for role, nodes in self.nodes_role.items():
            for node in nodes:
                roles += f"{node} [{role.lower()}]\n"

        # Load dagitty and pass the DAG string
        dagitty_str = f"dag {{ {self.__graph_str_parsed__} \n {roles} }}"
        self.__dagitty__ = dagitty.dagitty(dagitty_str)

    # R dagitty
    def __dagitty2inputs__(self, dag_dagitty):
        dag_str = ''
        dag_df = convert().tibble2tp(dagitty.edges(dag_dagitty))
        for a, b, e, *_ in dag_df.to_polars().iter_rows():
            dag_str += f"{a} {e} {b}\n"

        roles = {"Exposure": list(dagitty.exposures(dag_dagitty)),
                 'Outcome' : list(dagitty.outcomes(dag_dagitty)),
                 "Latent"  : list(dagitty.latents(dag_dagitty))}

        return dag_str, roles
    # -------------------------------------------------

    def __rebuild_graph__(self, graph):
        res = DAG(graph,
                  nodes_role     = self.nodes_role,
                  nodes_position = self.nodes_position,
                  nodes_label    = self.nodes_label,
                  edge_label     = self.edge_label
                  )
        return res

    def __repr__(self):
        self.__print_graph__()
        return ''

    def __str__(self):
         self.__repr__()
         return ''

    def __print_graph__(self):
        out = 'Graph:\n'

        d = [f"{n1} -> {n2}" for n1, n2 in self.directed]
        out += '\n'.join(d) if len(d)>0 else ''

        b = [f"{n1[0]} <-> {n2[0]}" for n1, n2 in self.bidirected]
        out += '\n' + '\n'.join(b) if len(b)>0 else ''

        u = [f"{n1} -- {n2}" for n1, n2 in self.undirected]
        out += '\n' +'\n'.join(u) if len(u)>0 else ''

        roles = [f"{role}: {', '.join(nodes)}" for role, nodes in self.nodes_role.items()]
        out += "\n"+"\n".join(roles) if len(roles)>0 else ''

        print(out)
        return out

    def __collect_nodes_from_edges__(self, edges_dict):
        nodes = []
        for edge_type, edges in edges_dict.items():
            if edge_type!='bidirected':
                nodes += list(set(itertools.chain.from_iterable(edges)))
            else:
                nodes += list(set(itertools.chain.from_iterable(itertools.chain.from_iterable(edges))))
        return nodes

    def __chunked_ranges__(self, limit, n):
        """
        Split [0..limit] into chunks.
        Each chunk has n elements, except:
          - the last one may have fewer if not divisible, OR
          - the last one may be larger if needed to include 'limit'.
        """
        start = 0
        idx = 0
        limit -=1
        while start <= limit:
            end = start + n - 1
            if end >= limit:   # last chunk, go all the way to limit
                yield idx, list(range(start, limit + 1))
                break
            else:
                yield idx, list(range(start, end + 1))
                start = end + 1
                idx += 1

    # manipulating graph  -----------------------------
    # nodes 
    def get_nodes(self, exclude_latent=False):
        nodes = list(self.nodes)
        latent_nodes = self.latent

        if exclude_latent and latent_nodes:
            nodes = [n for n in nodes if n not in latent_nodes]
        return nodes

    def set_node_label(self, nodes_label):
        for node, label in nodes_label.items():
            self.nodes_label[node] = label

    def set_nodes_role(self, nodes_role, keep_others=True):
        if keep_others:
            for role, nodes in self.nodes_role.items():
                if role not in nodes_role.keys():
                    nodes_role[role] = nodes

        self.__build_graph__(self.__graph_str_parsed__, nodes_role)
        return self

    def set_node_position(self, position):
        for node, p in position.items():
            self.position[node] = p

    # edges 
    def edge_add(self, edge):
        res = self
        if not self.edge_exist(edge):
            graph = self.__graph_list__.copy()
            graph.append(edge)
            res = self.__rebuild_graph__(graph)
        return res

    def edge_remove(self, edge):
        removed = False
        graph = self.__graph_list__.copy()

        if edge in self.__graph_list__:
            graph.remove(edge)
            removed = True
        elif self.__edge_type__(edge)=='bidirected':
            edge = (edge[1], edge[0])
            if edge in self.__graph_list__:
                graph.remove(edge)
                removed = True

        if removed:
            return self.__rebuild_graph__(graph)
        else:
            return  self

    def edge_replace(self, remove, add):
        res = self.edge_remove(remove)
        res = res.edge_add(add)
        return res

    def edge_exist(self, edge, edges=None):
        """
        Check whether `edge` exists in `edges`,
        robust to order of nodes for undirected and bidirected edges.
        """
        if edges is None:
            edge_type = self.__edge_type__(edge)
            edges = self.__getattribute__(edge_type)
        edges = [edges] if not isinstance(edges, list) else edges
        edge = self.__edge_frozen_format__(edge)
        edges_in_list = {self.__edge_frozen_format__(e) for e in edges}
        return edge in edges_in_list

    def set_edge_label(self, edge_label):
        for edge, label in edge_label.items():
            self.edge_label[edge] = label

    def __edge_frozen_format__(self, edge):
        """
        Convert an edge into a canonical, hashable form.
        - directed: ('A','B')
        - undirected: frozenset({'A','B'})
        - bidirected: frozenset({('A','B'),('B','A')})
        """
        # undirected
        if isinstance(edge, (set, frozenset)):
            return frozenset(edge)

        # bidirected
        if (isinstance(edge, tuple) 
            and len(edge) == 2 
            and all(isinstance(e, tuple) and len(e) == 2 for e in edge)):
            return frozenset([tuple(edge[0]), tuple(edge[1])])

        # directed
        if (isinstance(edge, tuple) 
            and len(edge) == 2 
            and all(isinstance(x, str) for x in edge)):
            return tuple(edge)

        raise ValueError(f"Unrecognized edge format: {edge}")

    def __edge_type__(self, edge):
        """
        Classify an edge as 'directed', 'bidirected', or 'undirected'.
        """
        # Undirected: set/frozenset of 2 nodes
        if isinstance(edge, (set, frozenset)):
            if all(isinstance(x, str) for x in edge) and len(edge) == 2:
                return "undirected"

        # Bidirected: tuple of two directed edges
        if (isinstance(edge, tuple) 
            and len(edge) == 2 
            and all(isinstance(e, tuple) and len(e) == 2 for e in edge)
            and all(isinstance(x, str) for e in edge for x in e)):
            return "bidirected"

        # Directed: tuple of two nodes
        if (isinstance(edge, tuple) 
            and len(edge) == 2 
            and all(isinstance(x, str) for x in edge)):
            return "directed"

        raise ValueError(f"Unrecognized edge format: {edge}")

    # comparing SCM
    def edge_differences(self, G2):
        res1 = self.__edge_differences__(G2)
        res2 = G2.__edge_differences__(self)
        return {"G1":res1, "G2":res2}

    def __edge_differences__(self, G2):
        res1 = {}
        edge_types = ['directed', 'undirected', 'bidirected']
        for edge_type in edge_types:
            res1[edge_type] = []
            edges_list1 = self.__getattribute__(edge_type)
            edges_list2 = G2.__getattribute__(edge_type)
            for edge in edges_list1:
                if edge_type=='bidirected':
                    if edge not in edges_list2 and (edge[1], edge[0]) not in edges_list2:
                        res1[edge_type] += [edge]
                else:
                    if edge not in G2.__getattribute__(edge_type):
                        res1[edge_type] += [edge]
        return res1
    # -------------------------------------------------

    # computations --------------------------------------
    # dagitty (R dependencies)
    def local_independencies(self, data=None):
        """
        Given a networkx.DiGraph, return implied conditional independencies using dagitty (via R).

        Parameters:
            G (nx.DiGraph): Directed acyclic graph (must be a valid DAG)

        Returns:
            List[str]: Implied conditional independencies, e.g., "X _|_ Y | Z"
        """

        data = data or self.data
        # compute
        if data is None:
            inds = dagitty.impliedConditionalIndependencies(self.__dagitty__)
            inds = [str(i).strip() for i in inds]
            inds = tp.tibble({"term":inds})
        else:
            inds = dagitty.localTests(self.__dagitty__, data=convert().tp2tibble(data))
            inds = convert().tibble2tp(inds, rownames2col='term')\
                         .rename({'p.value':"pvalue",
                                  '2.5%':'conf.low',
                                  '97.5%':'conf.hitg',
                                  })
       #         .unnest("parsed"))

        return inds
        
    # dagitty (R dependencies)
    def identification_analysis(self, exposure=None, outcome=None,
                                adj_set = None,
                                causal_probability='maybe'):
        """
        causal_probability: str
            If 'always', always compute it; if 'maybe', compute it
            only if there is not identification by adjustment for
            total_effect_adj_set effect
        """
        exposure = exposure or self.exposure
        outcome = outcome or self.outcome

        assert exposure is not None, "Exposure must be provided."
        assert outcome is not None, "Outcome must be provided."

        # identification by adjustment 
        # ----------------------------
        # total effect
        total_effect_adj_set = dagitty.adjustmentSets(self.__dagitty__,
                                                      exposure = exposure,
                                                      outcome = outcome,
                                                      effect='total',
                                                      type='minimal'
                                                      )
        total_effect_adj_set = None if len(total_effect_adj_set)==0 else list(total_effect_adj_set.rx2['1'])
        total_effect_adj_set = [''] if total_effect_adj_set==[] else total_effect_adj_set
        total_identified = True if total_effect_adj_set is not None else False
        # direct effect
        direct_effect_adj_set = dagitty.adjustmentSets(self.__dagitty__,
                                                       exposure = exposure,
                                                       outcome = outcome,
                                                       effect='direct'
                                                       )
        direct_effect_adj_set = None if len(direct_effect_adj_set)==0 else list(direct_effect_adj_set.rx2['1'])
        direct_effect_adj_set = [''] if direct_effect_adj_set==[] else direct_effect_adj_set
        direct_identified = True if direct_effect_adj_set is not None else False
        
        def build_formula(identified, y, d, X):
            if not identified:
                f = ''
            elif X is None or X[0]=='':
                f = f"{y} ~ {d}"
            else:
                f = f"{y} ~ {d} + {' + '.join(X)}"
            return f
        def build_formula_latex(identified, y, d, X):
            if not identified:
                f = ""
            elif X is None or X[0]=='':
                f = f"{y} ~ \\beta_0 + \\beta_{{d}}{d}"
            else:
                beta_xX = [f"\\beta{{{x}}}{x}" for x in X]
                f = f"{y} ~ \\beta_0 + \\beta_{{d}}{d} + {' + '.join(beta_xX)}"
            return f
            
        res = (
            tp.tibble({"Cause"  : [exposure],
                       'Effect' : [outcome],
                       'id_type': ['adjustement']
                       })
            .crossing(effect_type = ['Direct', 'Total'])
            .mutate(identified = tp.case_when(tp.col("effect_type")=='Direct', direct_identified,
                                              tp.col("effect_type")=='Total', total_identified),
                    adj_set = tp.case_when(tp.col("effect_type")=='Direct', direct_effect_adj_set,
                                           tp.col("effect_type")=='Total', total_effect_adj_set,
                                           ),
                    formula = tp.map(['identified', 'Effect', 'Cause', 'adj_set'], lambda vars: build_formula(*vars)),
                    formula_latex = tp.map(['identified', 'Effect', 'Cause', 'adj_set'], lambda vars: build_formula_latex(*vars))
                    )
        )

        # causal probability  (only not possible to use adjustment or explicitly asked)
        # ------------------
        if not total_identified or causal_probability=='always':
            X = ', '.join(self.get_nodes())
            Y = outcome
            D = ', '.join(exposure) if isinstance(exposure, list) else exposure
            Z = ', '.join(adj_set) if isinstance(adj_set, list) else adj_set

            p = f"p({X})"
            q = f"p({Y} | do({D}))" if Z is None else f"p({Y} | do({D}), {Z})"
            causal_probability = dosearch.dosearch(p, q, self.__dagitty__)
            causal_probability = causal_probability.rx2['formula'][0] \
                if bool(causal_probability.rx2['identifiable'][0]) else None

            # formulas
            if causal_probability is not None:
                formula = causal_probability.replace('\\left(', ' ')\
                                            .replace('\\right)', '')\
                                            .replace('\\', '')
                formula = f"{q} = {formula}"
                formula_latex = f"{q} = {causal_probability}"
            else:
                formula = ''
                formula_latex = ''
            
            res2 = (
                tp.tibble({"Cause"           : [exposure],
                           'Effect'          : [outcome],
                           'id_type'         : ['do-calculus'],
                           "effect_type"     : 'Total' if adj_set is None else f"Total (conditioned on {Z})",
                           'identified'      : True if causal_probability is not None else False,
                           'adj_set'         : None,
                           'formula'         : formula,
                           'formula_latex'   : formula_latex 
                           })
            )
            res = res.bind_rows(res2)

        return res

    # dagitty (R dependencies)
    def paths(self, exposure=None, outcome=None, adj_set=None, directed=False):
        exposure = exposure or self.exposure
        outcome = outcome or self.outcome

        assert exposure, "Exposure must be provided."
        assert outcome, "Outcome must be provided."

        adj = adj_set or NULL
        paths_info = dagitty.paths(self.__dagitty__, exposure, to=outcome, Z=adj, directed=directed)
        paths = list(paths_info.rx2['paths'])
        are_open = list(paths_info.rx2['open'])

        return {path:{'open':is_open, 'adj_set':adj_set} for path, is_open in zip(paths, are_open)}

    # dagitty (R dependencies)
    def equivalence_class(self):
        """
        Details
        -------
        A equivalence class of a DAG is a graph that replaces directional edges
        by undirectional edges except in v-structures (triples X->Z<-Y where 
        X and Y are not adjacent). Therefore, all Markov
        equivalent DAGs will have the same equivalence class.
        """
        eq = dagitty.equivalenceClass(self.__dagitty__)
        dag, _ = self.__dagitty2inputs__(eq)
        res = self.__rebuild_graph__(dag)
        return res

    # dagitty (R dependencies)
    def equivalent_dags(self):
        eqs = dagitty.equivalentDAGs(self.__dagitty__)
        res = []
        for eq in eqs:
            dag, _ = self.__dagitty2inputs__(eq)
            res += [self.__rebuild_graph__(dag)]
        return res

    def observationally_equivalent(self, G):
        """
        Check if two DAGs are observationally equivalent by comparing their
        markov equivalent classes. It applies to CBN or for
        SCM when no functional form for the SCM equations were selected.
        See details.

        Details
        -------
        Observational equivalence is related to Markov equivalence.

        Two DAGs are Markov equivalent iff
        A. They have the same skeleton (same set of adjacencies, i.e. same undirected edges)
        B. They have the same set of v-structures, which are triples X->Z<-Y where 
           X and Y are not adjacent).

        A equivalence class of a DAG is a graph that replaces directional edges
        by undirectional edges except in v-structures. Therefore, all Markov
        equivalent DAGs will have the same equivalence class.

        For CBN:
        - Two CBNs are observational equivalence iff they are Markov equivalence.

        For SCM:
        Without functional form assumptions, for observational equivalence:
        - Necessary condition: both SCMs have the same set of conditional independencies
        - Sufficient condition: both SCMs are in the same markov equivalence class (Pearl, 2009)
        - Basically, two SCMs are observationally equivalent iff their causal graphs belong
          to the same Markov equivalence class — i.e., they share the same skeleton and v-structures.

        With functional form assumptions
        - Once you impose functional form restrictions on SCMs, such as linearity,
          Gaussian disturbance, or additive error, and so on, observational equivalence
          can be strictly finer. That is, Markov-equivalence is not a sufficient condition.
          Example:
          a. Linear Gaussian SEMs assumption:
             - All DAGs in the same equivalence class remain indistinguishable.
               Markov equivalence = observational equivalence.
               Reason: any covariance matrix that one DAG can generate can also
               be generated by another DAG in its equivalence class, via suitable parameter choice.

          b. Linear non-Gaussian models (LiNGAM)
             - Orientations become testable because independent non-Gaussian noise
               'pins down' which variable must be the parent, breaking Markov equivalence.
                Example: X->Y and X <- Y: In Gaussian case: indistinguishable.
                         In non-Gaussian: identifiable.

          c. Additive Noise Models (ANMs)
             - If the true relation is Y = f(X) + e with independent noise e,
               then typically the 'wrong' orientation X = g(Y) + e'
               cannot hold with independent noise. So direction becomes identifiable.

        In summary, generally SCMs (no distributional restrictions), Markov equivalence
        does imply observational equivalence. But once you impose restrictions
        (linear, Gaussian, additive, etc.), observational equivalence can be strictly finer.
        That is, if one assumes functional forms or noise properties, one may be able to 
        distinguish DAGs inside a Markov equivalence class. Some Markov-equivalent DAGs
        become distinguishable. Then, the test of equivalence depends on the
        functional form assumption adopted, so it is case-by-case.

        References
        ----------
        - Pearl, J. (2009). Causality: Models, Reasoning and Inference. : Cambridge Univ Press.
        """
        # check if same equivalence class
        G1_eq = self.equivalence_class()
        G2_eq = G.equivalence_class()
        diff = G1_eq.edge_differences(G2_eq)
        obs_eq = True
        for g, edges in diff.items():
            obs_eq &= all([len(e)==0 for e in edges.values()])
        return obs_eq 
    # -------------------------------------------------

    # plots -------------------------------------------
    def plot(self,
             # nodes
             graph_style = 'default',
             nodes_label=None,
             nodes_position=None,
             # node
             node_subset=None,
             node_shape=None,
             node_size = None,
             node_color = None,
             node_border_color=None,
             node_border_style=None,
             node_border_width=None,
             node_latent_show=True,
             # node label
             show_labels = True,
             use_labels = True,
             node_label_box=True,
             node_label_fontsize=None,
             node_label_fontweight='normal',
             node_label_adj_x=0,
             node_label_adj_y=0,
             node_label_box_style="square",
             node_label_box_margin=.5,
             # edges
             edge_subset=None,
             edge_color=None,
             edge_style=None,
             edge_arc = None,
             edge_linewidth = None,
             edge_head_size = None,
             edge_head_style = None,
             edge_margin_tail=None,
             edge_margin_head=None,
             # edges labels
             edge_label=None,
             edge_label_size=None,
             edge_label_color=None,
             edge_label_alpha=None,
             edge_label_rotate=None,
             edge_label_position=None,
             edge_label_sig_level=0.05,
             edge_label_pvalue=None,
             # legend
             legend_show=True,
             legend_title='Nodes',
             legend_title_align='left',
             legend_title_weight='bold',
             legend_title_size=12,
             legend_omit_cases=['Observed'],
             legend_keys=None,
             legend_loc='best',
             legend_fontsize=10,
             legend_frame=False,
             legend_kws={},
             #
             title = None,
             title_loc = 'left',
             title_kws = {},
             # 
             figsize = [6, 4],
             usetex = True,
             ax=None,
             *args,
             **kws
             ):
        """
        Draw a custom DAG with support for:
          - Latent variables
          - Curved edges
          - Colored and dotted arcs
          - Optional arc representation for latent confounding
          - Custom node labels

        Parameters:
            G (nx.DiGraph): The input DAG with optional edge attributes 'style', 'color', 'curved'.
            nodes_position (dict): Optional node positions for layout.
            nodes_role (dict): Optional dict with keys 'latent', 'exposure', 'outcome' listing node names.
            use_arc (bool): If True, draw dotted arcs between children of latent confounders instead of drawing latent nodes.
            nodes_label (dict): Optional dict mapping node names to display labels.
            show_labels  (str or None; Default='label'): One of 'label', 'name', or 'none'.
                If 'label', use labels if provided; If 'name', always use node name; If 'none',
                don't omit labels and names of nodes altogether.
            node_label_adj_x (float or dict): displaces the labels in the x direction. If dict, the keys
                should be the node labels or name, and displacement will be applied only to those points
                specified in the dict. If float, the same displacement is applied to all nodes.
            node_label_adj_x (float or dict): same as node_label_adj_y, but for the y axis
            graph_style (str): specific styles for nodes and arrows
                  - 'default': nodes in circles with labels in their middle
                  - 'rectangle': nodes in rectangles with labels in their middle
                  - 'pearl': nodes as dots with labels next to them (use node_label_adj_x and node_label_adj_y
                             to adjust the location of the labels)
                  All features can be overwrittied by specifying the value of the parameters for the plot.
        """
        default_usetex = plt.rcParams["text.usetex"] 
        plt.rcParams["text.usetex"] = usetex
        plt.rcParams['text.latex.preamble'] = r'\usepackage{amsmath, amssymb, siunitx, bm}'


        # collect arguments
        pars = dict(locals())      # {'node_position':..., 'arg2':..., 'args':(...), 'kws':{...}}
        args = pars.pop('args') # extra positional
        kws  = pars.pop('kws')  # extra keyword

        # figure 
        # ------
        G_draw = self.__plot_create_nx__()
        if ax is None:
            fig, ax = plt.subplots(figsize=figsize, tight_layout=True)
        plt.sca(ax)

        # styles
        # ------
        nodes_style, labels_style, edges_style = self.__plot_get_style__(graph_style)

        # nodes 
        # -----
        node_subset    = self.__plot_nodes_subset__(node_subset, node_latent_show)
        nodes_position = self.__plot_nodes_positions__(G_draw, nodes_position)
        for role, nodes in node_subset.items():
            fig_nodes = nx.draw_networkx_nodes(
                G_draw,
                nodes_position,
                nodelist=nodes,
                ax=ax,
                # 
                node_size  = self.__plot_collect_aes__(role, node_size, nodes_style[role]['node_size']),
                node_color = self.__plot_collect_aes__(role, node_color, nodes_style[role]['node_color']),
                node_shape = self.__plot_collect_aes__(role, node_shape, nodes_style[role]['node_shape']),
                linewidths = self.__plot_collect_aes__(role, node_border_width,
                                                       nodes_style[role]['node_border_width']),
                edgecolors = self.__plot_collect_aes__(role, node_border_color,
                                                       nodes_style[role]['node_border_color']),
                alpha      = None,
                cmap       = None,
                vmin       = None,
                vmax       = None,
                label      = None,
                margins    = None, 
                hide_ticks = True
            )
            fig_nodes.set_linestyle(self.__plot_collect_aes__(role, node_border_style,
                                                              nodes_style[role]['node_border_style']))

        # nodes labels 
        # ------------
        if show_labels:
            nodes = set(itertools.chain.from_iterable(node_subset.values()))
            nodes_label = self.nodes_label | (nodes_label or {})
            adj_x = self.__plot_label_adj__(node_label_adj_x, nodes_label)
            adj_y = self.__plot_label_adj__(node_label_adj_y, nodes_label)
            for node in nodes:
                label = nodes_label.get(node, node) if use_labels else node
                role  = self.nodes_info[node]['role']
                x, y  = nodes_position[node] if nodes_position and nodes_position[node] else\
                    self.nodes_info[node]['position'] 

                bbox = None
                if node_label_box and graph_style=='rectangle':
                    bbox = {
                        "boxstyle": f"{node_label_box_style},pad={node_label_box_margin}",
                        "fc": self.__plot_collect_aes__(role, node_color, nodes_style[role]['node_color']),
                        "ec": self.__plot_collect_aes__(role, node_border_color,
                                                        nodes_style[role]['node_border_color']),
                        "lw": self.__plot_collect_aes__(role, node_border_width,
                                                       nodes_style[role]['node_border_width']),
                        "linestyle": self.__plot_collect_aes__(role, node_border_style,
                                                               nodes_style[role]['node_border_style']),
                        "alpha": 1}

                weight = self.__plot_collect_aes__(role, node_label_fontweight,
                                                   labels_style[role]['node_label_fontweight'])
                label = f"\\textbf{{{label}}}" if weight == 'bold' else label
                plt.text(x + adj_x[node],
                         y + adj_y[node],
                         label,
                         fontweight = weight,
                         fontsize   = self.__plot_collect_aes__(role, node_label_fontsize,
                                                                labels_style[role]['node_label_fontsize']),
                         ha = 'center',
                         va = 'center',
                         bbox = bbox)

        # edges and edges labels
        # ----------------------
        nodes = set(itertools.chain.from_iterable(node_subset.values()))
        for edge_type in ['directed', 'bidirected', 'undirected']:
            style = self.__plot_collect_aes__(edge_type, edge_style, edges_style['edge_style'][edge_type])
            color = self.__plot_collect_aes__(edge_type, edge_color, edges_style['edge_color'][edge_type])
            arc   = self.__plot_collect_aes__(edge_type, edge_arc, edges_style['edge_arc'][edge_type])
            width = self.__plot_collect_aes__(edge_type, edge_linewidth, edges_style['edge_linewidth'][edge_type])
            arrow_head_size = self.__plot_collect_aes__(edge_type, edge_head_size, edges_style['edge_head_size'][edge_type])
            arrow_head_style = self.__plot_collect_aes__(edge_type, edge_head_style, edges_style['edge_head_style'][edge_type])
            edge_margin_tail = self.__plot_edge_margin__(edge_margin_tail, edges_style["edge_margin_tail"][edge_type])
            edge_margin_head = self.__plot_edge_margin__(edge_margin_head, edges_style["edge_margin_head"][edge_type])

            for edge in self.__getattribute__(edge_type):
                edge = tuple(edge)
                if edge_type!='bidirected':
                    u, v = edge
                else:
                    u, v = edge[0][0], edge[0][1]

                # collect edges to show if edge_subset 
                show_edge = True
                if edge_subset:
                    e = set(edge) if edge_type=='undirected' else edge
                    show_edge = self.edge_exists(e, edge_subset.get(edge_type, []))

                if u in nodes and v in nodes and show_edge:
                    # edge
                    nx.draw_networkx_edges(
                        G_draw,
                        nodes_position,
                        edgelist            = [(u, v)],
                        style               = style,
                        edge_color          = color,
                        connectionstyle     = f"arc3,rad=-{arc}",
                        arrows              = True,
                        arrowstyle          = arrow_head_style,
                        arrowsize           = arrow_head_size,
                        min_source_margin   = edge_margin_tail.get(edge, 0),
                        min_target_margin   = edge_margin_head.get(edge, 0),
                        width               = width,
                        ax=ax)

                    # edge label
                    edge_label = edge_label or self.edge_label
                    label = edge_label.get(edge, '')
                    rotate = edge_label_rotate if edge_label_rotate is not None else True # must keep "is not None" here
                    nx.draw_networkx_edge_labels(
                        G_draw,
                        pos             = nodes_position,
                        connectionstyle = f"arc3,rad=-{arc}",
                        edge_labels     = {(u, v): label},
                        # 
                        alpha      = self.__plot_edge_label_feature__('alpha', edge, edge_label_alpha, None, edge_label_sig_level,
                                                                      edge_label_pvalue=edge_label_pvalue),
                        font_size  = self.__plot_edge_label_feature__('size' , edge, edge_label_size, 15),
                        font_color = self.__plot_edge_label_feature__('color', edge, edge_label_color, label=label),
                        rotate     = self.__plot_edge_label_feature__('rotate', edge, edge_label_rotate, default=rotate),
                        label_pos  = self.__plot_edge_label_feature__('position', edge, edge_label_position, .5),
                        ax         = ax
                    )

        # legend 
        # ------
        if legend_show:
            keys = []
            for role, _ in node_subset.items():
                if role not in legend_omit_cases:
                    if role=='Latent' and node_latent_show:
                        marker = ''
                        linecolor = self.__plot_collect_aes__(role, node_border_color,
                                                              nodes_style[role]['node_border_color']) 
                    else:
                        marker = 'o'
                        linecolor='white'
                    keys += [
                        Line2D(
                            [0], [0],
                            marker=marker,
                            color=linecolor,
                            label=role,
                            markersize=10,
                            markeredgecolor=self.__plot_collect_aes__(role, node_border_color,
                                                                      nodes_style[role]['node_border_color']),
                            markerfacecolor=self.__plot_collect_aes__(role, node_color,
                                                                      nodes_style[role]['node_color']),
                            linestyle=self.__plot_collect_aes__(role, node_border_style,
                                                                nodes_style[role]['node_border_style'])
                        )
                    ]
                if keys: 
                    legend = plt.legend(handles        = keys,
                                        title          = legend_title,
                                        title_fontsize = legend_title_size,
                                        alignment      = legend_title_align,
                                        # title_weight   = legend_title_weight,
                                        loc            = legend_loc,
                                        fontsize       = legend_fontsize,
                                        frameon        = legend_frame,
                                        **legend_kws
                                        )
                    if legend_title_weight=='bold' and legend_title:
                        legend.set_title(title=f'\\textbf{{{legend_title}}}', prop={'weight': 'bold'})

        # title 
        # -----
        if title:
            plt.title(label=title, loc=title_loc, **title_kws)

        plt.axis("off")
        plt.tight_layout()
        plt.show()
        plt.rcParams["text.usetex"] = default_usetex

        return plt, ax

    def plot_paths(self, exposure=None, outcome=None, adj_set=None, directed=False,
                   show_full_dag = True,
                   use_labels=True,
                   title_fontsize = 10,
                   figsize=(16, 9),
                   path_color='black',
                   **plot_kws
                   ):
        adj_set = [adj_set] if isinstance(adj_set, str) else adj_set

        paths = self.paths(exposure=exposure, outcome=outcome, adj_set=adj_set, directed=directed)
        npaths = len(paths)
        ncols = int(math.ceil(math.sqrt(npaths)))
        nrows = int(math.ceil(npaths / ncols))
        fig, axs = plt.subplots(nrows, ncols, figsize=figsize, tight_layout=True)
        if ncols >1 or nrows>1:
            axs=axs.flatten()
        else:
            axs = [axs]
        [ax.axis('off') for ax in axs]
        # 

        pos = self.nodes_position
        roles = self.nodes_role
        nodes_label = self.nodes_label
        edge_label = self.edge_label
        for i, (path, info) in enumerate(paths.items()):
            ax = axs[i]

            show_labels=True
            if show_full_dag:
                self.plot(ax=ax, edge_color ='lightgray', **plot_kws)
                show_labels=False

            # G2 = DAG(path, nodes_role=roles, nodes_position=pos, nodes_label=nodes_label)
            G2 = self.__rebuild_graph__(path)
            G2.plot(ax=ax, edge_linewidth=3, show_labels=show_labels,
                    edge_color=path_color, use_labels=use_labels, **plot_kws)
            adj = info['adj_set']
            if adj:
                adj = [self.nodes_label.get(x, x) for x in adj] if use_labels else adj
                adj = ', '.join(adj)
            else:
                adj = ""
            title = rf"Path is \textbf{{{'open' if info['open'] else 'closed'}}}; Adjustment set: "+"\{"+adj+"\}"
            ax.set_title(title, loc='left', fontsize=title_fontsize)
            ax.axis('on')
            plt.tight_layout()

        return axs

    def plot_equivalent_dags(self,
                             use_labels=True,
                             show_labels=True,
                             edge_difference_color='red',
                             title_fontsize = 10,
                             title_original_graph = 'Original Graph',
                             title_equivalent_graph = "Equivalent DAG",
                             show_footnote = True,
                             figsize=(16, 9),
                             max_per_figure = 9,
                             max_eq_dags= 27,
                             **plot_kws
                             ):
        # collecting equivalent DAGs
        eq_dags = self.equivalent_dags()
        n_eq_dags = len(eq_dags)
        if n_eq_dags == 0:
            return None

        if n_eq_dags > max_eq_dags:
            print(f"\n**Note:**\n"+
                  f"---------\n"
                  f"Maximun number of equivalent DAGs to plot is set to {max_eq_dags}"+
                  f" by default, but there are {n_eq_dags} equivalent DAGs. Some equivalent DAGs"+
                  f" will be omitted. To change it, set 'max_eq_dags'.\n")

        max_eq_dags = np.min([n_eq_dags, max_eq_dags])
        figs = dict(self.__chunked_ranges__(max_eq_dags, max_per_figure))

        print(f"Total of equivalent DAGs: {n_eq_dags}\n"+
              f"Plotting {max_eq_dags} equivalent DAG(s)\n"
              f"Generating {len(figs.keys())} figure(s) with a maximum of {max_per_figure} panels per figure\n")
        figs_res = {}
        
        for fig_number, panels in figs.items():

            # figure
            ncols = int(math.ceil(math.sqrt(max_per_figure)))
            nrows = int(math.ceil(max_per_figure / ncols))
            fig, axs = plt.subplots(nrows, ncols, figsize=figsize, tight_layout=True)
            if ncols >1 or nrows>1:
                axs=axs.flatten()
            else:
                axs = [axs]
            [ax.axis('off') for ax in axs]

            # panels
            for panel, panel_number in enumerate(panels):
                print(f"Creating plot {panel_number+1} of {n_eq_dags}...", end='')
                ax = axs[panel]
                eq_dag = eq_dags[panels[panel]]
                # baseline plot
                eq_dag.plot(ax=ax, edge_linewidth=1,
                            show_labels=show_labels,
                            use_labels=use_labels,
                            title=title_equivalent_graph,
                            title_fontsize=title_fontsize,
                            **plot_kws)
                # superimpose edges highlighing the differences
                edges = self.edge_differences(eq_dag)['G2']
                nodes = self.__collect_nodes_from_edges__(edges)
                eq_dag.plot(ax=ax, edge_linewidth=3,
                            node_subset = nodes,
                            edge_subset = edges,
                            show_labels=show_labels,
                            edge_color=edge_difference_color,
                            use_labels=use_labels,
                            title=title_equivalent_graph,
                            title_fontsize=title_fontsize,
                            **plot_kws)
                if show_footnote:
                    # footnote
                    xcoord=1
                    ycoord=1.07
                    yoffset=-.1
                    fn = f"Equivalent DAG: {panel_number+1} of {n_eq_dags}"
                    ax.annotate(fn, xy=(xcoord,yoffset), xytext=(xcoord,yoffset),
                                xycoords='axes fraction', size=11, ha='right',
                                style='italic', alpha=.6)
                print('done!')
                ax.axis('on')
                plt.tight_layout()
                figs_res[fig_number] = [fig, axs]
        return figs_res
    
    # ancillary
    def __plot_create_nx__(self):
        G = nx.MultiDiGraph()  # allows multiple edges & types

        # Directed edges
        for u, v in self.directed:
            G.add_edge(u, v, type="directed")

        # Bidirected edges: add both directions
        for (u1, v1), (u2, v2) in self.bidirected:
            G.add_edge(u1, v1, type="bidirected")
            G.add_edge(u2, v2, type="bidirected")

        # Undirected edges: add both directions
        for uv in self.undirected:
            u, v = tuple(uv)
            G.add_edge(u, v, type="undirected")
            G.add_edge(v, u, type="undirected")

        return G

    def __plot_nodes_subset__(self, node_subset, node_latent_show):
        node_subset = node_subset or self.nodes
        nodes_to_plot = {}
        for role, nodes in self.nodes_role.items():
            if role=='Latent' and not node_latent_show:
                continue
            else:
                nodes_to_plot[role] = set([node for node in nodes if node in node_subset])
        return nodes_to_plot

    def __plot_nodes_positions__(self, G_draw, nodes_position):
        nodes_position = nodes_position or self.nodes_position
        if not nodes_position:
            try:
                from networkx.drawing.nx_pydot import graphviz_layout
                nodes_position = graphviz_layout(G_draw, prog="dot")
            except ImportError:
                nodes_position = nx.spring_layout(G_draw)
        return nodes_position 

    def __plot_label_adj__(self, node_label_adj, nodes_label):
        if isinstance(node_label_adj, dict):
            adj = {node:node_label_adj.get(node, 0) for node in self.get_nodes(exclude_latent=False)}
            
        elif isinstance(node_label_adj, (float, int)):
            adj = {node:node_label_adj for node in self.get_nodes(exclude_latent=False)}

        # same for if labels are used
        for node, label in nodes_label.items():
            adj[label] = adj[node]
        
        return adj

    # styles
    def __plot_get_style__(self, graph_style):
        if graph_style=='default':
            aes = self.__plot_get_style_default__()
        
        if graph_style=='rectangle':
            aes = self.__plot_get_style_rectangle__()

        if graph_style=='pearl':
            aes = self.__plot_get_style_pearl__()

        return aes
    
    def __plot_get_style_default__(self):
        nodes = {
            "Exposure": {
                "node_shape": "o",
                "node_size": 1000,
                "node_color": "lightgray",
                "node_border_color": "black",
                "node_border_width": 1,
                "node_border_style": "-"
            },
            "Outcome": {
                "node_shape": "o",
                "node_size": 1000,
                "node_color": "gray",
                "node_border_color": "black",
                "node_border_width": 1,
                "node_border_style": "-"
            },
            "Observed": {
                "node_shape": "o",
                "node_size": 1000,
                "node_color": "white",
                "node_border_color": "black",
                "node_border_width": 1,
                "node_border_style": "-"
            },
            "Latent": {
                "node_shape": "o",
                "node_size": 1000,
                "node_color": "white",
                "node_border_color": "black",
                "node_border_width": 1,
                "node_border_style": "--"
            }
        }
        for role, node in self.nodes_role.items():
            if role not in nodes.keys():
                nodes[role] = nodes['Observed']

        labels = {
            "Exposure": {
                "node_label_fontweight": "normal",
                "node_label_fontsize"  : 12,
            },
            "Outcome": {
                "node_label_fontweight": "normal",
                "node_label_fontsize"  : 12,
            },
            "Observed": {
                "node_label_fontweight": "normal",
                "node_label_fontsize"  : 12,
            },
            "Latent": {
                "node_label_fontweight": "normal",
                "node_label_fontsize"  : 12,
            }
        }
        for role, node in self.nodes_role.items():
            if role not in labels.keys():
                labels[role] = labels['Observed']
            
        edges = {
            "edge_label": self.edge_label,
            "edge_style": {"directed": "solid",
                           "bidirected": "dashed",
                           "undirected": "solid"
                           },
            "edge_color": {"directed": "black",
                           "bidirected": "black",
                           "undirected": "orange"
                           },
            "edge_arc": {"directed": 0,
                         "bidirected": .33,
                         "undirected": 0,
                         },
            "edge_linewidth": {"directed": 1.5,
                               "bidirected": 1.5,
                               "undirected": 1.5
                               },
            "edge_head_size": {"directed": 20,
                               "bidirected": 20,
                               "undirected": 0
                               },
            "edge_head_style": {"directed": None,
                               "bidirected": '<|-|>',
                               "undirected": '-' 
                               },
            "edge_margin_tail": {"directed": 20,
                                 "bidirected": 20,
                                 "undirected": 0
                                 },
            "edge_margin_head": {"directed": 20,
                                 "bidirected": 20,
                                 "undirected": 0
                                 }
        }
        return [nodes, labels, edges]
    
    def __plot_get_style_pearl__(self):
        nodes = {
            "Exposure": {
                "node_shape": ".",
                "node_size": 200,
                "node_color": "lightgray",
                "node_border_color": "black",
                "node_border_width": 1,
                "node_border_style": "-"
            },
            "Outcome": {
                "node_shape": ".",
                "node_size": 200,
                "node_color": "gray",
                "node_border_color": "black",
                "node_border_width": 1,
                "node_border_style": "-"
            },
            "Observed": {
                "node_shape": ".",
                "node_size": 200,
                "node_color": "black",
                "node_border_color": "black",
                "node_border_width": 1,
                "node_border_style": "-"
            },
            "Latent": {
                "node_shape": ".",
                "node_size": 200,
                "node_color": "white",
                "node_border_color": "black",
                "node_border_width": 1,
                "node_border_style": "--"
            }
        }
        for role, node in self.nodes_role.items():
            if role not in nodes.keys():
                nodes[role] = nodes['Observed']

        labels = {
            "Exposure": {
                "node_label_fontweight": "normal",
                "node_label_fontsize"  : 12,
            },
            "Outcome": {
                "node_label_fontweight": "normal",
                "node_label_fontsize"  : 12,
            },
            "Observed": {
                "node_label_fontweight": "normal",
                "node_label_fontsize"  : 12,
            },
            "Latent": {
                "node_label_fontweight": "normal",
                "node_label_fontsize"  : 12,
            }
        }
        for role, node in self.nodes_role.items():
            if role not in labels.keys():
                labels[role] = labels['Observed']
            
        edges = {
            "edge_label": self.edge_label,
            "edge_style": {"directed": "solid",
                           "bidirected": "dashed",
                           "undirected": "solid"
                           },
            "edge_color": {"directed": "black",
                           "bidirected": "black",
                           "undirected": "orange"
                           },
            "edge_arc": {"directed": 0,
                         "bidirected": .33,
                         "undirected": 0,
                         },
            "edge_linewidth": {"directed": 1.5,
                               "bidirected": 1.5,
                               "undirected": 1.5
                               },
            "edge_head_size": {"directed": 20,
                               "bidirected": 20,
                               "undirected": 0
                               },
            "edge_head_style": {"directed": None,
                               "bidirected": '<|-|>',
                               "undirected": '-' 
                               },
            "edge_margin_tail": {"directed": 0,
                                 "bidirected": -10,
                                 "undirected": -10
                                 },
            "edge_margin_head": {"directed": -10,
                                 "bidirected": -10,
                                 "undirected": 0
                                 }
        }
        return [nodes, labels, edges]

    def __plot_get_style_rectangle__(self, *args, **kws):
        nodes = {
            "Exposure": {
                "node_shape": "",
                "node_size": 1000,
                "node_color": "lightgray",
                "node_border_color": "black",
                "node_border_width": 1,
                "node_border_style": "-"
            },
            "Outcome": {
                "node_shape": "",
                "node_size": 1000,
                "node_color": "gray",
                "node_border_color": "black",
                "node_border_width": 1,
                "node_border_style": "-"
            },
            "Observed": {
                "node_shape": "",
                "node_size": 1000,
                "node_color": "white",
                "node_border_color": "black",
                "node_border_width": 1,
                "node_border_style": "-"
            },
            "Latent": {
                "node_shape": "",
                "node_size": 1000,
                "node_color": "white",
                "node_border_color": "black",
                "node_border_width": 1,
                "node_border_style": "--"
            }
        }
        for role, node in self.nodes_role.items():
            if role not in nodes.keys():
                nodes[role] = nodes['Observed']

        labels = {
            "Exposure": {
                "node_label_fontweight": "normal",
                "node_label_fontsize"  : 12,
            },
            "Outcome": {
                "node_label_fontweight": "normal",
                "node_label_fontsize"  : 12,
            },
            "Observed": {
                "node_label_fontweight": "normal",
                "node_label_fontsize"  : 12,
            },
            "Latent": {
                "node_label_fontweight": "normal",
                "node_label_fontsize"  : 12,
            }
        }
        for role, node in self.nodes_role.items():
            if role not in labels.keys():
                labels[role] = labels['Observed']
            
        edges = {
            "edge_label": self.edge_label,
            "edge_style": {"directed": "solid",
                           "bidirected": "dashed",
                           "undirected": "solid"
                           },
            "edge_color": {"directed": "black",
                           "bidirected": "black",
                           "undirected": "orange"
                           },
            "edge_arc": {"directed": 0,
                         "bidirected": .33,
                         "undirected": 0,
                         },
            "edge_linewidth": {"directed": 1.5,
                               "bidirected": 1.5,
                               "undirected": 1.5
                               },
            "edge_head_size": {"directed": 20,
                               "bidirected": 20,
                               "undirected": 0
                               },
            "edge_head_style": {"directed": None,
                               "bidirected": '<|-|>',
                               "undirected": '-' 
                               },
            "edge_margin_tail": {"directed": 20,
                                 "bidirected": 20,
                                 "undirected": 0
                                 },
            "edge_margin_head": {"directed": 20,
                                 "bidirected": 20,
                                 "undirected": 0
                                 }
        }
        return [nodes, labels, edges]

    def __plot_collect_aes__(self, role, aes, default):
        res = None
        if aes is not None:
            if isinstance(aes, dict):
                res = aes.get(role, None)
            else:
                res = aes
        
        if not res:
            res = default
        return res

    def __plot_edge_margin__(self, edge_margin, default=20):
        edge_margin = edge_margin or {}
        edges = self.directed + self.bidirected
        if isinstance(edge_margin, (float, int)):
            edge_margin = {e:edge_margin for e in edges}
        edge_margin = {e:edge_margin.get(e, default) for e in edges}

        return edge_margin

    def __plot_edge_label_feature__(self, feature, edge, value, default=None,
                                    alpha_level=0.05, label=None, edge_label_pvalue=None):
        res = value.get(edge, default) if isinstance(value, dict) else (value or default)

        # default color: red for negative, black for positive
        if feature=='color' and not res:
            try:
                label = float(label)
                res = 'red' if label < 0 else 'black'
            except (TypeError, ValueError) as e:
                # default
                res = 'black'

        # default alpha: full for significant, faded otherwise
        if feature=='alpha' and not res and edge_label_pvalue:
            try:
                res = 1 if edge_label_pvalue.get(edge, 0) <= alpha_level else 0.2
            except (TypeError, ValueError) as e:
                # default
                res = 1
        return res
    # -------------------------------------------------

class estimate():
    
    def __init__(self,
                 G,
                 model='auto',
                 model_kws={},
                 # auto
                 model_auto_binary='LPM',
                 # LSEM
                 sem=None,
                 # 
                 *args,
                 **kws
                 ):
        """
        G : a SCM object
        
        model: str
            'auto' : use identification results.
            'GLSEM': use generalied linear structural equation models
            'NPSEM': uses nonparametric structural equation estimation
             See 'Details'

        Details
        -------

        For model='auto' 
          Outcome type is automatically
          Both total and direct effects are estimated
          if both are identified.

        For model='GLSEM' 
        For model='NPSEM' 

        """
        # self.__cov_type__ = cov_type
        # self.__clusters__ = clusters
        # self.__collect_info__(stage1, stage2)
        # self.__estimate__(data)
        # self.__get_diagnostics__()

    def __estimate__(self, G):
        pass
        

    def __graph2sem__(self, parameter_fmt="(beta_{cause}.{effect})"):
        # regression lines
        reg = ''
        for y, pa_y in self.nodes_parents.items():
            pa_y = " + ".join([f"(beta_{v}{y})*{v}" for v in pa_y])
            reg += f"{y} ~ beta_0{y} + {pa_y} + e_{y}\n"

        # correlations
        corr = "\n".join([f"{n1[0]} ~~ {n2[0]}" for n1, n2 in self.bidirected])
        corr = "\n".join([f"{n1} ~~ {n2}" for n1, n2 in self.undirected])

        # if self.exposure and self.outcome:
        #     # indirect effects
        #     self.__graph2sem_indirect_effect__(G, parameter_fmt)
        
        
        sem = f"# LSEM:\n{reg}#Correlations\n{corr}"

    def __graph2sem_indirect_effect__(self, parameter_fmt):
        """
        edges    : list of (u, v) directed edges
        exposure, outcome : compute indirect paths from exposure to outcome
        parameter_fmt: how to name each coefficient (e.g., 'beta_{u}.{v}' or '(beta_{u}.{v})')
        returns  : list of (path_nodes, effect_str)
        """
        # build adjacency
        edges = self.directed
        exposure = self.exposure
        outcome = self.outcome

        adj = defaultdict(list)
        for u, v in edges:
            adj[u].append(v)

        # enumerate simple paths (DFS)
        results = []

        # recursive function
        def dfs(node, visited, path):
            if node == outcome and len(path) >= 3:  # indirect: at least 2 edges
                # build product beta terms for edges along the path
                terms = [parameter_fmt.format(cause=path[i], effect=path[i+1]) for i in range(len(path)-1)]
                results.append( (path[:], " * ".join(terms)) )
                return
            for nxt in adj[node]:
                if nxt in visited:       # avoid cycles
                    continue
                visited.add(nxt)
                path.append(nxt)
                dfs(nxt, visited, path)
                path.pop()
                visited.remove(nxt)

        dfs(exposure, {exposure}, [exposure])
        return results

    def __parse_sem__(self, SEM: str):
        """
        Parse a SEM description and return:
          dag          : str   (each line  'child <- parent')
          edge_label   : dict  {(child,parent): label}
          nodes_role    : dict  {'Latent': [ ... ]}
        """
        sem = SEM
        edge_label, edges, latents = {}, set(), set()
        lines = [l.strip() for l in sem.splitlines()
                 if l.strip() and not l.lstrip().startswith('#')]

        for ln in lines:
            # ---------- structural equation ------------------------------------
            if "~" in ln and "=~" not in ln and ":=" not in ln:
                lhs, rhs = map(str.strip, ln.split("~", 1))

                # Pass-1: variables that belong to *true* interactions (≥2 factors)
                vars_in_interact = set()
                for term in rhs.split('+'):
                    term = term.strip()
                    m = re.match(r"\([^)]+\)\s*\*\s*(.*)", term)  # strip (par) *
                    rest = m.group(1) if m else term
                    factors = [f.strip() for f in rest.split('*')
                               if f.strip() and not re.fullmatch(r"[0-9.]+", f)]
                    if len(factors) > 1:                 # <- only real interactions
                        vars_in_interact.update(factors)

                # Pass-2: build edges / labels
                for term in rhs.split('+'):
                    term = term.strip()
                    m = re.match(r"\(([^)]+)\)\s*\*\s*(.*)", term)
                    par, rest = m.groups() if m else (None, term)
                    factors = [f.strip() for f in rest.split('*')
                               if f.strip() and not re.fullmatch(r"[0-9.]+", f)]

                    for f in factors:
                        edges.add((lhs, f))

                    if par and len(factors) == 1 and factors[0] not in vars_in_interact:
                        edge_label[(lhs, factors[0])] = par

            # ---------- latent definition --------------------------------------
            elif "=~" in ln:
                latent, rhs = map(str.strip, ln.split("=~", 1))
                latents.add(latent)
                for term in rhs.split('+'):
                    for f in map(str.strip, term.split('*')):
                        if f and not re.fullmatch(r"[0-9.]+", f):
                            edges.add((latent, f))

        dag_str = "\n".join(sorted(f"{c} <- {p}" for c, p in edges))
        nodes_role = {"Latent": sorted(latents)} if latents else {}
        return dag_str, edge_label, nodes_role



