import tidypolars4sci as tp
import networkx as nx
import re, itertools, math, inspect, textwrap
from textwrap import dedent
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
        self.__identification__ = None

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
                assert isinstance(node, str), "Check nodes_role. Node 'Outcome' must be a string or a 1-element list."

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

    def __collect_edges_properties__(self):
        self.directed   = self.__graph_dict__['directed']
        self.bidirected = self.__graph_dict__['bidirected']
        self.undirected = self.__graph_dict__['undirected']


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

    def set_nodes_role(self, nodes_role):
        res = DAG(graph=self.__graph_str_parsed__,
                  nodes_role=nodes_role,
                  nodes_label=self.nodes_label,
                  nodes_position=self.nodes_position,
                  edge_label=self.edge_label,
                  data=self.data)
        return res

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
                                causal_probability='maybe',
                                assumptions_show=False,
                                assumptions_verbose=False,
                                silent=False):
        """
        causal_probability: str
            If 'always', always compute it; if 'maybe', compute it
            only if there is not identification by adjustment for
            total_effect_adj_set effect
        """
        assert not outcome or isinstance(outcome, str), 'Outcome must be a string.'
        assert not exposure or (isinstance(exposure, str) or isinstance(exposure, list)), 'Exposure must be a string or list.'

        exposure = exposure or self.exposure
        outcome = outcome or self.outcome[0]

        assert exposure is not None, "Exposure must be provided."
        assert outcome is not None, "Outcome must be provided."

        self.__identification__ = identification(G=self,
                                                 exposure=exposure,
                                                 outcome=outcome,
                                                 adj_set = adj_set,
                                                 causal_probability=causal_probability)

        if assumptions_show:
            print(textwrap.dedent("""\
            Assumptions for identification:
            ------------------------------"""))
            self.__identification__.get_assumptions('identification', verbose=assumptions_verbose)
            print('\n')

        return self.__identification__
        
    @property
    def identification(self):
        if not self.__identification__:
            self.identification_analysis(silent=True)
        return self.__identification__

    def assumptions(self, category=None, verbose=False):
        self.identification.get_assumptions(category=category, verbose=verbose)

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

    def mediators(self, as_string=False):
        paths = self.paths(directed=True)
        paths = [p.split('->') for p in paths]
        exposure = self.exposure
        outcome = self.outcome
        res = []
        for path in paths:
            res += [[var.strip() for var in path if var.strip() not in  exposure + outcome]]
        res = [l for l in res if len(l)>0]

        if as_string:
            res = f"[{', '.join([f"{{{', '.join(l) }}}" for l in res])}]"
        return res
        

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
        Without functional form assumptions_show, for observational equivalence:
        - Necessary condition: both SCMs have the same set of conditional independencies
        - Sufficient condition: both SCMs are in the same markov equivalence class (Pearl, 2009)
        - Basically, two SCMs are observationally equivalent iff their causal graphs belong
          to the same Markov equivalence class — i.e., they share the same skeleton and v-structures.

        With functional form assumptions_show
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

    def plot_identification(self,
                            id_info='summary',
                            show_np = True,
                            show_linear = True,
                            show_do = True,
                            kws_graph={},
                            kws_identification={},
                            figsize=[10, 6],
                            ratio=[2.3, .7],
                            *args,
                            **kws
                            ):
        roles = ['Exposure', 'Outcome', 'Latent', 'Observed',
                 'exposure', 'outcome', 'latent', 'observed']
        for role in roles:
            assert not kws_graph.get(role, None) and not kws_identification.get(role, None), (
                f"Setting node role ({role}) not allowed in the plot kws. "+
                f"To set the node role, create a new DAG or use set_node_role before plotting.")

        if kws_identification:
            self.identification_analysis(**kws_identification)
            
        return self.identification.plot(G=self,
                                        id_info=id_info,
                                        show_np = show_np,
                                        show_linear = show_linear,
                                        show_do = show_do,
                                        figsize=figsize,
                                        ratio=ratio,
                                        kws_graph=kws_graph,
                                        *args,
                                        **kws
                                        )
    
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

class identification():

    def __init__(self, *args, **kws):
        self.identification = None
        self.identification_analysis(self, *args, **kws)
        self.__assumptions__()

    def __assumptions__(self):
        self.assumptions = {
            "assumptions": {
                # identification
                "correct_dag": {
                    "name"       : "Correct DAG",
                    "usage"      : ["identification"],
                    "definition" : "DAG structure matches the true causal relations, with no arrow omitted or unduly included",
                    "scape"      : "Connects reality and the DAG model",
                    "role"       : "Ensures adjustment sets and do-calculus give the correct identifiable causal effect.",
                    "violation"  : "Biased/invalid causal effect estimates and wrong adjustment sets.",
                    "notes"      : "A prerequisite for identifiability claims conditional on a DAG.",
                    'required'   : 'yes',
                    'testable'   : 'no',
                },
                "no_unmodeled_causes": {
                    "name"       : "No unmodeled causes (causal sufficiency)",
                    "usage"      : ["identification"],
                    "definition" : ("All direct and indirect common causes of variables in the DAG are included in the DAG"+
                                    " either as observed or latent nodes (no unmodeled causes)."),
                    "scope"      : "Connects reality and the DAG model",
                    "role"       : "Enables back-door/front-door adjustment or perform do-calculus on observables.",
                    "violation"  : "Confounding bias; causal effects not identifiable.",
                    "aliases"    : ["Causal Sufficiency"],
                    'required'   : 'yes',
                    'testable'   : 'no',
                },
                # identification and discovery
                "causal_markov_condition": {
                    "name"       : "Causal Markov Condition (CMC)",
                    "usage"      : ['identification', 'discovery'],
                    "definition" : "Each variable is independent of its non-descendants given its parents",
                    "scope"      : "Connects the DAG and distribution of each variable",
                    "role"       : "Links d-separation to conditional independencies, grounding do-calculus.",
                    "violation"  : "Graph–distribution link breaks and identification results may be incorrect.",
                    'required'   : 'yes',
                    'testable'   : 'no',
                },
                # identification and estimation
                "positivity": {
                    "name"       : "Positivity (Overlap)",
                    "usage"      : ['identification', "estimation", 'inference'],
                    "definition" : ("Each treatment level has positive probability to occur at all relevant levels"+
                                    " of the adjustment variables."),
                    "scope"      : "Distribution",
                    "role"       : "Required for g-formula, IPW, and many identification/estimation strategies.",
                    "violation"  : "Effects undefined or non-estimable for regions of covariate space.",
                    "aliases"    : ["Overlap", "Common Support"],
                    "notes"      : "Check e(X|Z) bounds for binary treatment; diagnose with support plots.",
                    'required'   : 'yes',
                    'testable'   : 'no',
                },

                # discovery
                "faithfulness": {
                    "name"       : "Faithfulness (Stability)",
                    "usage"      : ["discovery"],
                    "definition" : "All and only the CIs in the data arise from d-separation in the DAG (no fine-tuned cancellations).",
                    "scope"      : "Connects distribution of variables and the DAG",
                    "role"       : "Not required if the DAG is known; crucial for learning structure from data.",
                    "violation"  : "Multiple DAGs can explain the same CI pattern; discovery becomes ambiguous.",
                    "aliases"    : ["Stability", "No-fine-tuning"],
                    "notes"      : "Often assumed by PC/FCI; can fail in measure-zero parameter settings or symmetric systems.",
                    'testable'   : 'no',
                },

            },
        }

    def get_assumptions(self, category=None, verbose=False):
        """
        Return a list of assumption entries (with keys) that include the given usage category.

        Parameters
        ----------
        category : str
            An assumption category such as 'identification', 'discovery', 'estimation', 'inference'.

        Returns
        -------
        Print assumptions
        If no matches are found, returns list of categories
        """
        category = (category or "").strip().lower()

        # collect categories
        categories = []
        for assumption, details in self.assumptions['assumptions'].items():
            categories += details['usage']
        categories = set(categories)
                
        # collect
        if category in categories:
            result = []
            for key, entry in self.assumptions.get("assumptions", {}).items():
                if category in [u.lower() for u in entry.get("usage", [])]:
                    result.append({ "key": key, **entry })

            if verbose:
                self.__get_assumptions_print_verbose__(result)
            else:
                self.__get_assumptions_print__(result)
        else:
            print('Categories available:')
            [print(f"- {c}") for c in categories]

        return None

    def __get_assumptions_print__(self, assumptions):
        for i, assump in enumerate(assumptions):
            print(textwrap.dedent(f""" \
            {i+1}. {assump['definition']}
            """), end='')

    def __get_assumptions_print_verbose__(self, assumptions):
        for i, assump in enumerate(assumptions):
            print(textwrap.dedent(f""" \
            {i+1}. {assump['name']}
               - Definition: {assump.get('definition', '')}
               - Role: {assump.get('role', '')}
               - Scope: {assump.get('scope', '')}
               - Usage: {', '.join(assump.get('usage', ''))}
               - Violation: {assump.get('violation', '')}
            """), end='')

    # dagitty (R dependencies)
    def identification_analysis(self, *args, **kws):
        """
        causal_probability: str
            If 'always', always compute it; if 'maybe', compute it
            only if there is not identification by adjustment for
            total_effect_adj_set effect
        """
        G=kws.get("G", None)
        exposure=kws.get("exposure", None)
        outcome=kws.get("outcome", None)
        adj_set=kws.get("adj_set", None)
        causal_probability=kws.get("causal_probability", 'maybe')

        assert not outcome or isinstance(outcome, str), 'Outcome must be a string.'
        assert not exposure or (isinstance(exposure, str) or isinstance(exposure, list)), 'Exposure must be a string or list.'

        exposure = exposure or G.exposure
        outcome = outcome or G.outcome[0]

        assert exposure is not None, "Exposure must be provided."
        assert outcome is not None, "Outcome must be provided."

        # identification by adjustment 
        # ----------------------------
        adj = {}
        for effect in ['direct', 'total']:
            adj[effect] = self.__identification_analysis_adj__(G, exposure, outcome, effect)

        # causal probability  (only not possible to use adjustment or explicitly asked)
        # ------------------
        total_identified = adj['total']['identified']
        do = {}
        if not total_identified or causal_probability=='always':
            do['total'] = self.__identification_analysis_do__(G, exposure, outcome, adj_set)
            
        # collect results 
        # ---------------
        res = {'Adjustment variables':adj, 'do-calculus':do}
        
        self.identification = res 

    def __identification_analysis_adj__(self, G, exposure, outcome, effect):
        adj_set = dagitty.adjustmentSets(G.__dagitty__,
                                         exposure = exposure,
                                         outcome = outcome,
                                         effect=effect
                                         )

        adj_set    = None if len(adj_set)==0 else list(adj_set.rx2['1'])
        adj_set    = [''] if adj_set==[] else adj_set
        identified = True if adj_set is not None else False
        f, f_np, latex_parametric, latex_non_parametric = self.__identification_analysis_adj_formula__(identified, outcome,
                                                                                                       exposure, adj_set)

        # direct
        has_mediators = len(G.mediators())>0
        if effect=='direct':
            tau_name = 'Average Controlled Direct Effect (ACDE)'
            c     = 'ACDE'
            d0    = "d'"
            d1    = "d"
            m     = ', m' if  has_mediators  else ""
            Yi1_l = f'Y_i({d1+m})'
            Yi0_l = f'Y_i({d0+m})'
            Yi1   = Yi1_l.replace("_", '')
            Yi0   = Yi0_l.replace("_", '')

            adj   = True if adj_set and adj_set != [''] else False
            Z     = ", Z" if adj else ''
            Zstr  = f"Z = {', '.join(adj_set)}" if Z else None

            med   = True if has_mediators else False
            M     = ', M=m' if  med  else ""
            Mstr  = f"M = {G.mediators(as_string=True)}" if med else None


        tau = f"E[{Yi1} - {Yi0}]"
        Esoo= f"E[{Yi1}] = E[Y | D={d1+M+Z}]"


        # tau     = f"tau_{{{c}}}({d}) = {E} "
        # tau_soo = f"tau_{{{c}}}^{{SoO}}({d}) = \\mathbb{E}_{Z}[Eid] - \\mathbb{E|_{Z}[E[Y | D=d', M=m, Z]]"

        #     tau_latex   = "$\\tau_{\\text{ACDE}}(d, d', m) = \\mathbb{E}\\left[Y_i(d, m) - Y_i(d', m)\\right]$"
        #     tau_soo_latex = ("$\\tau_{\\text{ACDE}}^{\\text{SoO}}(d, d', m) " +
        #                      "= \\mathbb{E}_{{Z}}\\left[\\mathbb{E}[Y | D=d, M=m, Z]\\right]" +
        #                      " - \\mathbb{E}_{{Z}}\\left[\\mathbb{E}[Y | D=d', M=m, Z]\\right]$")


        # total
        effect_name_total = 'Average Causal Effect (ACE)' if effect=='total' else None

        tau_ace = "tau_{ACDE}^{SoO}(d, d') = \\mathbb{E}_{Z}[E[Y | D=d, Z]] - \\mathbb{E|_{Z}[E[Y | D=d', Z]]"


        effect_name = tau_acde_name or effect_name_total
        tau = tau_acde or tau_total

        res = {'outcome'                : outcome,
               'exposure'               : exposure,
               "identified"             : identified,
               "adj_set"                : adj_set,
               "formula"                : f,
               "formula_np"             : f_np,
               "latex_parametric"       : latex_parametric,
               "latex_non_parametric"   : latex_non_parametric,
               "effect_name"            : effect_name,
               'tau'              : tau,
               'tau_latex'        : tau_latex,
               }
        return res

    def __identification_analysis_adj_formula__(self, identified, outcome, exposure, adj):

        if not identified:
            f = None
            f_np = None
            latex_parametric = None
            latex_non_parametric = None
        else:
            d = ' + '.join([exposure] if isinstance(exposure, str) else exposure)
            X = ' + '.join(adj or [''])
            Xnp = ', '.join(adj or [''])
            y = outcome
            f    = f"{y} ~ {d} + {X}"
            f_np = f"{y} ~ f({d})" if not X else f"{y} ~ f({d}, {Xnp})"

            d = [exposure] if isinstance(exposure, str) else exposure
            beta_dTd = ' + '.join([f"\\beta_{{{di}}}{di}" for di in d])
            beta_xTX = ' + '.join([f"\\beta_{{{x}}}{x}" for x in adj or ['']])
            latex_parametric = f"E[{y} \mid \cdot] = \\beta_0 + {beta_dTd} + {beta_xTX}"

            d = ', '.join([exposure] if isinstance(exposure, str) else exposure)
            latex_non_parametric = f"E[{y} \mid \cdot] = f({d}, e)" if not X else f"{y} = f({d}, {Xnp}, e)"

        return f, f_np, latex_parametric, latex_non_parametric

    def __identification_analysis_do__(self, G, exposure, outcome, adj_set):
        X = ', '.join(G.get_nodes())
        Y = outcome
        D = ', '.join(exposure) if isinstance(exposure, list) else exposure
        Z = ', '.join(adj_set) if isinstance(adj_set, list) else adj_set

        p = f"p({X})"
        q = f"p({Y} | do({D}))" if Z is None else f"p({Y} | do({D}), {Z})"
        causal_probability = dosearch.dosearch(p, q, G.__dagitty__)
        causal_probability = causal_probability.rx2['formula'][0] \
            if bool(causal_probability.rx2['identifiable'][0]) else None

        # formulas
        if causal_probability is not None:
            formula = causal_probability.replace('\\left(', ' ')\
                                        .replace('\\right)', '')\
                                        .replace('\\', '')
            formula = f"{q} = {formula}"
            latex = f"{q} = {causal_probability}"
        else:
            formula = None
            latex = None

        identified = True if causal_probability is not None else False

        effect_name = 'Average Causal Effect (ACE)' if not adj_set else 'Conditional Average Causal Effect (CACE)'

        res = {'outcome'        : outcome,
               'exposure'       : exposure,
               "identified"     : identified,
               "adj_set"        : adj_set,
               "formula"        : formula,
               "latex"          : latex,
               "non_parametric" : latex,
               "effect_name"    : effect_name,
               }
        return res

    def details(self):
        for id_type, results in self.identification.items():
            if id_type!='do-calculus':
                self.__repr_adj_details__(results) 
            else:
                self.__repr_do_details__(results) 
        return None

    def get_dict(self):
        return self.identification

    def plot(self, kws_graph, *args, **kws):

        default_usetex = plt.rcParams["text.usetex"] 
        plt.rcParams["text.usetex"] = True
        plt.rcParams['text.latex.preamble'] = r'\usepackage{amsmath, amssymb, siunitx, bm}'

        G = kws.get("G", None)
        y_do = kws.get("y_do", True)
        ratio = kws.get("ratio", True)
        figsize = kws.get("figsize", [10, 6])
        ratio = kws.get("ratio", [10, 6])

        fig, axs = plt.subplots(nrows=2, ncols=1, figsize=figsize, tight_layout=True,
                                gridspec_kw={'height_ratios': ratio})
        # Graph 
        # -----
        ax = axs[0]
        G.plot(ax=ax, **kws_graph)
        ax = axs[1]

        # identification 
        # --------------
        details = kws.get("id_info", 'summary')
        kws.pop('details', None)
        if details=='summary':
            ax = self.__plot_summary__(ax=ax, *args, **kws)
        else:
            self.__plot_equations__(ax=ax, *args, **kws)
            
        plt.axis("off")
        plt.tight_layout()
        plt.show()
        plt.rcParams["text.usetex"] = default_usetex

        return plt, axs

    def __plot_summary__(self, ax, *args, **kws):
        G = kws.get("G", None)
        y_do = kws.get("y_do", True)
        ratio = kws.get("ratio", True)

        show_np = kws.get("show_np", True)
        show_linear = kws.get("show_linear", True)
        show_do = kws.get("show_do", True)


        # collect text 
        # ------------
        id = G.identification.get_dict()
        adj = id['Adjustment variables']
        do  = id['do-calculus']

        # adjustment (non-parametric)
        txt = ''
        if adj['total']['identified'] or adj['direct']['identified']:
            for effect in ['total', 'direct']:
                if adj[effect]['identified']:
                    txt += f"{effect.title()} effect: ${adj[effect]['latex_non_parametric']}$\n"
                else:
                    txt += "\\textit{(Not identified by adjustment)}\n"
        else:
            txt += "\\textit{(Not identified by adjustment)}\n"
            non_parametric = "\\textbf{Identification by adjustment:}\n" + txt


        # adjustment (non-parametric)
        txt = ''
        if adj['total']['identified'] or adj['direct']['identified']:
            for effect in ['total', 'direct']:
                if adj[effect]['identified']:
                    txt += f"{effect.title()} effect: ${adj[effect]['latex_parametric']}$\n"
                else:
                    txt += "\\textit{(Not identified by adjustment)}\n"
        else:
            txt += "\\textit{(Not identified by adjustment)}\n"
            parametric = "\\textbf{Identification by adjustment under linearity and no interaction:}\n" + txt

        # do
        txt = ''
        if do:
            if do['total']['identified']:
                do = do['total']
                if do['adj_set']:
                    conditional = [do['adj_set']] if isinstance(do['adj_set'], str) else do['adj_set']
                    conditional = f" (conditional on {', '.join(conditional)})"
                else:
                    conditional = ''
                    txt += f"Total effect causal probability {conditional}:\n ${do['latex']}$" 
            else:
                txt += "Total effect causal probability: \n\\textit{(Not identified)}\n"
        else:
            txt += "\\textit{(Analysis not conducted. Identification by adjustment available.)}\n"
            causal_probability = ("\\textbf{Identification by do-calculus:}\n" + txt)

        # plot 
        # ----
        x_left = 0.01
        x_right = 0.99
        y_top = .9
        y_bottom = .001
        if show_np:
            ax.text(x_left, y_top, s=non_parametric,
                    ha='left', va='top', ma='left',
                    fontdict=dict(weight='normal', style='normal',
                                  color='black', fontsize=12, alpha=1),
                    transform=ax.transAxes
                    )
        if show_linear:
            x = x_right if show_np else x_left
            ha = 'right' if show_np else 'left'
            ma = 'right' if show_np else 'left'
            ax.text(x, y_top, s=parametric,
                    ha=ha, va='top', ma=ma,
                    fontdict=dict(weight='normal', style='normal',
                                  color='black', fontsize=12, alpha=1),
                    transform=ax.transAxes
                    )
        if show_do:
            y  = y_bottom if (show_linear or show_np) else y_top
            va = 'bottom' if (show_linear or show_np) else 'top' 
            ax.text(x_left, y, s=causal_probability,
                    ha='left', va=va, ma='left',
                    fontdict=dict(weight='normal', style='normal',
                                  color='black', fontsize=12, alpha=1),
                    transform=ax.transAxes
                    )
        if not (non_parametric or parametric or causal_probability):
            txt = "\\textit{Direct and total effects not identifiable.}"
            ax.text(x_left, y_top, s=txt,
                    ha='left', va='top', ma='left',
                    fontdict=dict(weight='normal', style='normal',
                                  color='black', fontsize=12, alpha=1),
                    transform=ax.transAxes
                    )
            
        # Splines (axes lines)
        for side in ['bottom', 'left', 'right', 'top']:
            ax.spines[side].set_visible(True)
            ax.spines[side].set_linewidth(1.3)
            ax.tick_params(top=False, bottom=False, left=False, right=False,
                           labeltop=False, labelbottom=False, labelleft=False, labelright=False)

        return ax

    def __tidy__(self):
        pass
    
    def __str__(self):
        self.__repr__()
        return ''

    def __repr__(self):
        direct = self.identification['Adjustment variables']['direct']
        total =  self.identification['Adjustment variables']['total']
        do =  self.identification["do-calculus"]

        print(f"Exposure (cause): {direct['exposure']}\n"+
              f"Outcome (effect): {direct['outcome']}\n")

        self.__repr_adj__(direct, total)
        self.__repr_do__(do)
        return ''

    def __repr_adj__(self, direct, total):
        txt = dedent("""
        Identification method: Adjustment variables
        ---------------------\
        """)
        for result in [direct, total]:
            txt += dedent(f"""
            Causal effect: {result['effect_name']}
            Identified: {result['identified']}
            Adjustment set: {result['adj_set']}
            """)
        print(txt)

    def __repr_do__(self, result):
        txt = dedent("""\
        Identification method: do-calculus
        ---------------------
        """)
        if result:
            result = result['total']
            txt += dedent(f"""\
            Causal effect: {result['effect_name']}
            Identified: {result['identified']}
            Causal probability: {result['formula']}
            """)
        else:
            txt += "Analysis not conducted. Identification by adjustment available."
        print(txt)
            
    def __repr_adj_details__(self, results):
        print("TBD")

    def __repr_do_details__(self, results):
        print("TBD")

        
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
            'LSEM': use linear structural equation models
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
        pass

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
    
    def __assumptions__(self):
        assumptions = {
            # estimation, and inference
            "functional_form": {
                "name"       : "Functional Form Assumptions",
                "usage"      : ['estimation', 'inference'],
                "definition" : ("Parametric/semi-parametric restrictions (e.g., linearity, additivity, "+
                                "monotonicity, non-Gaussian noise)."),
                "level"      : "Distributional parameterization",
                "role"       : "Adds leverage for identification/orientation (e.g., LiNGAM) or consistent estimation.",
                "violation"  : "Misspecification bias; identifiability/orientation results may fail.",
                "examples"   : ["Linearity (LSEM)", "Additive noise (ANM)", "Non-Gaussian errors (LiNGAM)", "Monotonicity"],
                "notes"      : "Helpful for both discovery (edge orientation) and identification (parameter identifiability)."
            }
            }
            
