import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="rpy2.rinterface")
# 
from . import utils as ut
from .models import lsem
from .options import get_options
from .tau import *
# 
import tidypolars4sci as tp
import networkx as nx
import re, itertools, math, inspect, textwrap
from textwrap import dedent
import numpy as np
from scipy.stats import norm as dnorm
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from collections import defaultdict
# for examples
import difflib
# R packages/dependencies
from tools4sci.cypher import convert
from rpy2.robjects.packages import importr
from rpy2.robjects import NULL
# 
dagitty = importr("dagitty")
dosearch = importr("dosearch")

__all__ = ['DAG', 'estimate', 'examples']

class DAG:
    """
    Initialize a directed acyclic graph (DAG) representation.

    Parameters
    ----------
    graph: (str, dict, list)
        A string with the a graph, or a list or dictionary with the edges

        String
        ------
        If string, it can have different formats
            X -> Y  : directed edge from X to Y
            X -- Y  : undirected edge between X and Y
            X <-> Y : bidirected edge between X and Y

        Example 1:

            '''
            X1 -> Y
            X1 -> Z -> Y
            X1 <- X2
            '''

        Example 2: The following three versions are acceptable and produce the same graph:

            Version 1
            '''
            X1 -> A
            X1 -> B
            X2 -> C
            X2 -> D
            '''

            Version 2
            '''
            X1 -> {A, B}
            {C, D} <- X2
            '''

            Version 3
            '''
            X1 -> {A, B}
            X2 -> {C, D}
            '''

        Example 3 (comments are allowed and automatically ignored when creating the graph):
            '''
            # bidirected edge
            X3 <-> X4
            X3 -- X4  # undirected edge
            X5 -- X6 -> X7
            '''

        List
        ----
        If list, the edge types will be parsed based on their format:
    
            [
                ('X', 'Y'),                    # becomes X -> Y  (directed edge)
                {'X', 'Z'},                    # becomes X -- Y  (undirected edge)
                (('X1', 'X2'), ('X2', 'X1')),  # becomes X <-> Y (bidirected edge)
            ]

        Dict
        ----
        If dictionary, it must contains the edges as elements and the
        edge type (directed, undirected, bidirected) as keys. Example:

            {
                 'directed'  : [('X', 'Y'), ...],  # list of tuples
                 'undirected': [{'X1', 'X2'}, ...] # list of dictionaries
                 'bidirected': [ (('X1', 'X2'), ('X2', 'X1')), ...] # list of 2-tuple tuples
             }

        See more examples below.
    
    data : DataFrame-like or None, optional
        Observational data to retain alongside the graph for downstream
        identification tasks. The data is stored without validation.

    nodes_role : dict[str, Sequence[str]] or None, optional
        Keys should be node role names (e.g., ``'Exposure'``, ``'Outcome'``,
        ``'Latent'``) and values a string or list with the node names.
         Lowercase role keys for ``'Exposure'``, ``'Outcome'``, and
        ``'Latent'`` are automatically promoted to their capitalized equivalents.

    nodes_label : dict[str, str] or None, optional
        Labels for graph nodes. Keys should be node names, values their labels.
        Latex expression is accepted.

    nodes_position : dict[str, tuple[float, float]] or None, optional
        Layout coordinates for nodes. Keys should be node names, values 
        (x, y) coordinate tuples.

    edge_label : dict or None, optional
        Custom labels for edges. Keys should be edge, values the
        edge labels. Latex expression is accepted. See examples below.

    Examples
    --------
    >>> # basic settings
    >>> pos = {'D': (0,0),
    >>>        'Y': (1,0),
    >>>        'Z': (.5, -1),
    >>>        'M1': (.25, 1),
    >>>        'M2': (.75, 1),
    >>>        'M3': (1.75, 1),
    >>>        }
    >>> roles = {'Exposure'    : "D",
    >>>          'Outcome'     : "Y",
    >>>          "Latent"      : 'Z',
    >>>          "The M2 node" : "M2" # arbtiraty roles available
    >>>          }
    >>> node_labels = {"D": "$\widetilde{D}$",
    >>>           'Y': "Outcome"}
    >>> edge_labels = {
    >>>     # directed edge labels
    >>>     ('D', 'M1') : 1,
    >>>     ('M2', 'Y') : -1,
    >>>     ('M3', 'Y') : 'a',
    >>>     ('D', 'Y') : 'AbC',
    >>>     ('Z', 'D') : '$\\beta$',
    >>>     ('Z', 'Y'): 'asccc',
    >>>     # bidirected edge label
    >>>     (('D', 'Y'), ('Y', 'D')): '$f(x)=\\alpha$',
    >>>     # undirected edge label
    >>>     ( 'M1', 'M2' ) : 1234, # 
    >>>     ( 'M2', 'M1' ) : 1234, # 
    >>> }
    >>> 
    >>> 
    >>> # using string
    >>> # ------------
    >>> dag  = '''
    >>> D -> M1 
    >>> M1 -- M2
    >>> M2 -> Y
    >>> M3 -> Y
    >>> D <-> Y
    >>> D  -> Y
    >>> Z -> {D, Y}
    >>> '''
    >>> Gs = gcm.DAG(dag, nodes_role=roles, nodes_position=pos, nodes_label=node_labels, edge_label=edge_labels)
    >>> Gs.plot()
    >>> 
    >>> # using a list
    >>> # ------------
    >>> dag  =[('D', 'M1'), 
    >>>        ('M3', 'Y'), 
    >>>        ('M2', 'Y'), 
    >>>        ('D', 'Y'), 
    >>>        ('Z', 'D'), 
    >>>        ('Z', 'Y'), 
    >>>        (('D', 'Y'), ('Y', 'D')), 
    >>>        {'M2', 'M1'}
    >>>        ]
    >>> Gl = gcm.DAG(dag, nodes_role=roles, nodes_position=pos, nodes_label=labels, edge_label=edge_label)  # 
    >>> Gl.plot()
    >>> 
    >>> # using a dict
    >>> # ------------
    >>> dag = {
    >>>     'directed': [
    >>>         ('D', 'M1'), 
    >>>         ('M3', 'Y'), 
    >>>         ('M2', 'Y'), 
    >>>         ('D', 'Y'), 
    >>>         ('Z', 'D'), 
    >>>         ('Z', 'Y')
    >>>     ], 
    >>>     'bidirected': [
    >>>         (('D', 'Y'), ('Y', 'D'))
    >>>     ], 
    >>>     'undirected': [
    >>>         {'M2', 'M1'}
    >>>     ]
    >>> }      
    >>> Gd = gcm.DAG(dag, nodes_role=roles, nodes_position=pos, nodes_label=labels, edge_label=edge_label)  # 
    >>> Gd.plot()

    Returns
    -------
    DAG graph object
    """

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
        assert graph, "'graph' must be provided."
        assert nodes_position is None or isinstance(nodes_position, dict), (
            "nodes_position must be None or dict")
        assert nodes_label is None or isinstance(nodes_label, dict), (
            "nodes_label must be None or dict")
        assert nodes_role is None or isinstance(nodes_role, dict), (
            "nodes_roles must be None or dict")

        # deal with user provided roles in low case
        key_roles = ['Outcome', 'Exposure', "Latent"]
        if nodes_role:
            for role in  key_roles:
                if role.lower() in nodes_role.keys():
                    nodes_role[role] = nodes_role[role.lower()]
                    nodes_role.pop(role.lower())
            

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

    # manipulating graph  -----------------------------
    def get_nodes(self, exclude_latent=False):
        """
        Return the graph node names, optionally omitting latent variables.

        Parameters
        ----------
        exclude_latent : bool, optional
            If ``True``, latent nodes are excluded from the returned list.
            Defaults to ``False``.

        Returns
        -------
        list[str]
            Node names in the current graph. The order corresponds to the
            insertion order preserved in ``self.nodes``.
        """
        nodes = list(self.nodes)
        latent_nodes = self.latent

        if exclude_latent and latent_nodes:
            nodes = [n for n in nodes if n not in latent_nodes]
        return nodes

    def set_node_label(self, nodes_label):
        """
        Update display labels for one or more nodes.

        Parameters
        ----------
        nodes_label : dict[str, str]
            Mapping from node names to their new label strings.

        Examples
        --------
        >>> dag = DAG(graph="X -> Y")
        >>> dag.set_node_label({"X": "Treatment (X)", "Y": "Outcome (Y)"})
        """
        for node, label in nodes_label.items():
            self.nodes_label[node] = label

    def set_nodes_role(self, nodes_role):
        """
        Create a new DAG instance with updated node roles.

        Parameters
        ----------
        nodes_role : dict[str, Sequence[str]]
            Keys should be node role names (e.g., ``'Exposure'``, ``'Outcome'``,
            ``'Latent'``) and values a string or list with the node names.
             Lowercase role keys for ``'Exposure'``, ``'Outcome'``, and
            ``'Latent'`` are automatically promoted to their capitalized equivalents.

        Returns
        -------
        DAG
            A fresh `DAG` object reflecting the new role assignments.

        Examples
        --------
        >>> dag = DAG(graph="X -> Y")
        >>> updated = dag.set_nodes_role({"Exposure": ["X"], "Outcome": ["Y"]})
        >>> updated
        Graph:
        X -> Y
        Observed: 
        Exposure: X
        Outcome: Y
        >>> updated.exposure
        ['X']
        """
        res = DAG(graph=self.__graph_str_parsed__,
                  nodes_role=nodes_role,
                  nodes_label=self.nodes_label,
                  nodes_position=self.nodes_position,
                  edge_label=self.edge_label,
                  data=self.data)
        return res

    def set_node_position(self, position):
        """
        Assign layout coordinates to nodes in-place.

        Parameters
        ----------
        position : dict[str, tuple[float, float]]
            Mapping from node names to (x, y) coordinate tuples.
            Keys should be the node name, the value its position.

        Examples
        --------
        >>> G = DAG(graph="X -> Y")
        >>> G.set_node_position({"X": (0.0, 0.5), "Y": (1.0, 0.5)})
        """
        for node, p in position.items():
            self.position[node] = p

    def edge_add(self, edge):
        """
        Add an edge to the graph if it is not already present.

        Parameters
        ----------
        edge : tuple[str, str] or tuple[tuple[str, str], tuple[str, str]] or set[str]
            Edge specification compatible with the formats accepted at
            initialization. Use a two-tuple for directed edges, a set with two
            nodes for undirected edges, or a pair of directed tuples for
            bidirected edges.

        Returns
        -------
        DAG
            The current instance when the edge already exists; otherwise a new
            `DAG` instance containing the added edge.

        Examples
        --------
        >>> G = DAG(graph="X -> Y")
        >>> G = G.edge_add(("Y", "Z"))
        >>> ("Y", "Z") in G.directed
        True
        """
        res = self
        if not self.edge_exist(edge):
            graph = self.__graph_list__.copy()
            graph.append(edge)
            res = self.__rebuild_graph__(graph)
        return res

    def edge_remove(self, edge):
        """
        Remove an existing edge from the graph when present.

        Parameters
        ----------
        edge : tuple[str, str] or tuple[tuple[str, str], tuple[str, str]] or set[str]
            Edge specification matching one of the accepted formats. The check
            is insensitive to direction for bidirected and undirected edges.

        Returns
        -------
        DAG
            A new `DAG` instance with the edge removed when the edge exists;
            otherwise the current instance is returned unchanged.

        Examples
        --------
        >>> G = DAG(graph="X -> Y")
        >>> G = G.edge_remove(("X", "Y"))
        >>> ("X", "Y") in G.directed
        False
        """
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
        """
        Replace an existing edge with a new one in a single operation.

        Parameters
        ----------
        remove : tuple[str, str] or tuple[tuple[str, str], tuple[str, str]] or set[str]
            Edge specification to be removed. Formats follow the accepted edge
            types for the graph and support undirected and bidirected symmetry.

        add : tuple[str, str] or tuple[tuple[str, str], tuple[str, str]] or set[str]
            Edge specification to be added after removal.

        Returns
        -------
        DAG
            A `DAG` instance reflecting the requested change. If the removal
            fails because the edge does not exist, the method still returns the
            result of attempting to add the new edge.

        Examples
        --------
        >>> G = DAG(graph="X -> Y")
        >>> G = G.edge_replace(("X", "Y"), ("X", "Z"))
        >>> ("X", "Y") in G.directed, ("X", "Z") in G.directed
        (False, True)
        """
        res = self.edge_remove(remove)
        res = res.edge_add(add)
        return res

    def edge_exist(self, edge, edges=None):
        """
        Check whether an edge is present in the graph (or a supplied edge list).

        Parameters
        ----------
        edge : tuple[str, str] or tuple[tuple[str, str], tuple[str, str]] or set[str]
            Edge specification to check for existence. The method canonicalizes
            the representation so that undirected and bidirected edges are
            insensitive to node order.
        edges : list or None, optional
            Specific list of edges to search. When ``None``, the method looks up
            the corresponding edge collection from the instance.

        Returns
        -------
        bool
            ``True`` when the edge is found, otherwise ``False``.

        Examples
        --------
        >>> G = DAG(graph="X -> Y")
        >>> G.edge_exist(("X", "Y"))
        True
        >>> G.edge_exist({"X", "Y"})
        False
        """
        if edges is None:
            edge_type = self.__edge_type__(edge)
            edges = self.__getattribute__(edge_type)
        edges = [edges] if not isinstance(edges, list) else edges
        edge = self.__edge_frozen_format__(edge)
        edges_in_list = {self.__edge_frozen_format__(e) for e in edges}
        return edge in edges_in_list

    def set_edge_label(self, edge_label):
        """
        Assign or update labels for one or more edges.

        Parameters
        ----------
        edge_label : dict
            Mapping of edge specifications to label values. Keys can be any
            valid edge representation accepted at initialization. Values are
            stored verbatim without validation.

        Examples
        --------
        >>> G = DAG(graph="X -> Y")
        >>> G.set_edge_label({("X", "Y"): "beta"})
        >>> G.edge_label[("X", "Y")]
        'beta'
        """
        for edge, label in edge_label.items():
            self.edge_label[edge] = label

    # computations --------------------------------------
    # dagitty (R dependencies)
    def dseparated(self, var1=None, var2=None, conditional=None):
        """
        Determine whether two variables are d-separated given a conditioning set.

        Parameters
        ----------
        var1 : str
            Name of the first variable.
        var2 : str
            Name of the second variable.
        conditional : Sequence[str] or None, optional
            Variables to condition on. Provide an iterable of node names. When
            ``None``, no conditioning is applied.

        Returns
        -------
        bool
            ``True`` if the variables are d-separated given ``conditional``,
            otherwise ``False``.

        Examples
        --------
        >>> G = DAG(graph="X -> Z -> Y")
        >>> G.dseparated("X", "Y")
        False
        >>> G.dseparated("X", "Y", conditional=["Z"])
        True
        """
        assert var1 and isinstance(var1, str), "'var1' (a str) must be provided."
        assert var2 and isinstance(var2, str), "'var2' (a str) must be provided."

        if conditional is None:
            conditional = NULL
        res = dagitty.dseparated(self.__dagitty__, X = var1, Y = var2, Z=conditional)[0]
        return res
        
    # dagitty (R dependencies)
    def dseparation(self, var1, var2):
        """
        Retrieve the list of d-separations involving two variables.

        Parameters
        ----------
        var1 : str
            Name of the first variable.
        var2 : str
            Name of the second variable.

        Returns
        -------
        list[list[str]] or None
            Conditioning sets that d-separate ``var1`` and ``var2``. Each inner
            list contains the conditioning variables as strings. Returns
            ``None`` when no separating set is found.

        Examples
        --------
        >>> G = DAG(graph="X -> Z -> Y")
        >>> G.dseparation("X", "Y")
        [['Z']]
        """
        assert var1 and isinstance(var1, str), "'var1' (a str) must be provided."
        assert var2 and isinstance(var2, str), "'var2' (a str) must be provided."

        res = self.local_independencies()
        if res.nrow>0:
            res = (
                res
                .separate('term', into=['var1', 'var2|conditional'], sep='_||_', remove=False)
                .separate('var2|conditional', into=['var2', 'conditional'], sep=' | ', remove=True)  # 
                .mutate(var1 = tp.str_trim('var1'),
                        var2 = tp.str_trim('var2'),
                        conditional = tp.str_trim('conditional'),
                        )
                .replace_null({'conditional':''})
                .filter(((tp.col("var1")==var1) & (tp.col('var2')==var2)) |
                        ((tp.col("var2")==var1) & (tp.col('var1')==var2))
                        )
            )
            res = res.pull('conditional')
            res = [s.split(',') for s in res]
            res = [[string.strip() for string in inner_list] for inner_list in res]
        else:
            print(f'Not possible to d-separate {var1} and {var2} in the graph.')
            res = None
        return res

    # dagitty (R dependencies)
    def local_independencies(self, data=None, alpha=0.05, include_sep_cols=False):
        """
        List conditional independencies implied by the DAG, optionally using data.

        Parameters
        ----------
        data : tidypolars4sci.DataFrame or None, optional
            Observational data used to perform local conditional independence
            tests through ``dagitty::localTests``. When ``None`` (default), the
            method enumerates implied independencies analytically.
        alpha : float, optional
            Significance level for converting quantile-based confidence bounds
            into standard errors. Only used when ``data`` is provided. Defaults
            to 0.05.
        include_sep_cols : bool, optional
            When ``True``, return additional columns detailing the separated
            variables and conditioning sets. Defaults to ``False``.

        Returns
        -------
        tidypolars4sci.DataFrame
            Tidy representation of the implied independencies. The result
            always includes columns ``term`` (formatted as ``"Y _||_ X | Z"``),
            ``estimate``, ``se``, ``lo``, ``hi``, and ``pvalue``. When
            ``include_sep_cols`` is ``True``, columns ``var1``, ``var2``, and
            ``cond`` are also present.

        Examples
        --------
        >>> G = DAG(graph="X -> Z -> Y")
        >>> independencies = G.local_independencies(include_sep_cols=True)
        >>> independencies.select(["term"]).to_pandas().term.tolist()
        ['Y _||_ X | Z']
        """
        if data is None:
            data = self.data
        # compute
        if data is None:
            inds = dagitty.impliedConditionalIndependencies(self.__dagitty__)
            res = tp.tibble()
            for ind in inds:
                y = ind[0][0]
                x = ind[1][0]
                z = ind[2]
                term = f"{y} _||_ {x}"
                term = f"{term} | {', '.join(z)}" if z else term
                tmp = tp.tibble({'term': [term],
                                 "var1": [y],
                                 "var2": [x],
                                 "cond": [z]})
                res = res.bind_rows(tmp)
            inds = res
        else:
            inds = dagitty.localTests(self.__dagitty__, data=convert().tp2tibble(data), abbreviate_names=False)
            z = dnorm.ppf(1-alpha/2)
            inds = convert().rtibble2tp(inds, rownames2col='term')\
                         .rename({'p.value':"pvalue",
                                  '2.5%':'lo',
                                  '97.5%':'hi',
                                  })\
                         .mutate(se = ( tp.col('hi')-tp.col('lo') ) / (2*z) )
            if inds.nrow>0:
                inds = (
                    inds
                    .separate('term', into=['var1', 'var2_cond'], sep='_||_', remove=False)
                    .separate('var2_cond', into=['var2', 'cond'], sep='|')
                )

        vars = ['term', 'estimate', 'se', 'lo', 'hi', 'pvalue']
        if include_sep_cols:
            vars += ['var1', 'var2', 'cond']
        inds = inds.select(vars)

        return inds
        
    # dagitty (R dependencies)
    def identification_analysis(self, exposure=None, outcome=None,
                                conditional = None,
                                causal_probability='maybe',
                                iv='maybe',
                                verbose=True
                                ):
        """
        Run identification analysis for the specified exposure-outcome pair.

        Parameters
        ----------
        exposure : str or list[str] or None, optional
            Exposure variable(s) of interest. When ``None``, the current DAG
            exposure roles are used.
        outcome : str or None, optional
            Outcome variable. Defaults to the first DAG outcome role when
            omitted.
        conditional : str or list[str] or None, optional
            Variables to condition the causal effect on. Strings are promoted to
            single-element lists.
        causal_probability : {'always', 'maybe'}, optional
            Controls whether causal probabilities are computed. With ``'maybe'``
            (default) probabilities are evaluated only when identification by
             adjustment fails; ``'always'`` forces computation.
        iv : {'always', 'maybe'}, optional
            Identification using instrumental variable. Use ``'maybe'`` (default)
            to run analysis only when identification by
             adjustment fails; use ``'always'`` to force IV evaluation.
        verbose : bool, optional
            When ``True`` (default), results are printed via ``self.print``.

        Returns
        -------
        None

        Notes
        -----
        Results printed and can be retrieved using <DAG>.identification
        and <dag>.print(). See examples.

        Examples
        --------
        >>> G = DAG(graph="X -> Y")
        >>> G.identification_analysis(exposure="X", outcome="Y", verbose=False)
        >>> G.identification_analysis(exposure="X", outcome="Y", verbose=False)

        >>> G.identification()        # to print
        >>> G.print('identification') # to print
        >>> G.identification_dict     # dictionary
        """
        assert not outcome or isinstance(outcome, str), 'Outcome must be a string.'
        assert not exposure or (isinstance(exposure, str) or isinstance(exposure, list)), 'Exposure must be a string or list.'

        assert outcome or self.outcome, "No outcome found."
        assert exposure or self.exposure, "No exposure found."

        exposure = exposure or self.exposure
        outcome = outcome or self.outcome[0]
        conditional = [conditional] if isinstance(conditional, str) else conditional

        assert exposure is not None, "Exposure must be provided."
        assert outcome is not None, "Outcome must be provided."

        self.__identification__ = identification(G=self,
                                                 exposure = exposure,
                                                 outcome = outcome,
                                                 conditional = conditional,
                                                 causal_probability = causal_probability,
                                                 iv = iv,
                                                 verbose=verbose)
        if verbose:
            self.print('identification')

        return None

    def get_identified(self, by='parameter', include_all=False):
        """
        Retrieve identification results summarised by parameter or strategy.

        Parameters
        ----------
        by : {'parameter', 'strategy'}, optional
            Grouping used for the returned results. Defaults to ``'parameter'``.
        include_all : bool, optional
            When ``True``, include all strategies that identify the parameters.
            Otherwise, only the SoO, or IV, or do-calculus, whatever
            identifies it first. Defaults to ``False``.

        Returns
        -------
        dict

        Examples
        --------
        >>> G = DAG(graph="X -> Y")
        >>> G.identification_analysis(exposure="X", outcome="Y", verbose=False)
        >>> G.get_identified()
        """
        if not self.__identification__:
            self.identification_analysis()
        res = self.__identification__.get_identified(by=by, include_all=include_all)
        return res

    def identification(self, print='default', parameter='ACE', *args, **kws):
        """
        Print identification analysis using custom output options.

        Parameters
        ----------
        print : str, optional
            Content selector forwarded to the identification printer. Defaults
            to ``'default'``.
        parameter : str, optional
            Target causal parameter to display, e.g., ``'ACE'`` (default).
        *args :
            Additional positional arguments forwarded to ``self.print``.
        **kws :
            Keyword arguments supporting an ``identification`` dictionary that
            overrides default print options.

        Returns
        -------
        None

        Examples
        --------
        >>> G = DAG(graph="X -> Y")
        >>> G.identification_analysis(exposure="X", outcome="Y", verbose=False)
        >>> G.identification(print="assumptions", parameter="ACE")
        """
        if not self.__identification__:
            self.identification_analysis(verbose=False)

        identification = kws.get("identification", {})
        identification["content"] = print
        identification["parameter"] = parameter

        self.print('identification', identification=identification)
        return None

    @property
    def identification_dict(self):
        """
        Mapping of identification results produced by the last analysis.

        Returns
        -------
        dict
            Identification summary as generated by the internal identification
            object.

        Examples
        --------
        >>> G = DAG(graph="X -> Y")
        >>> G.identification_analysis(exposure="X", outcome="Y", verbose=False)
        >>> isinstance(G.identification_dict, dict)
        True
        """
        if not self.__identification__:
            self.identification_analysis()
        res = self.__identification__.identification
        return res

    def print(self,
              what = 'graph',
              identification = dict(
                  content='default',
                  style='text',
                  strategy = 'all',
                  parameter = 'ACE',
                  omit_DAG=True,
                  print_assumptions=None,
                  print_assumptions_verbose=None
              )
              ):
        """
        Display graph or identification information using configured options.

        Parameters
        ----------
        what : {'graph', 'DAG', 'dag', 'identification'}, optional
            Content selector. Case-insensitive variants for graph display are
            accepted. Defaults to ``'graph'``.
        identification : dict, optional
            Print configuration dict forwarded to the internal identification
            object. Missing keys fall back to global defaults obtained from
            ``get_options()``.

        Returns
        -------
        None

        Examples
        --------
        >>> G = DAG(graph="X -> Y")
        >>> G.print(what="graph")
        >>> G.identification_analysis(exposure="X", outcome="Y", verbose=False)
        >>> G.print(what="identification", identification={"content": "strategy"})
        """
        if what in ['graph', 'DAG', 'dag']:
            print(self)
        if what=='identification':
            ops = identification.copy()
            # defaults
            pars = ["print_assumptions", "print_assumptions_verbose"]
            for par in pars:
                if ops.get(par, None) is None:
                    ops[par] = get_options()[par]

            if not self.__identification__:
                self.identification_analysis()
            self.__identification__.print(**identification)
            self.__identification__.__assumptions_print__(category='identification', **ops)
        return None
        
    # dagitty (R dependencies)
    def paths(self, exposure=None, outcome=None, adj_set=None, directed=False):
        """
        Enumerate paths between exposure and outcome, optionally conditioning on a set.

        Parameters
        ----------
        exposure : str or list[str] or None, optional
            Exposure node(s). Defaults to the DAG's exposure role when omitted.
        outcome : str or list[str] or None, optional
            Outcome node(s). Defaults to the DAG's outcome role when omitted.
        adj_set : Sequence[str] or None, optional
            Conditioning set supplied to ``dagitty.paths``. ``None`` is passed
            through to indicate no adjustment.
        directed : bool, optional
            When ``True``, restrict to directed paths from exposure to outcome.
            Defaults to ``False``.

        Returns
        -------
        dict[str, dict[str, Any]]
            Mapping from path strings to dictionaries with keys ``'open'`` and
            ``'adj_set'`` indicating path status and conditioning set.

        Examples
        --------
        >>> G = DAG(graph="X -> Z -> Y")
        >>> G.paths(exposure="X", outcome="Y", directed=True)
        {'X -> Z -> Y': {'open': True, 'adj_set': None}}
        """
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
        """
        Extract mediator nodes lying on directed paths from exposure to outcome.

        Parameters
        ----------
        as_string : bool, optional
            When ``True``, return a formatted string representation of mediator
            sets. Defaults to ``False`` to return a list of lists.

        Returns
        -------
        list[list[str]] or str
            Mediator nodes grouped by directed path when ``as_string`` is
            ``False``; otherwise a string representation of the same structure.

        Examples
        --------
        >>> G = DAG(graph="X -> M -> Y")
        >>> G.mediators()
        [['M']]
        >>> G.mediators(as_string=True)
        '[[M]]'
        """
        paths = self.paths(directed=True)
        paths = [p.split('->') for p in paths]
        exposure = self.exposure
        outcome = self.outcome
        res = []
        for path in paths:
            res += [[var.strip() for var in path if var.strip() not in  exposure + outcome]]
        res = [l for l in res if len(l)>0]
        
        if as_string:
            res = f"[{', '.join([f"[{', '.join(l) }]" for l in res])}]"
        return res
        
    # dagitty (R dependencies)
    def equivalence_class(self):
        """
        Construct the partially directed equivalence class implied by the DAG.

        Returns
        -------
        DAG
            A new `DAG` instance representing the Markov equivalence class,
            where edges are undirected unless compelled by v-structures.

        Notes
        -----
        The equivalence class replaces directional edges with undirected edges
        except in v-structures (triples ``X -> Z <- Y`` where ``X`` and ``Y``
        are not adjacent).

        Examples
        --------
        >>> G = DAG(graph="X -> Z -> Y")
        >>> eq = G.equivalence_class()
        >>> eq
        Graph:

        Z -- X
        Z -- Y
        Observed: Z, Y, X
        >>> eq.undirected
        [{'X', 'Z'}, {'Z', 'Y'}]
        """
        eq = dagitty.equivalenceClass(self.__dagitty__)
        dag, _ = self.__dagitty2inputs__(eq)
        res = self.__rebuild_graph__(dag)
        return res

    # dagitty (R dependencies)
    def equivalent_dags(self):
        """
        Generate all DAGs that are Markov equivalent to the current graph.

        Returns
        -------
        list[DAG]
            Collection of `DAG` instances, each representing a distinct DAG in
            the equivalence class.

        Examples
        --------
        >>> G = DAG(graph="X -> Z -> Y")
        >>> dags = G.equivalent_dags()
        >>> len(dags)
        3
        """
        eqs = dagitty.equivalentDAGs(self.__dagitty__)
        res = []
        for eq in eqs:
            dag, _ = self.__dagitty2inputs__(eq)
            res += [self.__rebuild_graph__(dag)]
        return res

    def observationally_equivalent(self, G):
        """
        Test whether two DAGs are observationally equivalent.


        Parameters
        ----------
        G : DAG
            Graph to compare with the current instance.

        Returns
        -------
        bool
            ``True`` if both graphs encode the same observational constraints,
            i.e., they belong to the same Markov equivalence class; ``False``
            otherwise.

        Details
        -------

        The method checks if two DAGs are observationally equivalent by comparing their Markov equivalent classes.
        The method considers only the DAG structure, that is, CBN or SCM when no functional
        form for the latter is selected. Observational equivalence is related to Markov equivalence.

        Two DAGs are Markov equivalent iff

        A. They have the same skeleton (same set of adjacencies, i.e., same undirected edges)  

        B. They have the same set of v-structures (triples \( X \rightarrow Z \leftarrow Y \) where X and Y are not adjacent).

        An equivalence class of a DAG is a graph that replaces directional edges with undirected edges except
        in v-structures. Therefore, all Markov equivalent DAGs will have the same equivalence class.

        For CBN:

        - Two CBNs are observationally equivalent iff they are Markov equivalent.

        For SCM:

        Without functional form assumptions, for observational equivalence:

        - Necessary condition: both SCMs have the same set of conditional independencies.

        - Sufficient condition: both SCMs are in the same Markov equivalence class (Pearl, 2009).

        - Basically, two SCMs are observationally equivalent iff their causal graphs belong to the same Markov
        equivalence class --- i.e., they share the same skeleton and v-structures.

        With functional form assumptions:

        - Once you impose functional form restrictions on SCMs, such as linearity, Gaussian disturbance, or
        additive error, observational equivalence can be strictly finer. That is, Markov equivalence is not a sufficient condition.

        Example:

        a. Linear Gaussian SEMs assumption:
        - All DAGs in the same equivalence class remain indistinguishable.
        Markov equivalence = observational equivalence. Reason: any covariance matrix that
        one DAG can generate can also be generated by another DAG in its equivalence class, via suitable parameter choice.

        b. Linear non-Gaussian models (LiNGAM):
        - Orientations become testable because independent non-Gaussian noise
        'pins down' which variable must be the parent, breaking Markov equivalence.
        Example: \( X \rightarrow Y \) and \( X \leftarrow Y \): In the Gaussian case: indistinguishable.
        In non-Gaussian: identifiable.

        c. Additive Noise Models (ANMs):
        - If the true relation is \( Y = f(X) + e \) with independent noise \( e \),
        then typically the 'wrong' orientation \( X = g(Y) + e' \) cannot hold with
        independent noise. So direction becomes identifiable.

        In summary, generally, SCMs (no distributional restrictions) imply that Markov equivalence
        does imply observational equivalence. But once you impose restrictions (linear, Gaussian,
        additive, etc.), observational equivalence can be strictly finer. That is, if one assumes
        functional forms or noise properties, one may be able to distinguish DAGs inside a Markov
        equivalence class. Some Markov-equivalent DAGs become distinguishable. Then, the test of
        equivalence depends on the functional form assumption adopted, so it is case-by-case.

        Examples
        --------
        >>> G1 = DAG(graph="X -> Y")
        >>> G2 = DAG(graph="X <- Y")
        >>> G1.observationally_equivalent(G2)
        True

        References
        ----------
        Pearl, J. (2009). *Causality: Models, Reasoning and Inference*.
        Cambridge University Press.
        """
        # check if same equivalence class
        G1_eq = self.equivalence_class()
        G2_eq = G.equivalence_class()
        diff = G1_eq.edge_differences(G2_eq)
        obs_eq = True
        for g, edges in diff.items():
            obs_eq &= all([len(e)==0 for e in edges.values()])
        return obs_eq 

    def assumptions(self, category=None, verbose=False):
        """
        Retrieve identification assumptions grouped by category.

        Parameters
        ----------
        category : str or None, optional
            Filter assumptions to a specific category (e.g., ``'identification'``).
            When ``None`` (default), all available categories are returned.
        verbose : bool, optional
            If ``True``, include additional descriptive information when supported
            by the underlying identification object. Defaults to ``False``.

        Returns
        -------
        dict or tidypolars4sci.DataFrame
            Structure containing the requested assumptions, as provided by the
            identification backend.

        Examples
        --------
        >>> G = DAG(graph="X -> Y")
        >>> G.identification_analysis(exposure="X", outcome="Y", verbose=False)
        >>> G.assumptions(category="identification")
        """
        if not self.__identification__:
            self.identification_analysis()
        return self.__identification__.assumptions(category=category, verbose=verbose)
    # -------------------------------------------------

    # plots -------------------------------------------
    def plot(self,
             # nodes
             graph_style = None,
             nodes_label=None,
             nodes_position=None,
             estimates=None,
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
             edge_label_color_background='white',
             edge_label_color_border='white',
             edge_label_size=None,
             edge_label_color=None,
             edge_label_alpha=None,
             edge_label_rotate=None,
             edge_label_position=None,
             edge_label_sig_level=0.05,
             edge_label_pvalue=None,
             edge_label_font_family = None,
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
             show_plot=None,
             *args,
             **kws
             ):
        """
        Render the DAG using matplotlib with extensive styling controls.

        Parameters
        ----------
        graph_style : {'default', 'rectangle', 'pearl'} or None, optional
            Predefined style bundle for nodes and edges. When ``None``, falls
            back to the global plotting option.
        nodes_label : dict[str, str] or None, optional
            Mapping from node names to display labels.
        nodes_position : dict[str, tuple[float, float]] or None, optional
            Coordinates to override automatic layout positions.
        estimates : estimate or None, optional
            Output of ``causalinf.scm.estimate`` used to annotate edges with
            estimates and p-values.
        node_subset : dict[str, list[str]] or None, optional
            Restrict plotting to specific node groups (e.g., observed,
            latent). Defaults to all nodes.
        node_shape, node_size, node_color, node_border_color, node_border_style, node_border_width : dict or scalar, optional
            Visual attributes applied per node group; scalars are broadcast.
        node_latent_show : bool, optional
            If ``False``, omit latent nodes while preserving their effects via
            arcs. Defaults to ``True``.
        show_labels : bool, optional
            Display node labels when ``True`` (default).
        use_labels : bool, optional
            When ``True`` (default), prefer custom labels over node names.
        node_label_box : bool, optional
            Draw a bounding box around node labels in rectangle mode.
        node_label_fontsize, node_label_fontweight : dict or scalar, optional
            Font styling overrides for node labels.
        node_label_adj_x, node_label_adj_y : dict or float, optional
            Horizontal and vertical label offsets.
        node_label_box_style : str, optional
            Matplotlib box style applied when ``node_label_box`` is ``True``.
        node_label_box_margin : float, optional
            Padding for label boxes.
        edge_subset : dict[str, list] or None, optional
            Limit plotting to selected edges by type.
        edge_color, edge_style, edge_arc, edge_linewidth, edge_head_size, edge_head_style : dict or scalar, optional
            Edge styling parameters by edge type.
        edge_margin_tail, edge_margin_head : dict or float, optional
            Arrowhead offsets for edges.
        edge_label : dict or None, optional
            Explicit edge labels overriding stored defaults.
        edge_label_color_background, edge_label_color_border : str, optional
            Background and border colors for edge labels.
        edge_label_size, edge_label_color, edge_label_alpha, edge_label_rotate, edge_label_position : dict or scalar, optional
            Label appearance controls.
        edge_label_sig_level : float, optional
            Significance level used when estimates include confidence bounds.
        edge_label_pvalue : dict or None, optional
            P-value annotations keyed by edge.
        edge_label_font_family : str or None, optional
            Font family for edge labels.
        legend_show : bool, optional
            Display the legend when ``True`` (default).
        legend_title : str, optional
            Legend title. Defaults to ``'Nodes'``.
        legend_title_align : {'left', 'center', 'right'}, optional
            Horizontal alignment for the legend title.
        legend_title_weight : str, optional
            Font weight for the legend title.
        legend_title_size : int, optional
            Legend title font size.
        legend_omit_cases : list[str], optional
            Node role labels to omit from the legend.
        legend_keys : dict or None, optional
            Custom legend entries keyed by role.
        legend_loc : str, optional
            Legend placement for ``matplotlib.axes.Axes.legend``.
        legend_fontsize : int, optional
            Legend text size.
        legend_frame : bool, optional
            Draw a frame around the legend when ``True``.
        legend_kws : dict, optional
            Additional keyword arguments forwarded to ``legend``.
        title : str or None, optional
            Plot title.
        title_loc : {'left', 'center', 'right'}, optional
            Title alignment. Defaults to ``'left'``.
        title_kws : dict, optional
            Additional title styling options.
        figsize : Sequence[float], optional
            Width and height (in inches) for the created figure. Defaults to
            ``[6, 4]``.
        usetex : bool, optional
            Enable LaTeX rendering for text. Defaults to ``True``.
        ax : matplotlib.axes.Axes or None, optional
            Existing axis to draw on. A new figure and axis are created when
            ``None``.
        show_plot : bool or None, optional
            Override global option controlling whether ``plt.show()`` is called.
        *args :
            Additional positional arguments forwarded to the internal plotting
            helpers.
        **kws :
            Extra keyword arguments forwarded to the internal plotting helpers.

        Returns
        -------
        matplotlib.axes.Axes
            plot object and axis on which the graph is drawn.

        Examples
        --------
        >>> G = DAG(graph="X -> Y")
        >>> plt, ax = G.plot(figsize=(4, 3), show_plot=False)
        True
        """
        assert estimates is None or isinstance(estimates, estimate), (
            "'estimates' must be either None or an object of causalinf.scm.estimate ")

        default_usetex = plt.rcParams["text.usetex"] 
        plt.rcParams["text.usetex"] = usetex
        plt.rcParams['text.latex.preamble'] = r'\usepackage{amsmath, amssymb, siunitx, bm}'
        show_plot = show_plot if not None else get_options('show_plot')

        # collect arguments
        pars = dict(locals())      # {'node_position':..., 'arg2':..., 'args':(...), 'kws':{...}}
        args = pars.pop('args') # extra positional
        kws  = pars.pop('kws')  # extra keyword

        # use estimates as labels
        if estimates is not None:
            edge_label, edge_label_pvalue = self.__plot_collect_labels_estimate__(estimates)

        # figure 
        # ------
        G_draw = self.__plot_create_nx__()
        if ax is None:
            fig, ax = plt.subplots(figsize=figsize, tight_layout=True)
        plt.sca(ax)

        # styles
        # ------
        graph_style = graph_style or get_options('graph_style')
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
                    show_edge = self.edge_exist(e, edge_subset.get(edge_type, []))

                if u in nodes and v in nodes and show_edge:
                    # edge
                    nx.draw_networkx_edges(
                        G_draw,
                        nodes_position,
                        edgelist            = [(u, v)],
                        style               = style,
                        edge_color          = color,
                        connectionstyle     = f"arc3,rad={arc}",
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
                        connectionstyle = f"arc3,rad={arc}",
                        edge_labels     = {(u, v): label},
                        bbox=dict(facecolor=edge_label_color_background, edgecolor=edge_label_color_border),
                        # 
                        alpha      = self.__plot_edge_label_feature__('alpha', edge, edge_label_alpha, None, edge_label_sig_level,
                                                                      edge_label_pvalue=edge_label_pvalue),
                        font_size  = self.__plot_edge_label_feature__('size' , edge, edge_label_size, 15),
                        font_color = self.__plot_edge_label_feature__('color', edge, edge_label_color, label=label),
                        rotate     = self.__plot_edge_label_feature__('rotate', edge, edge_label_rotate, default=rotate),
                        label_pos  = self.__plot_edge_label_feature__('position', edge, edge_label_position, .5),
                        font_family=edge_label_font_family,
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
        if show_plot:
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
        """
        Plot individual paths between exposure and outcome nodes.

        Parameters
        ----------
        exposure : str or list[str] or None, optional
            Exposure node(s) to anchor the paths. Defaults to the DAG exposure
            role when omitted.
        outcome : str or list[str] or None, optional
            Outcome node(s) serving as path targets. Defaults to the DAG outcome
            role when omitted.
        adj_set : str or Sequence[str] or None, optional
            Adjustment set used to assess path openness. Strings are promoted to
            single-element lists.
        directed : bool, optional
            If ``True``, restrict to directed paths from exposure to outcome.
            Defaults to ``False``.
        show_full_dag : bool, optional
            Draw the entire DAG in the background with muted styling before
            highlighting each path. Defaults to ``True``.
        use_labels : bool, optional
            When ``True`` (default), prefer custom node labels over names.
        title_fontsize : int, optional
            Font size for subplot titles. Defaults to ``10``.
        figsize : tuple[float, float], optional
            Size of the grid of path plots in inches. Defaults to ``(16, 9)``.
        path_color : str, optional
            Color applied to highlighted path edges. Defaults to ``'black'``.
        **plot_kws :
            Additional keyword arguments forwarded to ``DAG.plot`` for both the
            background DAG (when ``show_full_dag`` is ``True``) and each path.

        Returns
        -------
        list[matplotlib.axes.Axes]
            Axes objects for the generated subplots. The list is flattened even
            when the grid contains a single axis.

        Examples
        --------
        >>> G = DAG(graph="X -> Z -> Y")
        >>> axes = G.plot_paths(exposure="X", outcome="Y", directed=True, show_full_dag=False)
        >>> len(axes)
        1
        """
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
        """
        Visualize multiple DAGs in the Markov equivalence class.

        Parameters
        ----------
        use_labels : bool, optional
            Prefer custom node labels when ``True`` (default).
        show_labels : bool, optional
            Display node labels on the plots. Defaults to ``True``.
        edge_difference_color : str, optional
            Color used to highlight edges that differ from the original graph
            in each equivalent DAG. Defaults to ``'red'``.
        title_fontsize : int, optional
            Font size for subplot titles. Defaults to ``10``.
        title_original_graph : str, optional
            Title assigned to the baseline plot of the original DAG.
        title_equivalent_graph : str, optional
            Title applied to each equivalent DAG subplot.
        show_footnote : bool, optional
            Display a numbered footnote beneath each subplot when ``True``.
        figsize : tuple[float, float], optional
            Figure size in inches for each panel grid. Defaults to ``(16, 9)``.
        max_per_figure : int, optional
            Maximum number of panels per figure. Defaults to ``9``.
        max_eq_dags : int, optional
            Cap on the number of equivalent DAGs to display. Defaults to ``27``.
        **plot_kws :
            Additional keyword arguments forwarded to ``DAG.plot``.

        Returns
        -------
        dict[int, list]
            Mapping from figure index to ``[figure, axes_list]`` pairs. Returns
            ``None`` when no equivalent DAGs exist.

        Examples
        --------
        >>> G = DAG(graph="X -> Z <- Y")
        >>> figs = G.plot_equivalent_dags(show_footnote=False, max_eq_dags=4)
        >>> isinstance(figs, dict)
        True
        """
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

    def plot_equivalence_class(self, *args, **kws):
        """
        Plot the partially directed Markov equivalence class of the DAG.

        Parameters
        ----------
        *args :
            Positional arguments forwarded to ``DAG.plot``.
        **kws :
            Keyword arguments forwarded to ``DAG.plot``.

        Returns
        -------
        matplotlib.axes.Axes
            Axis containing the rendered equivalence class.

        Examples
        --------
        >>> G = DAG(graph="X -> Z <- Y")
        >>> ax = G.plot_equivalence_class(show_plot=False)
        >>> ax is not None
        True
        """
        self.equivalence_class().plot(*args, **kws)

    def plot_identification(self,
                            content='default', # detailed, default
                            effect='total', #total, direct, or do, only if if_info=full
                            show_np = True,
                            show_linear = True,
                            show_do = True,
                            kws_graph={},
                            kws_identification={},
                            kws_detailed = None,
                            figsize = None,
                            ratio   = None,
                            ncols   = None,
                            nrows   = None,
                            title_dag = None,
                            title_info = None,
                            txt_line_height=.55,
                            *args,
                            **kws
                            ):
        """
        Plot identification information alongside the DAG.

        Parameters
        ----------
        content : {'default', 'detailed'}, optional
            Level of detail displayed in the identification summary. Defaults to
            ``'default'``.
        effect : {'total', 'direct', 'do'}, optional
            Effect type to highlight when ``content`` requires it. Defaults to
            ``'total'``.
        show_np, show_linear, show_do : bool, optional
            Toggle inclusion of non-parametric, linear, and do-calculus
            strategies in the summary. All default to ``True``.
        kws_graph : dict, optional
            Keyword arguments forwarded to ``DAG.plot`` for the DAG panel.
        kws_identification : dict, optional
            Arguments passed to ``identification_analysis`` before plotting.
        kws_detailed : dict or None, optional
            Overrides for detailed identification output (e.g.,
            ``{'strategy': 'SoO', 'parameter': 'ACE'}``). Defaults to selecting
            the first available parameter.
        figsize : tuple[float, float] or None, optional
            Figure size in inches. When ``None``, the identification plotting
            routine chooses a default.
        ratio : float or None, optional
            Aspect ratio override for the combined plot.
        ncols, nrows : int or None, optional
            Layout configuration for identification panels.
        title_dag : str or None, optional
            Title displayed above the DAG subplot.
        title_info : str or None, optional
            Title for the identification summary panel.
        txt_line_height : float, optional
            Text line height used when ``figsize`` is not provided. Defaults to
            ``0.55``.
        *args :
            Additional positional arguments forwarded to the underlying plotting
            routine.
        **kws :
            Extra keyword arguments forwarded to the underlying plotting routine.

        Returns
        -------
        tuple
            Result of ``self.__identification__.plot`` which includes figure and
            axes handles.

        Examples
        --------
        >>> G = DAG(graph="X -> Y")
        >>> G.identification_analysis(exposure="X", outcome="Y", verbose=False)
        >>> result = G.plot_identification(show_plot=False)
        """
        roles = ['Exposure', 'Outcome', 'Latent', 'Observed',
                 'exposure', 'outcome', 'latent', 'observed']
        for role in roles:
            assert not kws_graph.get(role, None) and not kws_identification.get(role, None), (
                f"Setting node role ({role}) not allowed in the plot kws. "+
                f"To set the node role, create a new DAG or use set_node_role before plotting.")

        if not self.__identification__ or kws_identification:
            self.identification_analysis(**kws_identification, verbose=False)
        
        # defaults for kws_detailed
        kws_detailed = kws_detailed or {}
        strategy = kws_detailed.get('strategy', 'SoO')
        parameter = kws_detailed.get('parameter', None)
        if not parameter:
            parameter = next(iter(self.__identification__.identification[strategy]))
        kws_detailed['strategy'] = strategy
        kws_detailed['parameter'] = parameter

        return self.__identification__.plot(G=self,
                                            info=content,
                                            effect=effect,
                                            show_np = show_np,
                                            show_linear = show_linear,
                                            show_do = show_do,
                                            figsize=figsize,
                                            ratio=ratio,
                                            ncols=ncols,
                                            nrows=nrows,
                                            kws_graph=kws_graph,
                                            kws_detailed = kws_detailed,
                                            txt_line_height=txt_line_height,
                                            title_dag = title_dag,
                                            title_info = title_info,
                                            *args,
                                            **kws
                                            )
    
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

        # remove comments
        graph = "\n".join(line for line in re.sub(r"#.*", "", graph).splitlines() if line.strip())

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
        # Parse DAG string to properties of the graph: nodes, directed, 
        # bidirected, and undirected edges. 
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
        dag_df = convert().rtibble2tp(dagitty.edges(dag_dagitty))
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
        # Split [0..limit] into chunks.
        # Each chunk has n elements, except:
        #   - the last one may have fewer if not divisible, OR
        #   - the last one may be larger if needed to include 'limit'.
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

    def __edge_frozen_format__(self, edge):
        # Convert an edge into a canonical, hashable form.
        # - directed: ('A','B')
        # - undirected: frozenset({'A','B'})
        # - bidirected: frozenset({('A','B'),('B','A')})
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
        # """
        # Classify an edge as 'directed', 'bidirected', or 'undirected'.
        # """
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
        """
        Compare edge sets between two DAGs by edge type.

        Parameters
        ----------
        G2 : DAG
            Graph to compare with the current instance.

        Returns
        -------
        dict[str, dict[str, list]]
            Dictionary with keys ``'G1'`` and ``'G2'``, each mapping to a
            dictionary keyed by edge type (``'directed'``, ``'undirected'``,
            ``'bidirected'``) listing edges present in one graph but absent in
            the other.

        Examples
        --------
        >>> G1 = DAG(graph="X -> Y")
        >>> G2 = DAG(graph="X <- Y")
        >>> diff = G1.edge_differences(G2)
        >>> diff["G1"]["directed"]
        [('X', 'Y')]
        """
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
            adj = {node:node_label_adj.get(node, 0)
                   for node in self.get_nodes(exclude_latent=False)}
        elif isinstance(node_label_adj, (float, int)):
            adj = {node:node_label_adj
                   for node in self.get_nodes(exclude_latent=False)}
        # same for if labels are used
        for node, label in nodes_label.items():
            adj[label] = adj[node]
        return adj

    def __plot_collect_labels_estimate__(self, estimates, show_sig=True, show_se=False, show_ci=False):
        tab = (estimates.est.parameters
               .separate('term',  ['_to', '_from'], '~', remove=False)
               .mutate(_to = tp.str_trim('_to'),
                       _from = tp.str_trim('_from')
                       )
               .filter(tp.col("_from")!='')
               .filter(tp.col("_to")!='')
               .drop_null('_from', '_to')
               )
        digits = 4
        ests = {}
        pvalues = {}
        for row in tab.iterrows():
            est = round(row['estimate'], digits)
            ests |= {(row['_from'], row['_to']): est}

            pvalue = row['pvalue']
            pvalues |= {(row['_from'], row['_to']): pvalue}

        return ests, pvalues

    # styles
    def __plot_get_style__(self, graph_style):
        if graph_style=='default':
            aes = self.__plot_get_style_default__()
        
        elif graph_style=='rectangle':
            aes = self.__plot_get_style_rectangle__()

        elif graph_style=='pearl':
            aes = self.__plot_get_style_pearl__()

        else:
            aes = self.__plot_get_style_default__()

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
                         "bidirected": -.33,
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
                         "bidirected": -.33,
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
                         "bidirected": -.33,
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

class identification:

    def __init__(self, *args, **kws):
        self.identification = None
        self.__assumptions_list__()
        self.identification_analysis(self, *args, **kws)

    def assumptions(self, category=None, verbose=False):
        # """
        # Return a list of assumption entries (with keys) that include the given usage category.

        # Parameters
        # ----------
        # category : str
        #     An assumption category such as 'identification', 'discovery', 'estimation', 'inference'.

        # Returns
        # -------
        # Print assumptions
        # If no matches are found, returns list of categories
        # """
        category = (category or "").strip().lower()

        # collect categories
        categories = []
        for assumption, details in self.__assumptions__.items():
            categories += details['usage']
        categories = set(categories)
                
        # collect
        res = None
        if category in categories:
            result = []
            for key, entry in self.__assumptions__.items():
                if category in [u.lower() for u in entry.get("usage", [])]:
                    result.append(entry)

            if verbose:
                res = self.__assumptions_collect_verbose__(result)
            else:
                res = self.__assumptions_collect__(result)
        else:
            print('Categories available:')
            [print(f"- {c}") for c in categories]

        return res

    def __assumptions_list__(self):
        self.__assumptions__ = {
            # identification
                "correct_dag": {
                    "name"       : "Correct DAG",
                    "usage"      : ["identification"],
                    "definition" : ("DAG structure matches the true causal relations: " +
                                    "(a) A directed arrow from a variable A to a variable B means that there is a causal " +
                                    "effect of A on B, which may or may not be zero; (b) Absence of an arrow from a variable C " +
                                    "to a variable D implies certainty that C does not cause D; (c) A bidirected arrow between " +
                                    "a variable E and a variable F means that they share a common unobserved or latent cause." 
                                    ),
                    "scope"      : "Connection between reality and the DAG model",
                    "role"       : "Ensures adjustment sets and do-calculus yield the correct identifiable causal effect.",
                    "violation"  : "Biased or invalid causal effect estimates and incorrect adjustment sets.",
                    "notes"      : "A prerequisite for identifiability claims conditional on a DAG.",
                    'required'   : 'yes',
                    'testable'   : 'no',
                },
                # "no_unmodeled_causes": {
                #     "name"       : "No unmodeled causes (causal sufficiency)",
                #     "usage"      : ["identification"],
                #     "definition" : ("All direct and indirect common causes of variables in the DAG are included in the DAG"+
                #                     " either as observed or latent nodes (no unmodeled causes)."),
                #     "scope"      : "Connects reality and the DAG model",
                #     "role"       : "Enables back-door/front-door adjustment or perform do-calculus on observables.",
                #     "violation"  : "Confounding bias; causal effects not identifiable.",
                #     "aliases"    : ["Causal Sufficiency"],
                #     'required'   : 'yes',
                #     'testable'   : 'no',
                # },
                # identification and discovery
                "causal_markov_condition": {
                    "name"       : "Causal Markov Condition (CMC)",
                    "usage"      : ['identification', 'discovery'],
                    "definition" : "Each variable is independent of its non-descendants given its parents",
                    "scope"      : "Connects the DAG and the conditional distribution of each variable",
                    "role"       : "Links d-separation to conditional independencies, grounding do-calculus.",
                    "violation"  : "Graph–distribution link breaks and identification results may be incorrect.",
                    'required'   : 'yes',
                    'testable'   : 'no',
                },
                # identification and estimation
                "positivity": {
                    "name"       : "Positivity (Overlap)",
                    "usage"      : ['identification', "estimation", 'inference'],
                    "definition": ("Each treatment level has a positive probability of occurring, including at all relevant levels" +
                                   " of the adjustment variables if they are used for identification."),
                    "scope"      : "Variables' distributions",
                    "role"       : "Required for the g-formula, IPW, and many identification and estimation strategies.",
                    "violation"  : "Effects are undefined or non-estimable in certain regions of the covariate space.",
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
        }

    def __assumptions_print__(self, print_assumptions=True, category=None, *args, **kws):
        if print_assumptions:
            print(dedent("""
            Assumptions for identification:
            ------------------------------"""))
            assumptions = self.assumptions(category=category, verbose=kws.get("print_assumptions_verbose", False))
            for i, a in enumerate(assumptions):
                print(f"{i+1}. {a}")
            print('\n')
        return None

    def __assumptions_collect__(self, assumptions):
        txt = []
        for i, assump in enumerate(assumptions):
            txt += [assump['definition']]
        return txt

    def __assumptions_collect_verbose__(self, assumptions):
        txt = []
        for i, assump in enumerate(assumptions):
            txt += [dedent(f"""\
            {assump['name']}
               - Definition: {assump.get('definition', '')}
               - Scope: {assump.get('scope', '')}
               - Role: {assump.get('role', '')}
               - Usage: {', '.join(assump.get('usage', ''))}
               - Violation: {assump.get('violation', '')}\
            """)]
        return txt

    # dagitty (R dependencies)
    def identification_analysis(self, *args, **kws):
        # """
        # causal_probability: str
        #     If 'always', always compute it; if 'maybe', compute it
        #     only if there is not identification by adjustment for
        #     total_effect_adj_set effect
        # """
        G = kws.get("G", None)
        exposure = kws.get("exposure", None)
        outcome = kws.get("outcome", None)
        conditional = kws.get("conditional", None)
        c = '' if not conditional else 'c'
        causal_probability = kws.get("causal_probability", 'maybe')
        iv = kws.get("iv", 'maybe')
        verbose = kws.get("verbose", True)

        assert not outcome or isinstance(outcome, str), 'Outcome must be a string.'
        assert not exposure or (isinstance(exposure, str) or isinstance(exposure, list)), 'Exposure must be a string or list.'

        exposure = exposure or G.exposure
        outcome = outcome or G.outcome[0]

        assert exposure is not None, "Exposure must be provided."
        assert outcome is not None, "Outcome must be provided."

        # identification by adjustment 
        # ----------------------------
        effects = [f'{c}ACE', f'{c}ACDE']
        adj = {}
        for effect in effects:
            print(f"Searching for identification by adjustment variables for {effect}...", end='') if verbose else None
            adj[effect] = self.__identification_analysis_adj__(G, exposure, outcome, effect, conditional)
            print(f"done!") if verbose else None

        # instrumental variable (IV)
        # ---------------------
        IV = {}
        effect = f'{c}ACE' 
        total_identified = adj[effect]['identified']
        conduct = (not total_identified or iv=='always') and not conditional# conditional effect not available for IV
        print(f"Searching for identification by instrumental variables skipped.") if verbose and not conduct else None
        print(f"Searching for identification by instrumental variables...", end='') if verbose and conduct else None
        IV[effect] = self.__identification_analysis_iv__(G, exposure, outcome, conditional, conduct=conduct, conditional=conditional)
        print(f"done!") if verbose and conduct else None

        # causal probability  (condjuct only if not possible to use adjustment or if explicitly asked)
        # ------------------
        do = {}
        effect = f'{c}ACE'
        total_identified = adj[effect]['identified']
        iv_identified = IV[effect]['identified']
        conduct = (not total_identified and not iv_identified) or causal_probability=='always'
        print(f"Searching for identification by do-calculus skipped.") if verbose and not conduct else None
        print(f"Searching for identification by do-calculus...", end='') if verbose and conduct else None
        do[effect] = self.__identification_analysis_do__(G, exposure, outcome, conditional, conduct=conduct)
        print(f"done!") if verbose and conduct else None

        # collect results 
        # ---------------
        res = {'SoO':adj, 'do':do, "IV": IV}
        
        self.identification = res 

    def __identification_analysis_adj__(self, G, exposure, outcome, effect, conditional=None):
        if conditional:
            assert any([d not in conditional for d in exposure]), (
              "You cannot use exposure ({exposure}) as conditioning variable. Remove it from 'conditional'.")
            nodes_role = G.nodes_role | {"Adjusted": conditional}
            G = G.set_nodes_role(nodes_role)
        Ci = conditional
            
        # identification analysis
        effect_type = 'direct' if bool(re.search(pattern='.*ACDE', string=effect)) else 'total'
        adj_set = dagitty.adjustmentSets(G.__dagitty__,
                                         exposure = exposure,
                                         outcome = outcome,
                                         effect = effect_type,
                                         )
        # None: not identifiable; []: No adjustment needed; ['<var<'...]: adjustments
        adj_set_all = convert().rlist2list(adj_set)
        adj_set    = None if len(adj_set)==0 else list(adj_set.rx2['1'])
        adj_set    = [''] if adj_set==[] else adj_set
        identified = True if adj_set is not None else False
        
        # mediators (total effect should not adjust for mediators)
        has_mediators = len(G.mediators())>0 and effect=='ACDE'
        Mi = set(itertools.chain.from_iterable(G.mediators()))
        Mi = [m for m in Mi if m in (adj_set or [''])]

        # adjustments
        adj = [z for z in adj_set if z not in Mi] if Mi else adj_set
        adj = True if adj and adj != [''] else False
        Xi  = [x for x in adj_set or [''] if x not in Mi]

        # non-parametric and parametric formulas
        formulas = self.__identification_analysis_adj_formula__(identified, outcome, exposure, adj_set, conditional)
        f_par     = formulas['formula']
        f_np = formulas['formula np']
        f_par_print = formulas['print parametric']
        f_np_print = formulas['print non-parametric']
        f_par_latex = formulas['latex parametric']
        f_np_latex = formulas['latex non-parametric']
        beta_d_print = formulas['beta_d_print']
        beta_d_latex = formulas['beta_d_latex']

        # collect which variables used their code Mi, Zi, from tau.VARIABLES
        where = ''
        variables = None
        if identified:
            variables = {'Yi':outcome, 'Di':exposure}
            variables |= {'Mi':Mi} if has_mediators else {}
            variables |= {'Xi':Xi} if adj else {}
            variables |= {'Ci':Ci} if conditional else {}
            where += 'where'
            for var_code, vars in variables.items():
                vars = vars if isinstance(vars, list) else [vars]
                where += f"\n  {var_code}: {VARIABLES['variables'][var_code]} ({', '.join(vars)})"

        # use adjustements:
        adjusted = identified and adj

        # results
        result = adj_set
        result_str = ''
        if identified:
            adj_set_all = ' or '.join([f"{{{s}}}" for s in [', '.join(l) for l in adj_set_all]])
            result_str = f"Adjustments: {adj_set_all}"
            # result_str = f"Adjustments: {{{', '.join(result)}}}"
        else:
            result_str = "Not identifiable by adjustment."
            
        res = {
            # result
            'conducted'     : True,
            "identified"    : identified,
            'result'        : result,
            'result str'    : result_str.replace("{}", "None"),
            'adjusted'      : adjusted,
            # variables
            'outcome'       : outcome,
            'exposure'      : exposure,
            "conditional on": conditional,
            'variables'     : variables,
            'where'         : where,
            #
            'formulas': {
                'parametric'    : f_par,
                'non-parametric': f_np
            },
            'text': {
                "Non-parametric"       : f_np_print,
                "Parametric(*)"        : f_par_print + "\n(*) Under linearity and no interaction",
                'Parametric tau'       : ', '.join(beta_d_print),
            },
            'latex' : {
                "Non-parametric"       : f_np_latex,
                "Parametric(*)"        : f_par_latex + "\n(*) Under linearity and no interaction",
                'Parametric tau'       : ', '.join(beta_d_latex),
            }
        }
        return res

    def __identification_analysis_adj_formula__(self, identified, outcome, exposure, adj, conditional):

        if not identified:
            f = ""
            f_np = ''
            latex_parametric = ''
            latex_non_parametric = ''
            print_parametric = ''
            print_non_parametric = ''
            beta_d = ['']
            beta_d_latex = ['']
        else:
            adj = list(set(adj + conditional)) if conditional else adj
            d = ' + '.join([exposure] if isinstance(exposure, str) else exposure)
            X = ' + '.join(adj or [''])
            Xnp = ', '.join(adj or [''])
            y = outcome
            f    = f"{y} ~ {d} + {X}"
            f_np = f"{y} ~ f({d})" if not X else f"{y} ~ f({d}, {Xnp})"

            d = [exposure] if isinstance(exposure, str) else exposure
            beta_d = [f"b{i+1}" for i in range(len(d))]
            beta_Z = [f"b{i+1+len(d)}" for i in range(len(adj))] if adj!=[''] else ''
            beta_dTd = ' + '.join([f"{b} {D}" for b, D in zip(beta_d, d)])
            beta_xTX = ' + '.join([f"{b} {Z}" for b, Z in zip(beta_Z, adj)]) if adj!=[''] else ''

            beta_d_latex = [f"\\beta_{{{i+1}}}" for i in range(len(d))]
            beta_Z_latex = [f"\\beta_{{{i+1+len(d)}}}" for i in range(len(adj))] if adj!=[''] else ''
            beta_dTd_latex = ' + '.join([f"{b} {D}" for b, D in zip(beta_d_latex, d)])
            beta_xTX_latex = ' + '.join([f"{b} {Z}" for b, Z in zip(beta_Z_latex, adj)]) if adj!=[''] else ''

            print_parametric = f"E[Yi | ...] = b0 + {beta_dTd}" + (f" + {beta_xTX}" if adj!=[''] else '')
            latex_parametric = f"\\mathbb{{E}}[Y_i \mid \dots] = \\beta_0 + {beta_dTd_latex}"  + \
                (f" + {beta_xTX_latex}" if adj!=[''] else '')
            latex_parametric = f"${latex_parametric}$"

            vars = ', '.join([exposure] if isinstance(exposure, str) else exposure)
            vars = ', '.join(d) if not X else f"{', '.join(d)}, {Xnp}"
            print_non_parametric = f"E[Yi | ...] = f({vars})"
            latex_non_parametric = f"$\\mathbb{{E}}[Y_i \mid \dots] = f({vars})$"

        res = {
            'formula': f,
            'formula np': f_np,
            
            'print parametric' : print_parametric, 
            'print non-parametric' : print_non_parametric, 

            'latex parametric' : latex_parametric, 
            'latex non-parametric' : latex_non_parametric, 
           
            'beta_d_print' : beta_d,
            'beta_d_latex' : beta_d_latex,
        }
        return res
    
    def __identification_analysis_do__(self, G, exposure, outcome, conditional, conduct=False):
        if conduct:
            # identification
            X = ', '.join(G.get_nodes())
            Y = outcome
            D = ', '.join(exposure) if isinstance(exposure, list) else exposure
            Z = ', '.join(conditional) if isinstance(conditional, list) else conditional
            p = f"p({X})"
            q = f"p({Y} | do({D}))" if Z is None else f"p({Y} | do({D}), {Z})"
            causal_probability = dosearch.dosearch(p, q, G.__dagitty__)
            causal_probability = causal_probability.rx2['formula'][0] if bool(causal_probability.rx2['identifiable'][0]) else None
            identified = True if causal_probability is not None else False

            # formulas
            if identified:
                formula = causal_probability.replace('\\left(', ' ')\
                                            .replace('\\right)', '')\
                                            .replace('\\', '')
                p = formula
                formula = f"{q} = {formula}"
                formula_latex = f"${q} = {causal_probability}$"
                result = formula
                result_str = f"Causal probability: {formula}"
            else:
                formula = ''
                formula_latex = ''
                result = None
                result_str = "Not identifiable by do-calculus."

            # collect which variables used their code Mi, Zi, from tau.VARIABLES
            variables = None
            where = ''
            if identified:
                variables = {'Yi':outcome, 'Di':exposure}
                variables |= {'Ci':conditional} if conditional else {}
                where = 'where'
                for var_code, vars in variables.items():
                    vars = vars if isinstance(vars, list) else [vars]
                    where += f"\n  {var_code}: {VARIABLES['variables'][var_code]} ({', '.join(vars)})"

        else:
            identified = False
            result = None
            result_str = 'Not conducted. Identification by adjustment or instrumental variable available.'
            variables = None
            where = ""
            formula = ""
            formula_latex = ""

        res = {
            'conducted'      : conduct,
            "identified"     : identified,
            'result'         : result,
            'result str'     : result_str,
            'adjusted'      : False, # this does not matter for do-calculus
            # 
            'outcome'        : outcome,
            'exposure'       : exposure,
            "conditional on" : conditional,
            'variables'     : variables,
            'where'         : where,
            # 
            'formulas':{
                'parametric'    : formula,
                'non-parametric': formula,
            },
            'text':{
                "Non-parametric"       : formula,
                "Parametric(*)"        : formula,
                'Parametric tau'       : '',
            },
            'latex':{
                "Non-parametric"       : formula_latex,
                "Parametric(*)"        : formula_latex,
                'Parametric tau'       : '',
            }
        }
        return res

    def __identification_analysis_iv__(self, G, exposure, outcome, adj_set, conduct=False, conditional=None):
        if conduct and not conditional:
            assert len(exposure)==1, "IV method only works with a single exposure. Currently exposures: {exposure}"
            # identification
            result = dagitty.instrumentalVariables(G.__dagitty__, exposure=exposure, outcome=outcome)
            result = self.__identification_analysis_iv_parse__(result)
            identified = len(result.keys()) >  0
        else:
            identified = False
            result     = None

        # formulas
        formulas = self.__identification_analysis_iv_formula__(identified, outcome, exposure, result)
        f_par     = formulas['formula']
        f_np = formulas['formula np']
        f_par_print = formulas['print parametric']
        f_np_print = formulas['print non-parametric']
        f_par_latex = formulas['latex parametric']
        f_np_latex = formulas['latex non-parametric']
        beta_d_print = formulas['beta_d_print']
        beta_d_latex = formulas['beta_d_latex']
        
        # result_str
        # Note: results={'Z': {'adjustments': ['Z1']}, 'Z2': {'adjustments': []}, 'Z4': {'adjustments': ['Z1', 'Z3']}}
        if conditional:
            result_str = "Identification analysis for conditional average effects not available for IV."
        else:
            if conduct:
                if identified:
                    result_str = ''
                    txt = []
                    for iv, adj in result.items():
                        adjs = adj['adjustments']
                        Xs = f'(if adjusted by {', '.join(adjs)})' if len(adjs)>0 else ''
                        txt += [f"{iv} {Xs}"]
                    result_str = "Instrument: " + f' or \n'.join(txt)
                else:
                    result_str = 'No instrument available in the DAG.'
            else:
                result_str = 'Not conducted. Identification by adjustment available.'

            

        # collect which variables used their code Mi, Zi, from tau.VARIABLES
        where = ''
        variables = None
        if identified:
            Zmin = min(result, key=lambda k: len(result[k]['adjustments']))
            Xi = result[Zmin]['adjustments']
            variables = {'Yi':outcome, 'Di':exposure, 'Zi':Zmin}
            variables |= {'Xi':Xi} if len(Xi)>0 else {}
            # variables |= {'Ci':Ci} if conditional else {} # not available for IV
            where = 'where'
            for var_code, vars in variables.items():
                vars = vars if isinstance(vars, list) else [vars]
                where += f"\n  {var_code}: {VARIABLES['variables'][var_code]} ({', '.join(vars)})"

        # adjustements used?
        adjusted  = conduct and identified and len(Xi)>0

        res = {
            # result
            'conducted'     : conduct,
            "identified"    : identified,
            'result'        : result,
            'result str'    : result_str,
            'adjusted'      : adjusted,
            # variables
            'outcome'       : outcome,
            'exposure'      : exposure,
            "conditional on": None, # not availble for IV
            'variables'     : variables,
            'where'         : where,
            #
            'formulas': {
                'parametric'    : f_par,
                'non-parametric': f_np
            },
            'text': {
                "Non-parametric"       : f_np_print,
                "Parametric(*)"        : f_par_print + "\n(*) Under linearity and no interaction",
                'Parametric tau'       : beta_d_print,
            },
            'latex' : {
                "Non-parametric"       : f_np_latex,
                "Parametric(*)"        : f_par_latex + "\n(*) Under linearity and no interaction",
                'Parametric tau'       : beta_d_latex,
            }
        }
        return res
    
    def __identification_analysis_iv_parse__(self, ivs_obj):
        # """
        # Convert the output of dagitty::instrumentalVariables (via rpy2) to a Python dict:

        # Returns:
        #     {
        #         '<IV 1>': ['adjstments': [...]},
        #         '<IV 2>': ['adjstments': [...]},
        #         ...
        #     }
        # """
        def to_str_list(x):
            try:
                from rpy2.robjects.vectors import StrVector
                from rpy2.robjects import NULL
                if x is None or x is NULL:
                    return []
                if isinstance(x, StrVector):
                    return list(map(str, x))
            except Exception:
                pass
            if x is None:
                return []
            if isinstance(x, (list, tuple)):
                return list(map(str, x))
            try:
                return [str(x)]
            except Exception:
                return []

        result = {'by_instrument': {}}
        if ivs_obj is None:
            return result

        try:
            entries = list(ivs_obj)
        except Exception:
            return result

        for el in entries:
            try:
                names = getattr(el, "names", None)
                if names:
                    name_map = {str(n): i for i, n in enumerate(list(names))}
                    i_raw = el[name_map.get("I", 0)]
                    z_raw = el[name_map.get("Z", 1)] if "Z" in name_map else []
                else:
                    i_raw = el[0]
                    z_raw = el[1] if len(el) > 1 else []

                instrument_list = to_str_list(i_raw)
                if not instrument_list:
                    continue
                instrument = instrument_list[0]
                given = to_str_list(z_raw)

                entry = {
                    #     # "instrument": instrument,
                    #     # "given": given,
                    "adjustments": list(given),
                }
                # entry = list(given)
                result["by_instrument"].setdefault(instrument, []).append(entry)
            except Exception:
                continue

        result = result["by_instrument"]
        result = {iv:controls[0] for iv, controls in result.items()}
        return result

    def __identification_analysis_iv_formula__(self, identified, outcome, exposure, ivs):
        # IV works with a single exposure. 'assert' is in the main IV function
        exposure = exposure[0] if isinstance(exposure, list) else exposure

        if not identified or not ivs:
            f_iv = ""
            f_iv_np = ""
            latex_parametric = ""
            latex_non_parametric = ""
            print_parametric = ""
            print_non_parametric = ""
            beta = {'text':'', 'latex':''}
            formulas = {'text':"", 'latex':""}
        else:
            # get one of the (possible multiple) instruments, one with smallest number of adjustements
            Yi = outcome
            Di = exposure
            Zi = min(ivs, key=lambda k: len(ivs[k]['adjustments']))
            Xi = ivs[Zi]['adjustments']

            d = exposure
            X = ' + '.join(Xi or [''])
            Xnp = ', '.join(Xi or [''])
            y = outcome

            # formula (for estimation of linear models)
            f_dy = f"{y} ~ {d} + {X}"                     # structural form
            f_zd = f"{d} ~ {Zi} + {X}"                    # first stage
            f_zy = f"{y} ~ {Zi} + {X}"                    # reduced form
            f_iv = f"{y} ~ 1 + {X} + [{d} ~ {Zi} + {X}]"  # linearmodels module

            # non-parametric
            no_adj = not Xi or len(Xi)==0
            f_dy_np = f"E[{y} | ...] = f_1({d})"  if no_adj else f"E[{y} | ...] = f_1({d}, {', '.join(Xi)})"
            f_zd_np = f"E[{d} | ...] = f_2({Zi})" if no_adj else f"E[{d} | ...] = f_2({Zi}, {', '.join(Xi)})"
            f_zy_np = f"E[{y} | ...] = f_3({Zi})" if no_adj else f"E[{y} | ...] = f_3({Zi}, {', '.join(Xi)})"
            f_iv_np = {'Structural form:' :  f_dy_np,
                       'First stage:'     :  f_zd_np,
                       'Reduced form:'    :  f_zy_np}
            print_non_parametric = dedent(f"""
            Structural form: {f_dy_np}
            First stage:   : {f_zd_np}
            Reduced form:  : {f_zy_np}\
            """)
            latex_non_parametric = "\n"+ dedent(rf"""$\begin{{aligned}}
            \text{{Structural form}}&:  {_print2latex(f_dy_np).replace("$", '')}
            \text{{First stage}}    &:  {_print2latex(f_zd_np).replace("$", '')}
            \text{{Reduced form}}   &:  {_print2latex(f_zy_np).replace("$", '')}
            \end{{aligned}}$
            """.replace("\n", '\\\\'))

            # parametric
            equations_info = {
                'Structural form' : [[Yi, Di, Xi], {"text": [r'b{i}', 'nu' ],
                                                    'latex': [r'\beta_{{{i}}}', r'\nu'] }], # Y ~ D
                'First stage'     : [[Di, Zi, Xi], {"text": [r'a{i}', 'eta'],
                                                    'latex': [r'\alpha_{{{i}}}', r'\eta']}], # D ~ Z
                'Reduced form'    : [[Yi, Zi, Xi], {"text": [r'd{i}', 'e'  ],
                                                    'latex': [r'\delta_{{{i}}}', r'\epsilon']}]} # Y ~ Z
            formulas = {'text':[], 'latex':[]}
            for eq_type, eq_elements in equations_info.items():
                for (dep_var, ind_var, adj), parameters in [eq_elements]:
                    for print_type, parameter in parameters.items():
                        k = 1 + 1 + len(adj) # intercept + indvar + adjustments  
                        e = parameter[1]
                        p = parameter[0]
                        p = [f"{p.format(i=i)}" for i in range(k+1)]       # b0  +    b1     + b2, ..., b_{k-1}
                        covars = ' + '.join([rf"{p} {X}" for p, X in zip(p, [''] + [ind_var] + adj)])

                        space = np.max([len(s) for s in equations_info.keys()]) - len(eq_type)
                        eq_type = f"{eq_type+' '*space}:" if print_type=='text' else rf"\text{{{eq_type}}} &"

                        # f = f"{dep_var} = {covars} + {e}"
                        f = f"E[{dep_var} | ...] = {covars}"

                        formulas[print_type] += [f"{eq_type} {f}"]
            formulas['text'] = '\n' + '\n'.join(formulas['text'])
            formulas['latex'] = '\n' + rf"$\begin{{aligned}} { '\\\\ '.join(formulas['latex'])} \end{{aligned}}$" 


            # betas = tau
            beta = {}
            for pr in ['text', 'latex']:
                tau_zy = equations_info['Reduced form'][1][pr][0].format(i=1)
                tau_zd = equations_info['First stage'][1][pr][0].format(i=1)
                divided_by = "-"*np.max([len(tau_zd), len((tau_zy))])
                if pr=='latex':
                    beta[pr] = f"\\displaystyle \\frac{{{tau_zy}}}{{{tau_zd}}} = \\beta_1"
                    
                else:
                    beta[pr] = dedent(f"""\
                    {tau_zy}  = b1
                    {divided_by}
                    {tau_zd}\
                    """)

        res = {
            'formula': f_iv,
            'formula np': f_iv_np,
            
            'print parametric' : formulas['text'],
            'print non-parametric' : print_non_parametric, 

            'latex parametric' : formulas['latex'], 
            'latex non-parametric' : latex_non_parametric, 
           
            'beta_d_print' : beta['text'],
            'beta_d_latex' : beta['latex'],
        }
        return res
    
    def __identification_organize_by_causal_effect__(self):
        id = self.identification
        causal_effects = [list(causal_effect.keys()) for causal_effect in id.values()]
        causal_effects = set(itertools.chain.from_iterable(causal_effects))

        res = {causal_effect:{} for causal_effect in causal_effects}
        for strategy, causal_effects in id.items():
            for causal_effect, result in causal_effects.items():
                res[causal_effect][strategy] = result
        return res

    def get_identified(self, by='parameter', include_all=False):
        res = None
        if by == 'parameter':
            res = self.__identification_get_identified_parameter__(include_all=include_all)
        if by == 'strategy':
            res = self.__identification_get_identified_strategy__(include_all=include_all)
        return res

    def __identification_get_identified_parameter__(self, include_all=False):
        id = self.__identification_organize_by_causal_effect__()
        identified = {}
        for effect, strategies in id.items():
            strategy_identifies = []
            for strategy, result in strategies.items():
                if result['identified'] or include_all:
                    strategy_identifies += [strategy]
            if strategy_identifies:
                identified[effect] = strategy_identifies
        return identified
    
    def __identification_get_identified_strategy__(self, include_all=False):
        id = self.identification
        identified = {}
        for strategy, effects in id.items():
            effect_identified = []
            for effect, result in effects.items():
                if result['identified'] or include_all:
                    effect_identified += [effect]
            if effect_identified:
                identified[strategy] = effect_identified
        return identified

    def __repr__(self):
        print(self.print())
        return ""

    def print(self, content='default', style='text', strategy=None, parameter=None,
              omit_DAG=True, *args, **kws):
        parameter = parameter or list(self.identification['SoO'].keys())[0]
        conditional = list(self.identification['SoO'].values())[0]['conditional on']
        print(dedent(f"""
        Exposure: {', '.join(self.identification['SoO'][parameter]['exposure'])}
        Outcome: {self.identification['SoO'][parameter]['outcome']}\
        """))
        if conditional:
            print(f"Conditional on: {conditional}")

        if content=='detailed':
            txt = self.__print_detailed__(style=style, strategy=strategy, parameter=parameter, *args, **kws)
            print(txt)

        elif content=='concise': 
            txt = self.__print_concise__(omit_DAG)
            print(txt)

        elif content=='default': 
            txt = self.__print_default__(style=style, *args, **kws)
            print(txt)
            
        return None
    
    def __print_default__(self, *args, **kws):
        id = self.__identification_organize_by_causal_effect__()
        style = kws.get("style", 'text')
        txt = ''
        for causal_effect, strategies in id.items():
            tau_name = PARAMETER[causal_effect]['name']
            tau_abv  = causal_effect

            line = '-'*len(tau_name)

            txt += dedent(f"""\n
            {tau_name} ({tau_abv})
            {line}\
            """)
            for j, (strategy, result) in enumerate(strategies.items()):
                strategy_name = IDENTIFICATION[strategy]['name']
                conducted     = result['conducted']
                identified    = result['identified']
                do_latex      = strategy=='do' and style=='latex' and identified
                result        = "Causal probability: "+result[style]['Non-parametric'] if do_latex else result['result str']

                # identation/spaces
                result = result.replace('\n', '\n'+' '*28)
                skip_line = '\n' if j<len(strategies)-1 else ''

                txt += dedent(f"""
                Method: {strategy_name} ({strategy})
                Identified: {identified}
                {result}{skip_line}\
                """)
        return txt

    def __print_concise__(self, omit_DAG=True, table=False):
        conditional = list(self.identification['SoO'].values())[0]['conditional on']
        methods = self.identification.keys()
        res = {}
        for method in methods:
            res[method] = {}
            causal_effects = self.identification[method].keys()
            for causal_effect in causal_effects:
                available = self.identification[method].get(causal_effect, False)

                if available:
                    identified = self.identification[method][causal_effect]['identified']
                    conducted  = self.identification[method][causal_effect]['conducted']

                    if conducted and identified:
                        res[method][causal_effect] = 'Yes'
                    elif conducted and not identified:
                        res[method][causal_effect] = 'No'
                    elif not conducted:
                        res[method][causal_effect] = 'NA/NC**'
                else:
                    res[method][causal_effect] = 'NA/NC**'

        c = "c" if conditional else ""
        c_spelled = "Conditional " if conditional else ""
        space = " "*len(c_spelled)
        # 
        s1 = f"{res['SoO'][f'{c}ACE']:<4}"
        s2 = f"{res['SoO'][f'{c}ACDE']:<4}"
        s3 =  f"{res['IV'][f'{c}ACE']:<6}"
        s4 = "NA/NC**"                     # s4 =  f"{res['IV'][f'{c}ACDE']:<6}"
        s5 =  f"{res['do'][f'{c}ACE']}"
        s6 = "NA/NC**"                             # s6 =  f"{res['do'][f'{c}ACDE']}"
        footnote = """\
        Notes:
        *  For path effects (indirect effects), use SEM estimation
        ** NA/NC: Identification analysis not available or not conducted\
        """
        if not table:
            txt = dedent(f"""
            ==============================================================================
            {space}                                              Identified?
            {c_spelled}Causal Effects*                           SoO  IV   do-calculus 
            ==============================================================================
            {c_spelled}Averave Causal Effect ({c}ACE)              {s1}  {s3}    {s5}
            {c_spelled}Averave Controlled Direct Effect ({c}ACDE)  {s2}  {s4}    {s6}
            ==============================================================================
            Notes:
            *  For path effects (indirect effects), use SEM estimation
            ** NA/NC: Identification analysis not available or not conducted
            """)
            if not omit_DAG:
                print(dedent(f"""
                ===========================================================================
                {G}
                """))
        else:
            txt = {'columns': [f"{c_spelled}Causal Effects*", "SoO", "IV", "do-calculus"],
                    'rows': [[f"{c_spelled}Averave Causal Effect, ({c}ACE)", s1, s3, s5],
                             [f"{c_spelled}Averave Controlled Direct Effect ({c}ACDE)", s2, s4, s6]],
                    "footnote" : footnote
                   }
        return txt

    def __print_detailed__(self, *args, **kws):
        conditional = list(self.identification['SoO'].values())[0]['conditional on']
        id = self.identification

        style = kws.get("style", 'text')
        to_print = self.__print_detailed_get_to_print__(*args, **kws)

        txt = ''
        for strategy, parameters in to_print.items():
            txt += dedent(f"""
            Identification method: {strategy}
            ---------------------\
            """)
            for effect_abv in parameters:
                adj        = id[strategy][effect_abv].get('adjusted', False)
                identified = id[strategy][effect_abv].get("identified", False)
                tau_par    = id[strategy][effect_abv].get(style, {'Parametric tau':''})['Parametric tau']
                E_id_np    = id[strategy][effect_abv].get(style, {'Non-parametric':''})['Non-parametric']
                E_id_par   = id[strategy][effect_abv].get(style, {'Parametric(*)':''})['Parametric(*)']
                where      =  (#IDENTIFICATION[strategy][effect_abv]['where'][adj] +
                               IDENTIFICATION[strategy].get(effect_abv, {'where':{adj:''}})['where'][adj] +
                               id[strategy][effect_abv].get('where', ''))
                if strategy=='do' and identified:
                    result = id[strategy][effect_abv][style].get(f"Non-parametric",'Analysis not conducted for {effect_abv}')
                else:
                    result = id[strategy][effect_abv].get(f"result str",'Analysis not conducted for {effect_abv}')

                effect_name = PARAMETER[effect_abv]['name']
                tau         = PARAMETER[effect_abv]['parameter']
                tau_delta1  = tau.replace('d,', 'd+1,').replace('d\'', 'd')
                beta        = f"{tau_delta1} = {tau_par}" if E_id_par else ''
                E           = PARAMETER[effect_abv]['definition']
                # E_id        = IDENTIFICATION[strategy][effect_abv][adj]
                E_id        = IDENTIFICATION[strategy].get(effect_abv, {adj:""})[adj]

                if style=='latex':
                    tau_def = f"{_print2latex(tau)} = {_print2latex(E)}"
                    tau_id = f"{_print2latex(tau)} = {_print2latex(E_id)}"
                    where  = _print2latex(where).replace('\\\\', '\\\\&')
                    beta   = _print2latex(beta)
                    E_id_np  = "Non-parametric: " + E_id_np
                    E_id_par = "Parametric(*): "+ E_id_par
                else:
                    tau_def = f"{tau} = {E}"
                    tau_id  = f"{tau} = {E_id}"
                    # adjusting spaces/identation
                    result   = result.replace("\n", "\n"+" "*34)
                    tau_id  = tau_id.replace("\n", '\n'+" "*41)
                    E_id_np  = "Non-parametric: " + E_id_np.replace("\n", '\n'+" "*24)
                    E_id_par = "  Parametric(*) : "+ E_id_par.replace("\n", '\n'+" "*4)
                    E_id     = E_id.replace("\n", '\n'+" "*41)
                    beta     = beta.replace("\n", '\n'+" "*24)
                    where    = where.replace("\n", '\n'+" "*21)

                if identified:
                    txt += dedent(f"""
                    Parameter: {effect_name} ({effect_abv})
                      {tau_def}
                    Identification:
                      {result}
                    Details:
                      {tau_id}
                      {where}
                    Models:
                      {E_id_np}
                    """)
                    txt += E_id_par if strategy!='do' else ''
                    txt += '\n    '+beta+"\n" if strategy!='do' else ''
                else:
                    txt += dedent("\n"+result+"\n")
                # print(txt)
        return txt

    def __print_detailed_get_to_print__(self, *args, **kws):
        parameters = kws.get("parameter", None)
        strategies = kws.get("strategy", None)

        parameters = [parameters] if isinstance(parameters, str) else parameters
        strategies = [strategies] if isinstance(strategies, str) else strategies

        parameters_available = [list(v.keys()) for _, v in self.identification.items()]
        parameters_available = list(set(itertools.chain.from_iterable(parameters_available)))

        strategies_available = list(self.identification)

        to_print = {}
        if not parameters and not strategies:
            for strategy, effect in self.identification.items():
                to_print[strategy] = list(effect.keys())

        elif parameters and not strategies:
            for parameter in parameters:
                assert parameter in parameters_available,\
                    (f"Parameter {parameter} is currently not available for identification",
                     " analysis with graphical causal models."+
                     f" Available: {parameters_available}")
                strategies = [st for st, par in self.identification.items() if parameter in par.keys()]
                for strategy in strategies:
                    to_print[strategy] = parameters

        elif not parameters and strategies:
            for strategy in strategies:
                assert strategy in strategies_available, (f"Identification strategy {strategy} not available"+
                                                          f" for graphical causal models."+
                                                          f" Available: {strategies_available}" )
                to_print[strategy] = list(self.identification[strategy].keys())

        elif parameters and strategies:
            for strategy in strategies:
                assert strategy in strategies_available, \
                    (f"Identification strategy {strategy} not available"+
                     f" for graphical causal models."+
                     f" Available: {strategies_available}" )
                for parameter in parameters:
                    msg = {st:list(par.keys()) for st, par in self.identification.items()}
                    assert parameter in self.identification[strategy].keys(),\
                        (f"Parameter {parameter} not available for identification strategy {strategy}."+
                         f" Available: {msg}")
                    to_print[strategy] = parameters
                
        return to_print

    def get_dict(self):
        return self.identification

    def plot(self, kws_graph, *args, **kws):
        default_usetex = plt.rcParams["text.usetex"] 
        plt.rcParams["text.usetex"] = True
        plt.rcParams['text.latex.preamble'] = r'\usepackage{amsmath, amssymb, siunitx, bm}'

        G = kws.get("G", None)
        effect = kws.get("effect", True)
        y_do = kws.get("y_do", True)

        title_dag = kws.get("title_dag", None)

        txt, table = self.__plot_get_txt__(*args, **kws)
        figsize, ratio = self.__plot_get_figsize_and_ratio__(txt, table, *args, **kws)
        nrows, ncols   = self.__plot_get_ncols_nrows__(*args, **kws)

        fig, axs = plt.subplots(nrows=nrows, ncols=ncols, figsize=figsize, tight_layout=True,
                                gridspec_kw=ratio)
        # Graph 
        # -----
        ax = axs[0]
        G.plot(ax=ax, title=title_dag, **kws_graph)
        ax = axs[1]

        # identification info
        # -------------------
        kws.pop('details', None)
        ax = self.__plot_info__(ax=ax, txt=txt, table=table, *args, **kws)
            
        plt.axis("off")
        plt.tight_layout()
        plt.show()
        plt.rcParams["text.usetex"] = default_usetex

        return plt, axs
    
    def __plot_info__(self, ax, txt, table, *args, **kws):
        conditional = list(self.identification['SoO'].values())[0]['conditional on']
        conditional = [conditional] if conditional and isinstance(conditional, str) else conditional
        conditional_info = f"(Effects conditional on {', '.join(conditional)})" if conditional else conditional
        
        content = kws.get("info", 'default')
        G = kws.get("G", None)
        y_info = kws.get("y_info", (1.07 if content!='detailed' else 1))
        ratio = kws.get("ratio", True)
        fontsize = kws.get("fontsize", 12)

        title_info = kws.get("title_info", '')
        title_info = title_info or ""

        show_np = kws.get("show_np", True)
        show_linear = kws.get("show_linear", True)
        show_do = kws.get("show_do", True)

        # collect text 
        # ------------
        if not table:
            ax.text(0.01, y_info, s=txt,
                    ha='left', va='top', ma='left',
                    fontdict=dict(weight='normal', style='normal',
                                  color='black', fontsize=fontsize, alpha=1),
                    transform=ax.transAxes
                    )
        else:
            rows = txt['rows']
            columns = txt['columns']

            table_row_heights = kws.get("table_row_heights", [.17, .17, .17])
            table_col_sizes = kws.get("table_col_sizes", [.5, .1, .1, .1])
            table_fontsize = kws.get("table_fontsize", fontsize)

            title_info = "Identified?"
            table = ax.table(
                cellText=rows,
                colLabels=columns,
                cellLoc='left',
                colLoc='left',
                loc='upper left')  # anchors table to top-left corner
            
            table.auto_set_font_size(False)
            table.set_fontsize(table_fontsize)
            cells = table.get_celld()
            for row in range(len(rows) + 1):  # +1 for header
                for col in range(len(columns)):
                    cell = cells[(row, col)]
                    cell.set_width(table_col_sizes[col])
                    cell.set_height(table_row_heights[row])

            ax.text(0.01, .0, s=txt['footnote'],
                    ha='left', va='bottom', ma='left',
                    fontdict=dict(weight='normal', style='normal',
                                  color='black', fontsize=fontsize, alpha=1),
                    transform=ax.transAxes)

        title_info = title_info + f" {conditional_info}" if conditional else title_info
        ax.set_title(title_info, fontsize=13, loc='left', pad=10)

        # Splines (axes lines)
        borders = False if table else True
        for side in ['bottom', 'left', 'right', 'top']:
            ax.spines[side].set_visible(borders)
            ax.spines[side].set_linewidth(1.3)
            ax.tick_params(top=False, bottom=False, left=False, right=False,
                           labeltop=False, labelbottom=False, labelleft=False, labelright=False)

        return ax

    def __plot_get_figsize_and_ratio__(self, txt, table, *args, **kws):
        # ratio
        content = kws.get("info", 'default')
        if content=='default':
            rh = kws.get("ratio", None) or [1/2, 1/2]
            rw = [1]
            fig_width = 10
        elif content=='concise':
            rh = kws.get("ratio", None) or [2/3, 1/3]
            rw = [1]
            fig_width = 10
        elif content=='detailed':
            rw = ratio = kws.get("ratio", None) or [1/2, 1/2]
            rh = [1]
            fig_width = 13
        ratio = {'width_ratios': rw,
                 'height_ratios': rh}

        num_lines = 10 if table else sum(1 for line in txt.splitlines() if line.strip())
        height_per_line = kws.get("txt_line_height", .55)
        
        fig_height = max(2, num_lines * height_per_line)  # set minimum height if desired
        figsize = kws.get("figsize", None) or [fig_width, np.max([fig_height, 5])]

        return figsize, ratio

    def __plot_get_txt__(self, *args, **kws):
        content = kws.get("info", 'default')
        table = False
        if content=='default':
            txt = self.__print_default__(style='latex')
            txt = re.sub(r'^(Conditional.*|Average.*)\n[-]{2,}.*\n', r'\\textbf{\\underline{\1}}\n', txt, flags=re.MULTILINE)
        elif content=='concise':
            table = True
            txt = self.__print_concise__(table=table)
        elif content=='detailed':
            parameter = kws["kws_detailed"].get("parameter", None)
            strategy = kws["kws_detailed"].get("strategy", None)
            assert parameter, "To plot details, 'parameter' must be provided. Use kws_detailed={'parameter':...}"
            assert strategy, "To plot details, 'strategy' must be provided. Use kws_detailed={'strategy':...}"

            txt = self.__print_detailed__(style='latex', strategy=strategy, parameter=parameter)
            txt = re.sub(r'^(Identification method.*)\n[-]{2,}.*\n', r'\\textbf{\\underline{\1}}\n', txt, flags=re.MULTILINE)
        txt = txt.replace("-*\n", '') if not table else txt
        return txt, table

    def __plot_get_ncols_nrows__(*args, **kws):
        info = kws.get("info", 'default')
        ncols = kws.get("ncols", None)
        nrows = kws.get("nrows", None)
        if info=='default':
            ncols   = ncols or 1
            nrows   = nrows or 2
        elif info=='concise':
            ncols   = ncols or 1
            nrows   = nrows or 2
        elif info=='detailed':
            ncols   = ncols or 2
            nrows   = nrows or 1
        return nrows, ncols

    def __tidy__(self):
        pass
    
    def __str__(self):
        self.__repr__()
        return ''
    
class examples:

    def __new__(cls, which=None, print_DAG=False, *args, **kws):
        """
        Retrieve a predefined example DAG or list available examples.

        Parameters
        ----------
        which : str or None, optional
            Name of the example to load. When ``None``, the function prints the
            list of available examples (optionally with their DAG representations)
            and returns ``None``.
        print_DAG : bool, optional
            If ``True`` and ``which`` is ``None``, print the textual
            representation of each example DAG. Defaults to ``False``.
        *args :
            Additional positional arguments forwarded to the example factory.
        **kws :
            Additional keyword arguments forwarded to the example factory.

        Returns
        -------
        DAG or None
            Instantiated `DAG` object when ``which`` matches an example; otherwise
            ``None``.

        Examples
        --------
        >>> examples() # print the list of predefined examples
        >>> G = examples('Frontdoor') # load DAG from predefined example
        >>> isinstance(G, DAG)
        True
        """
        if not which:
            examples._print_examples(print_DAG=print_DAG)
            dag = None
        else:
            try:
                dag = examples._get_examples(which, *args, **kws)
            except KeyError:
                # friendly suggestion for typos
                suggestion = difflib.get_close_matches(which, examples._get_examples().keys(), n=3, cutoff=0.4)
                hint = f" Did you mean: {', '.join(suggestion)}?" if suggestion else ""
                raise ValueError(f"Unknown example '{which}'.{hint}")
        return DAG(**dag) if dag else None

    def _get_examples(which=None, *args, **kws):
        all_examples = {
            "Not identifiable" : examples._example_not_identifiable(*args, **kws),
            "One confounder"  : examples._example_one_confounder(*args, **kws),
            "Two confounders" : examples._example_two_confounder(*args, **kws),
            "Front-door"       : examples._example_front_door(*args, **kws),
            "IV with 1 instrument"  : examples._example_iv_1_instrument(*args, **kws),
            "IV with 3 instruments"  : examples._example_iv_3_instruments(*args, **kws),
            "SoO, IV, and do identified with 1 confounder": examples._example_soo_iv_do_one_counfounder(*args,
                                                                                                        **kws),
            "Mediation: 2 sequential 1 confounder" : examples._example_mediation_2_sequential_1_confounder(*args,
                                                                                                           **kws),
            # "Back-door": self._back_door(),
            # Pearl's book
            "Pearl Example 1.1 (a)"  : examples._example_pearl_fig_1_1_a(*args, **kws),
            "Pearl Example 1.1 (b)"  : examples._example_pearl_fig_1_1_b(*args, **kws),
            "Pearl Example 1.2"  : examples._example_pearl_fig_1_2(*args, **kws),
            "Pearl Example 1.3 (a)"  : examples._example_pearl_fig_1_3_a(*args, **kws),
            "Pearl Example 1.3 (b)"  : examples._example_pearl_fig_1_3_b(*args, **kws),
            "Pearl Example 3.1"  : examples._example_pearl_fig_3_1(*args, **kws),
            "Pearl Example 3.4"  : examples._example_pearl_fig_3_4(*args, **kws),
            "Pearl Example 3.5"  : examples._example_pearl_fig_3_5(*args, **kws),
        }
        res = all_examples[which] if which else all_examples
        return res

    def _print_examples(print_DAG):
        print(dedent("""
        List of available examples:
        --------------------------\
        """))
        for i, (name, example) in enumerate(examples._get_examples().items()):
            print(f"{i+1}. {name}")
            if print_DAG:
                print(DAG(**example))
        print(f"\nUsage: examples(which='<example name>')"+
              f"\nExample: G = examples(which='{name}')")
        if not print_DAG:
            print("Note: To print the associated DAG of each example, use examples(print_DAG=True)")
        return None
        
    def _example_not_identifiable(*args, **kws):
        dag = """
        D  -> Y
        D <-> Y
        Z -> {D, Y}
        """
        pos = {"D": (0, 0), "Y": (1, 0), "Z": (0.5, 1)}
        roles = {"Exposure": "D", "Outcome": "Y"}
        labels = None
        return dict(graph=dag, nodes_role=roles, nodes_position=pos, nodes_label=labels)

    def _example_one_confounder(*args, **kws):
        dag = """
        D  -> Y
        Z1 -> {D, Y}
        """
        pos = {"D": (0, 0), "Y": (1, 0), "Z1": (0.5, 1)}
        roles = {"Exposure": "D", "Outcome": "Y"}
        labels = {'Z1':"$Z_1$"}
        return dict(graph=dag, nodes_role=roles, nodes_position=pos, nodes_label=labels)

    def _example_two_confounder(*args, **kws):
        dag = """
        D  -> Y
        Z1 -> {D, Y}
        Z2 -> {D, Y}
        """
        pos = {"D": (0, 0), "Y": (1, 0), "Z1": (0.5, 1), "Z2": (0.5, -1)}
        roles = {"Exposure": "D", "Outcome": "Y"}
        labels = {'Z2':"$Z_2$", 'Z1':"$Z_1$"}
        return dict(graph=dag, nodes_role=roles, nodes_position=pos, nodes_label=labels)

    def _example_front_door(*args, **kws):
        dag  = """
        U -> {D, Y}
        D  -> Z -> Y
        Z2 -> {D, Y}
        """
        pos = {'D': (0 , 0),
               'Z': (.5, 0),
               'Y': (1 , 0),
               'U': (.5, 1),
               'Z2': (.5, -1),
               }
        roles = {'Exposure': "D",
                 'Outcome' : "Y",
                 "Latent"  : "U"
                 }
        labels = {'Z2':"$Z_2$"}
        return dict(graph=dag, nodes_role=roles, nodes_position=pos, nodes_label=labels)

    def _example_iv_1_instrument(*args, **kws):
        dag  = """
        X <-> Y
        Z -> X -> Y
        """
        pos = {'Z': ( 0, 0),
               'X': ( .5, -1),
               "Y": ( 1,-2)}
        roles = {'Exposure': "X",
                 'Outcome' : "Y"}
        edge_labels = {('Z', 'X'): "$\\beta$",
                       ('X', 'Y'): "$\\alpha$"}
        labels = None
        return dict(graph=dag, nodes_role=roles, nodes_position=pos, nodes_label=labels,
                    edge_label=edge_labels)

    def _example_iv_3_instruments(*args, **kws):
        dag  = """
        D <-> Y
        Z1 -> D -> Y
        D <- X1 -> Y
        Z1<- Z2 -> Y
        Z1<- Z3 -> D
        Z1-> Z4 <- X2 -> Y
        """
        pos = {'D':  ( 0, 0),
               "Y":  ( 1, 0),
               'Z1': (-1, 0),
               "Z2": (0,-.5),
               "Z3": (-.5, 1),
               "Z4": (-.5,-1),
               "X2": ( .5,-1),
               "X1": (.5, 1),
               }
        roles = {'Exposure': "D",
                 'Outcome' : "Y"}
        edge_labels = None
        labels = {'X1': '$X_1$',
                  'X2': '$X_2$',
                  'Z1': '$Z_1$',
                  'Z2': '$Z_2$',
                  'Z3': '$Z_3$',
                  'Z4': '$Z_4$',
                  }
        return dict(graph=dag, nodes_role=roles, nodes_position=pos, nodes_label=labels,
                    edge_label=edge_labels)

    def _example_soo_iv_do_one_counfounder(*args, **kws):
        dag  = """
        Z  -> D -> Y
        D <- X1 -> Y
        Z <- X2 -> Y
        """
        pos = {'D':  ( 0, 0),
               "Y":  ( 1, 0),
               'Z': (-1, 0),
               "X2": ( .5,-1),
               "X1": (.5, 1),
               }
        roles = {'Exposure': "D",
                 'Outcome' : "Y"}
        edge_labels = None
        labels = {'X1': '$X_1$',
                  'X2': '$X_2$',
                  }
        return dict(graph=dag, nodes_role=roles, nodes_position=pos, nodes_label=labels,
                    edge_label=edge_labels)

    def _example_mediation_2_sequential_1_confounder(*args, **kws):
        dag  = """
        D -> M1 -> M2 -> Y
        D -> Y
        D  <- Z -> Y
        """
        pos = {'D' : (0 , 0),
               'M1': (.5, 1),
               'M2': ( 1, 1),
               'Y' : (1.5 , 0),
               'Z': (.75, -1),
               }
        roles = {'Exposure': "D",
                 'Outcome' : "Y",
                 }
        labels = {"M1":'$M_1$',
                  "M2":'$M_2$',
                  }
        return dict(graph=dag, nodes_role=roles, nodes_position=pos, nodes_label=labels)

    def _example_pearl_fig_1_1_a(*args, **kws):
        """
        Source:
        - Pearl, J. (2009). Causality: Models, Reasoning and Inference. : Cambridge University Press.
        """
        dag  = """
        W -> Z -> Y
        Z <-> X -> Y
        """
        pos = {'Z': ( 0, 0),
               'X': ( 1, 0),
               "Y": ( .5,-1),
               'W': ( 0, 1),
               }
        roles = {'Exposure': "X",
                 'Outcome' : "Y"
                 }
        edge_labels = None
        labels = None
        return dict(graph=dag, nodes_role=roles, nodes_position=pos, nodes_label=labels,
                    edge_label=edge_labels)

    def _example_pearl_fig_1_1_b(*args, **kws):
        """
        Source:
        - Pearl, J. (2009). Causality: Models, Reasoning and Inference. : Cambridge University Press.
        """
        dag  = """
        Z -> {W, Z, Y}
        Y -> X
        """
        pos = {'Z': ( 0, 0),
               'X': ( 1, 0),
               "Y": ( .5,-1),
               'W': ( 0, 1),
               }
        roles = {'Exposure': "Z",
                 'Outcome' : "Y"
                 }
        edge_labels = None
        labels = None
        return dict(graph=dag, nodes_role=roles, nodes_position=pos, nodes_label=labels,
                    edge_label=edge_labels)

    def _example_pearl_fig_1_2(*args, **kws):
        """
        Source:
        - Pearl, J. (2009). Causality: Models, Reasoning and Inference. : Cambridge University Press.
        """
        dag  = """
        X1 -> {X2, X3} -> X4 -> X5
        """
        pos = {"X1": ( 0, 0),
               "X2": ( 1, -1),
               "X3": ( -1,-1),
               "X4": ( 0, -2),
               "X5": ( 0, -3),
               }
        roles = {'Exposure': "X1",
                 'Outcome' : "X5"
                 }
        edge_labels = None
        labels = {"X1" : 'X1 (Season)',
                  "X2" : "X2 (Rain)",
                  "X3" : "X3 (Sprinkler)",
                  "X4" : 'X4 (Wet)',
                  "X5" : 'X5 (Slippery)'
                  }
        return dict(graph=dag, nodes_role=roles, nodes_position=pos, nodes_label=labels,
                    edge_label=edge_labels)

    def _example_pearl_fig_1_3_a(*args, **kws):
        """
        Source:
        - Pearl, J. (2009). Causality: Models, Reasoning and Inference. : Cambridge University Press.
        """
        dag  = """
        X -> Z1 <- Z2 <- Z3 <- Y
        Z1 <-> Z3
        """
        pos = {"X":  (0 ,0),
               "Z1": (1 ,0),
               "Z2": (2 ,0),
               "Z3": (3 ,0),
               "Y" : (4 ,0),
               }
        roles = {'Exposure': "X",
                 'Outcome' : "Y"
                 }
        edge_labels = None
        labels = None
        return dict(graph=dag, nodes_role=roles, nodes_position=pos, nodes_label=labels,
                    edge_label=edge_labels)
        
    def _example_pearl_fig_1_3_b(*args, **kws):
        """
        Source:
        - Pearl, J. (2009). Causality: Models, Reasoning and Inference. : Cambridge University Press.
        """
        dag  = """
        X -> Z2 -> Z1 -> X
        Y -> Z2
        """
        pos = {"X":  (0 ,0),
               "Z1": (1 ,1),
               "Z2": (2 ,0),
               "Y" : (3 ,0),
               }
        roles = {'Exposure': "X",
                 'Outcome' : "Y"
                 }
        edge_labels = None
        labels = None
        return dict(graph=dag, nodes_role=roles, nodes_position=pos, nodes_label=labels,
                    edge_label=edge_labels)

    def _example_pearl_fig_3_1(*args, **kws):
        """
        Source:
        - Pearl, J. (2009). Causality: Models, Reasoning and Inference. : Cambridge University Press.
        """
        dag  = """
        X -> {Z2, Y}
        Z2 -> {Z3, Y}
        Z3 -> Y
        Z1 -> Z2
        B -> Z3
        Z0 -> {X, Z1, B}
        """
        pos = {"X":  (0 ,0),
               "Z0": (1 ,1),
               "Z1": (1 ,.5),
               "Z2": (1 ,0),
               "Z3": (2 ,0),
               "B":  (1.5 ,.5),
               "Y" : (1 ,-.5),
               }
        roles = {'Exposure': "X",
                 'Outcome' : "Y",
                 'Latent'  : ['Z0', 'B']
                 }
        edge_labels = None
        labels = {"Z0": "$Z_0$",
                  "Z1": "$Z_1$",
                  "Z2": "$Z_2$",
                  "Z3": "$Z_3$",
                  }
        return dict(graph=dag, nodes_role=roles, nodes_position=pos, nodes_label=labels,
                    edge_label=edge_labels)
        
    def _example_pearl_fig_3_4(*args, **kws):
        """
        Source:
        - Pearl, J. (2009). Causality: Models, Reasoning and Inference. : Cambridge University Press.
        """
        dag  = """
        X1 -> {X3, X4}
        X2 -> {X4, X5}
        X3 -> Xi
        X4 -> {Xi, Xj}
        X5 -> Xj
        X6 -> Xj
        Xi -> X6
        """
        pos = {"Xi":  (0, 0),
               'Xj':  (2, 0),
               "X1":  (0, 2),
               "X2":  (2, 2),
               "X3":  (0, 1),
               "X4":  (1, 1),
               "X5":  (2, 1),
               "X6":  (1, 0),
               }
        roles = {'Exposure': "Xi",
                 'Outcome' : "Xj",
                 }
        edge_labels = None
        labels = {"Xi": "$X_i$",
                  "Xj": "$X_j$",
                  "X1": "$X_1$",
                  "X2": "$X_2$",
                  "X3": "$X_3$",
                  "X4": "$X_4$",
                  "X5": "$X_5$",
                  "X6": "$X_6$",
                  }
        return dict(graph=dag, nodes_role=roles, nodes_position=pos, nodes_label=labels,
                    edge_label=edge_labels)

    def _example_pearl_fig_3_5(*args, **kws):
        dag  = """
        U -> {X, Y}
        X  -> Z -> Y
        """
        pos = {'X': (0 , 0),
               'Z': (.5, 0),
               'Y': (1 , 0),
               'U': (.5, 1),
               }
        roles = {'Exposure': "X",
                 'Outcome' : "Y",
                 "Latent"  : "U"
                 }
        labels = None
        return dict(graph=dag, nodes_role=roles, nodes_position=pos, nodes_label=labels)
