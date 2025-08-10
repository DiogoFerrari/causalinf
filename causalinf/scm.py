import tidypolars4sci as tp
import networkx as nx
import re, itertools
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
                 DAG=None,
                 SEM=None,
                 data=None,
                 # node
                 nodes_role=None,
                 nodes_label=None,
                 nodes_position=None,
                 # edges
                 edge_label=None
                 ):
        """
        DAG: a string with the a DAG
        SEM: a string with the structural equation model (SEM).
             If both DAG and SEM are provided, the 'SEM' is ignored.
             It follows the formula sintax for each equation.
             Multiline with comments and blank lines are allowed
             in the string. See examples below.
             Edge parameter and path effect definition are also
             allowed in the string. If edge parameters are provided,
             they are used as 'edge_labels', except if the later is also
             provided. Edge parameter and path effect definition
             must follow variable name conventions.
             Latent variables are inferred from the formula and
             nodes_role is updated.
             See examples below.

        
        """
        self.__get_nodes_role__(nodes_role)
        self.nodes_label = nodes_label or {}
        self.nodes_position = nodes_position
        self.edge_label = edge_label or {}
        self.data = data

        self.build_DAG(DAG, SEM)

    def __repr__(self):
        self.__print_DAG__()
        return ''

    def __str__(self):
         self.__repr__()
         return ''

    def __print_DAG__(self):
        d = [f"{n1} -> {n2}" for n1, n2 in self.get_edges()['directed']]
        d = '\n'.join(d)

        b = [f"{n1} <-> {n2}" for n1, n2 in self.get_edges()['bidirected']]
        b = '\n'.join(b)

        u = [f"{n1} <-> {n2}" for n1, n2 in self.get_edges()['undirected']]
        u = '\n'.join(u)

        roles = [f"{role}: {', '.join(nodes)}" for role, nodes in self.nodes_role.items()]
        roles = "\n".join(roles)

        out = f"DAG:\n{d}\n{b}\n{u}\n{roles}"
        print(out)
        return out

    def __get_nodes_role__(self, nodes_role):
        self.nodes_role = nodes_role or {}
        for role, node in self.nodes_role.items() :
            if role=='Outcome':
                assert isinstance(node, str), "Check nodes_role. Node 'Outcome' must be a string"

            else:
                assert isinstance(node, str) or isinstance(node, list), \
                    "Check nodes_role. Nodes 'Exposure' and 'Latent' must be strings or lists"
                node = node if isinstance(node, list) else [node]
                self.nodes_role[role] = node
        
    def build_DAG(self, DAG, SEM):
        # networkx
        if DAG is not None:
            self.__dag2nx__(DAG)
        elif SEM is not None:
            DAG, edge_label, nodes_role = self.__parse_sem__(SEM)
            self.__dag2nx__(DAG)
            self.set_node_role(nodes_role )
            if not self.edge_label:
                self.set_edge_label(edge_label) 
        else:
            assert True, "Either DAG or the SEM must be provided."

        # dagitty
        self.__nx2dagitty__()
            
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

    def __dag2nx__(self, DAG) -> nx.DiGraph:
        """
        Parse a simple dagitty-like DAG text into a networkx.DiGraph.
        Supports ->, <-, <-> edges and  'X -> {A,B}' shorthand

        - Directed edges are added normally.
        - Bidirected edges (<->) are replaced with a latent node.

        Returns:
            G (nx.DiGraph): A directed graph with optional latent confounders.
        """
        # expand shorthand first
        DAG = self.__dag2nx_parse__(DAG)

        G = nx.DiGraph()
        self.directed = []
        self.bidirected = []
        self.undirected = []

        latent_count = 0

        lines = DAG.strip().splitlines()
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue  # skip empty/comment lines

            # Match directed edge A -> B
            match = re.match(r"(\w+)\s*->\s*(\w+)", line)
            if match:
                a, b = match.groups()
                G.add_edge(a, b)
                self.directed += [(a, b)]
                continue

            # Match directed edge B <- A
            match = re.match(r"(\w+)\s*<-\s*(\w+)", line)
            if match:
                b, a = match.groups()
                G.add_edge(a, b)
                self.directed += [(a, b)]
                continue

            # Match bidirected edge B <-> A
            match = re.match(r"(\w+)\s*<->\s*(\w+)", line)
            if match:
                b, a = match.groups()
                G.add_edge(a, b)
                G.add_edge(b, a)
                self.bidirected += [((a, b), (b, a))]
                continue

            # Match bidirected edge B -- A
            match = re.match(r"(\w+)\s*--\s*(\w+)", line)
            if match:
                b, a = match.groups()
                G.add_edge(a, b)
                G.add_edge(b, a)
                self.undirected += [(a, b)]
                continue

            raise ValueError(f"Unrecognized line format: '{line}'")

        # setting nodes attributes
        for role, nodes in self.nodes_role.items():
            for node in nodes:
                nx.set_node_attributes(G, {node:True}, role)

        self.dag = DAG
        self.G = G
        return None

    def __dag2nx_parse__(self, dag_text:str) -> str:
        res = []
        regex  = re.compile(r"(\w+|\{[^}]+\})\s*(<->|<-|->|--)\s*(\w+|\{[^}]+\})")
        
        dag_text = self.__dag2nx_parse_line_paths__(dag_text)
        for ln in dag_text.strip().splitlines():
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
                        res.append(f"{n1} {edge} {n2}")
                else:
                    raise ValueError(f"Unrecognized line format: '{ln}'")

        return "\n".join(res)

    def __dag2nx_parse_line_paths__(self, dag):
        # Split the path string by spaces to separate nodes and arrows
        lines = dag.split("\n")

        res = []
        for path in lines:
            delimiter_pattern = re.compile(r'(->|<-|<->)')
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

    def __nx2dagitty__(self):
        # Convert to dagitty string: "dag { A -> B; B -> C; ... }"
        edges = [f"{u} -> {v}" for u, v in self.G.edges()]
        edges = '; '.join(edges)

        roles = ''
        for role, nodes in self.nodes_role.items():
            for node in nodes:
                roles += f"{node} [{role.lower()}]\n"

        # Load dagitty and pass the DAG string
        dagitty_str = f"dag {{ {edges} \n {roles} }}"
        self.__dagitty__ = dagitty.dagitty(dagitty_str)

    def __dagitty2nx__(self, dag_dagitty):
        eq = convert().tibble2tp(dagitty.edges(dag_dagitty))
        res = ''
        for a, b, e, *_ in eq.to_polars().iter_rows():
            res += f"{a} {e} {b}\n"
        return res

    # nodes 
    # -----
    def nodes_info(self):
        return dict(self.G.nodes(data=True))

    def get_nodes(self, exclude_latent=True):
        nodes = list(self.nodes_info().keys())
        latent_nodes = self.nodes_role.get("Latent", None)
        latent_nodes = latent_nodes if isinstance(latent_nodes, list) else [latent_nodes ]

        if exclude_latent and latent_nodes is not None:
            nodes = [n for n in nodes if n not in latent_nodes]
        return nodes
        
    def get_edges(self):
        G = self.G
        directed = []
        bidirected = []
        for u, v in G.edges():
            if G.has_edge(v, u):  # Check if the reverse edge exists
                # To avoid adding the edge twice (e.g., (A,B) and (B,A))
                # we can ensure u < v, or just add one of the directions
                # and store it as an undirected relationship.
                if (u, v) not in bidirected and (v, u) not in bidirected:
                    bidirected.append((u, v)) 
            else:
                directed.append((u, v))
        edges = {"directed": directed, 'bidirected':bidirected, 'undirected':undirected}
        return edges
        
    def set_node_label(self, nodes_label):
        for node, label in nodes_label.items():
            self.nodes_label[node] = label

    def set_node_role(self, nodes_role):
        for node, role in nodes_role.items():
            self.nodes_role[node] = role
        self.__nx2dagitty__()

    def set_node_position(self, position):
        for node, p in position.items():
            self.position[node] = p

    # edges 
    # -----
    def set_edge_label(self, edge_label):
        for edge, label in edge_label.items():
            self.edge_label[edge] = label

    # plots 
    # -----
    def plot(self,
             # nodes
             nodes_position=None,
             nodes_role=None,
             nodes_label=None,
             dag_style = 'default',
             # 
             node_subset=None,
             node_shape=None,
             node_size = None,
             node_color = None,
             node_edge_color='black',
             node_obs_border_style='-',
             # 
             node_latent_show=True,
             node_latent_color_edge='black',
             node_latent_border_style='--',
             # 
             node_label_or_name = 'label',
             node_label_box=True,
             node_label_box_color_background='white',
             node_label_box_color_edge='black',
             node_label_box_linewidth=1,
             node_label_fontsize=None,
             node_label_fontweight='normal',
             node_label_adj_x=None,
             node_label_adj_y=None,
             node_label_box_style="square",
             node_label_box_margin=.5,
             # edges
             edge_subset=None,
             # edges directed
             edge_directed_color = 'black',
             edge_directed_linewidth = 1.5,
             # edges bidirected
             edge_bidirected_color = 'black',
             edge_bidirected_linewidth = 1.5,
             edge_bidirected_arc = 0.5,
             # edges labels
             edge_label=None,
             edge_label_position=.5,
             edge_label_size=15,
             edge_label_color='black',
             edge_label_rotate=False,
             edge_label_kws={},
             edge_margin_tail=None,
             edge_margin_head=None,
             # legend
             legend=True,
             legend_loc='best',
             legend_fontsize=10,
             figsize = [6, 4],
             usetex = True,
             ax=None,
             *args,
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
            node_label_or_name  (str or None; Default='label'): One of 'label', 'name', or 'none'.
                If 'label', use labels if provided; If 'name', always use node name; If 'none',
                don't omit labels and names of nodes altogether.
            node_label_adj_x (float or dict): displaces the labels in the x direction. If dict, the keys
                should be the node labels or name, and displacement will be applied only to those points
                specified in the dict. If float, the same displacement is applied to all nodes.
            node_label_adj_x (float or dict): same as node_label_adj_y, but for the y axis
            dag_style (str): specific styles for nodes and arrows
                  - 'default': nodes in circles with labels in their middle
                  - 'rectangle': nodes in rectangles with labels in their middle
                  - 'pearl': nodes as dots with labels next to them (use node_label_adj_x and node_label_adj_y
                             to adjust the location of the labels)
                  All features can be overwrittied by specifying the value of the parameters for the plot.
        """
        default_usetex = plt.rcParams["text.usetex"] 
        plt.rcParams["text.usetex"] = usetex

        if dag_style=='default':
            node_shape= node_shape or "o"
            node_size = node_size or 1000
            node_label_fontsize = node_label_fontsize or 10
            edge_margin_tail= edge_margin_tail or 20
            edge_margin_head= edge_margin_head or 20
            node_label_adj_x= node_label_adj_x or 0
            node_label_adj_y= node_label_adj_y or 0
            node_color = node_color or {"Exposure": "lightgray",
                                        "Outcome" : "gray",
                                        "Observed": 'white',
                                        'Latent'  : "white"}

        elif dag_style=='rectangle':
            node_shape= node_shape or ""
            node_size = node_size or 1000
            node_label_fontsize = node_label_fontsize or 10
            edge_margin_tail= edge_margin_tail or 20
            edge_margin_head= edge_margin_head or 20
            node_label_adj_x= node_label_adj_x or 0
            node_label_adj_y= node_label_adj_y or 0
            node_color = node_color or {"Exposure": "lightgray",
                                        "Outcome" : "gray",
                                        "Observed": 'white',
                                        'Latent'  : "white"}

        elif dag_style=='pearl':
            node_shape= node_shape or "."
            node_size = node_size or 200
            node_label_fontsize = node_label_fontsize or 13
            edge_margin_tail= edge_margin_tail or 0
            edge_margin_head= edge_margin_head or 0
            node_label_adj_x= node_label_adj_x or .01
            node_label_adj_y= node_label_adj_y or .01
            node_color = node_color or {'Exposure':'grey',
                                        'Outcome':'black',
                                        'Latent':'white',
                                        'Observed':'black'}

        assert isinstance(node_label_adj_x, (dict, float, int)), "node_label_adj_x must be a dict or a number."
        assert isinstance(node_label_adj_y, (dict, float, int)), "node_label_adj_y must be a dict or a number."

        # nodes
        nodes_role = nodes_role or (self.nodes_role or {})
        use_labels = node_label_or_name is not None and node_label_or_name=='label' 
        nodes_label = nodes_label or (self.nodes_label or {}) if use_labels else {}
        # node positions
        nodes_position = nodes_position or self.nodes_position
        # node labels
        node_label_adj_x = self.__plot_label_adj__(node_label_adj_x, nodes_label)
        node_label_adj_y = self.__plot_label_adj__(node_label_adj_y, nodes_label)
        # node roles
        latent_nodes = set(nodes_role.get('Latent', []))
        exposure_nodes = set(nodes_role.get('Exposure', []))
        outcome_nodes = set(nodes_role.get('Outcome', []))
        # edges
        edge_label = edge_label or self.edge_label
        edge_margin_tail = self.__plot_edge_margin__(edge_margin_tail)
        edge_margin_head = self.__plot_edge_margin__(edge_margin_head)
        #

        G_draw = self.G.copy()
        node_subset = set(node_subset or G_draw.nodes())
        edge_subset = edge_subset or G_draw.edges()


        
        # figure 
        # ------
        if ax is None:
            fig, ax = plt.subplots(figsize=figsize, tight_layout=True)
        plt.sca(ax) # Set current axis

        # position 
        # --------
        if not nodes_position:
            try:
                from networkx.drawing.nx_pydot import graphviz_layout
                nodes_position = graphviz_layout(G_draw, prog="dot")
            except ImportError:
                nodes_position = nx.spring_layout(G_draw)

        # nodes
        # -----
        latent_nodes = latent_nodes & node_subset
        observed_nodes = node_subset - latent_nodes
        nodes_to_show = observed_nodes.union(latent_nodes) if node_latent_show else observed_nodes 
        nodes_to_omit = node_subset - nodes_to_show 
        # 
        node_shape = '' if node_shape is None or node_shape=='squared' else node_shape
        node_edge_color = None if node_shape is None else node_edge_color
        options = {
            "node_shape": node_shape,
            'node_color': [node_color["Exposure"] if n in exposure_nodes else
                           node_color["Outcome"] if n in outcome_nodes else
                           node_color["Observed"] for n in observed_nodes],
            "node_size": node_size,
            "edgecolors": "black",
            "linewidths": 1,
        }
        # observed
        nodes = nx.draw_networkx_nodes(G_draw, nodes_position, nodelist=observed_nodes,
                                       ax=ax, **options)
        nodes.set_linestyle(node_obs_border_style)
        # latent
        if node_latent_show:
            nodes = nx.draw_networkx_nodes(G_draw, nodes_position, nodelist=list(latent_nodes),
                                           node_color=node_color['Latent'], edgecolors=node_latent_color_edge,
                                           linewidths=1, node_size=node_size, node_shape=node_shape,
                                           ax=ax)
            nodes.set_linestyle(node_latent_border_style)
        # labels
        if node_label_or_name is not None:
            final_labels = {n: nodes_label.get(n, n) for n in G_draw.nodes()}
            labels = []
            for n in nodes_to_show:
                label = final_labels.get(n, n)
                x, y = nodes_position[n]

                # Determine background color based on role
                if n in exposure_nodes:
                    fc = node_color["Exposure"]
                    linetype = node_obs_border_style
                elif n in outcome_nodes:
                    fc = node_color["Outcome"]
                    linetype = node_obs_border_style
                elif n in latent_nodes:
                    fc = node_color["Latent"]
                    linetype = node_latent_border_style
                else:
                    fc = node_color["Observed"]
                    linetype = node_obs_border_style

                bbox = None
                if node_label_box and not node_shape:
                    bbox = {
                        "boxstyle": f"{node_label_box_style},pad={node_label_box_margin}",
                        "fc": fc,
                        "ec": node_label_box_color_edge,
                        "lw": node_label_box_linewidth,
                        "linestyle": linetype,
                        "alpha": 1}

                plt.text(x + node_label_adj_x[label],
                         y + node_label_adj_y[label],
                         label, fontweight=node_label_fontweight,
                         fontsize=node_label_fontsize, ha='center', va='center', bbox=bbox)

        # edges 
        # -----
        # directed
        attr = {}
        for u, v in self.directed:
            style = attr.get("style", "solid")
            color = edge_directed_color or 'black'
            curved = attr.get("curved", False)
            rad = 0.33 if curved else 0.0
            arrowhead = 20 if not curved else 1
            if u in nodes_to_show and v in nodes_to_show:
                nx.draw_networkx_edges(G_draw, nodes_position,
                                       edgelist=[(u, v)],
                                       style=style,
                                       edge_color=color,
                                       connectionstyle=f"arc3,rad=-{rad}",
                                       arrows=True,
                                       # arrowstyle='-|>',     # arrow at both ends
                                       arrowsize=arrowhead,
                                       min_source_margin=edge_margin_tail[(u, v)],
                                       min_target_margin=edge_margin_head[(u, v)],
                                       width=edge_directed_linewidth,
                                       ax=ax)
        # bidirected
        for (u, v), (v2, u2) in self.bidirected:
            style = attr.get("style", "dashed")
            color = edge_bidirected_color or 'black'
            curved = attr.get("curved", False)
            rad = 0.33 if curved else 0.0
            arrowhead = 20 if not curved else 1
            if u in nodes_to_show and v in nodes_to_show:
                nx.draw_networkx_edges(
                    G_draw,
                    nodes_position,
                    edgelist=[(u, v)], style=style, edge_color=color,
                    # connectionstyle="angle,angleA=30,angleB=30",
                    connectionstyle=f"arc3,rad=-{edge_bidirected_arc}",
                    arrows=True, arrowstyle='<|-|>', arrowsize=arrowhead,
                    # 
                    min_source_margin=edge_margin_tail[((u, v), (v2, u2))],
                    min_target_margin=edge_margin_head[((u, v), (v2, u2))],
                    width=edge_bidirected_linewidth,
                     ax=ax
                )
        # edge labels
        if edge_label and nodes_position:
            for u, v in self.directed + self.bidirected:
                if u in nodes_to_show and v in nodes_to_show:
                    nx.draw_networkx_edge_labels(
                        G_draw,
                        nodes_position,
                        font_size = edge_label_size, edge_labels = edge_label,
                        font_color = edge_label_color, rotate=edge_label_rotate,
                        label_pos=edge_label_position, **edge_label_kws)

        # Optional legend
        if legend and nodes_role:
            legend_elements = []
            for role in nodes_role:
                # role = role.title()
                marker = 'o' if role !="Latent" else ''
                markeredgecolor = 'black' if role !="Latent" else node_latent_color_edge
                linestyle = '' if role !="Latent" and node_latent_show and \
                    len(latent_nodes)>0 else node_latent_border_style
                legend_elements += [
                    Line2D([0], [0], marker=marker, color='black', label=role,
                           markeredgecolor=node_latent_color_edge,
                           markerfacecolor=node_color[role],
                           markersize=10,
                           linestyle=linestyle
                           )
                ]
            plt.legend(handles=legend_elements, loc=legend_loc, fontsize=legend_fontsize, frameon=False)

        plt.axis("off")
        plt.tight_layout()
        plt.show()
        plt.rcParams["text.usetex"] = default_usetex

        return ax
    
    def plot_paths(self, exposure=None, outcome=None, adj_set=None, directed=False,
                   show_full_dag = True,
                   title_fontsize = 10,
                   figsize=(16, 9)
                   ):
        adj_set = [adj_set] if isinstance(adj_set, str) else adj_set

        paths = self.paths(exposure=exposure, outcome=outcome, adj_set=adj_set, directed=directed)
        npaths = len(paths)
        ncols = int(math.ceil(math.sqrt(npaths)))
        nrows = int(math.ceil(npaths / ncols))
        fig, axs = plt.subplots(nrows, ncols, figsize=figsize, tight_layout=True)
        axs=axs.flatten()
        [ax.axis('off') for ax in axs]
        # 

        pos = self.nodes_position
        roles = self.nodes_role
        nodes_label = self.nodes_label
        edge_label = self.edge_label
        for i, (path, info) in enumerate(paths.items()):
            ax = axs[i]

            if show_full_dag:
                self.plot(ax=ax, edge_directed_color='lightgray', edge_bidirected_color='lightgray')

            G2 = scm.DAG(path, nodes_role=roles, nodes_position=pos)
            G2.plot(ax=ax, edge_directed_linewidth=3, edge_bidirected_linewidth=3, node_label_or_name=None)
            adj = info['adj_set']
            adj = "None" if adj is None else ", ".join(adj)
            title = rf"Path is \textbf{{{'open' if info['open'] else 'closed'}}}; Adjustment set: {adj}"
            ax.set_title(title, loc='left', fontsize=title_fontsize)
            ax.axis('on')
            plt.tight_layout()
        return axs

    def __plot_label_adj__(self, node_label_adj, nodes_label):
        if isinstance(node_label_adj, dict):
            adj = {node:node_label_adj.get(node, 0) for node in self.get_nodes(exclude_latent=False)}
            
        elif isinstance(node_label_adj, (float, int)):
            adj = {n:node_label_adj for n in self.get_nodes(exclude_latent=False)}

        # same for if labels are used
        for node, label in nodes_label.items():
            adj[label] = adj[node]
        
        return adj

    def __plot_edge_margin__(self, edge_margin):
        if isinstance(edge_margin, dict):
            edge_margin = {(u, v):edge_margin.get((u, v), 20) for u, v in self.directed + self.bidirected}
            
        elif isinstance(edge_margin, (float, int)):
            edge_margin = {(u, v):edge_margin for u, v in self.directed + self.bidirected}

        return edge_margin

    # computations
    # ------------
    # dagitty (R dependencies)
    def local_independencies(self, data=None):
        """
        Given a networkx.DiGraph, return implied conditional independencies using dagitty (via R).

        Parameters:
            G (nx.DiGraph): Directed acyclic graph (must be a valid DAG)

        Returns:
            List[str]: Implied conditional independencies, e.g., "X _|_ Y | Z"
        """
        G = self.G

        data = data if data is not None else self.data
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
        exposure = exposure or self.nodes_role['Exposure']
        outcome = outcome or self.nodes_role['Outcome']

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
        exposure = exposure or self.nodes_role['Exposure']
        outcome = outcome or self.nodes_role['Outcome']

        assert exposure is not None, "Exposure must be provided."
        assert outcome is not None, "Outcome must be provided."

        adj = adj_set or NULL
        paths_info = dagitty.paths(self.__dagitty__, exposure, to=outcome, Z=adj, directed=directed)
        paths = list(paths_info.rx2['paths'])
        are_open = list(paths_info.rx2['open'])

        return {path:{'open':is_open, 'adj_set':adj_set} for path, is_open in zip(paths, are_open)}

    # dagitty (R dependencies)
    def equivalence_class():
        pass
        
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
        

