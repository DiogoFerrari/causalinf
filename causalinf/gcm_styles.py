from typing import Mapping, MutableMapping, Any, Union, Sequence
from types import MappingProxyType

# Type alias for clarity
GraphStyleDict = Mapping[str, Any]
GraphStyleInput = Union[str, GraphStyleDict]

def freeze(d):
    # """Recursively turn dictionaries into immutable MappingProxyTypes."""
    if isinstance(d, dict):
        return MappingProxyType({k: freeze(v) for k, v in d.items()})
    return d

def resolve_graph_style(graph_style: GraphStyleInput,
                        graph_styles: Mapping[str, GraphStyleDict]) -> GraphStyleDict:
    # """
    # Normalize a graph_style input (string or dict) into a style dict.

    # - If graph_style is a string, it must be a key in graph_styles.
    #   Returns the corresponding dict.
    # - If graph_style is a mapping/dict, it is returned as-is (for now).
    # - Otherwise raises TypeError.
    # """
    graph_style = graph_style or 'default'
    if isinstance(graph_style, str):
        try:
            return graph_styles[graph_style]
        except KeyError as exc:
            valid = ", ".join(sorted(graph_styles.keys()))
            raise ValueError(
                f"Unknown graph_style {graph_style!r}. "
                f"Valid names are: {valid}"
            ) from exc

    if isinstance(graph_style, Mapping):
        return graph_style

    raise TypeError(
        f"graph_style must be either a string key or a mapping, "
        f"got {type(graph_style).__name__}"
    )


STYLE_DEFAULT = freeze({
    "nodes" : {
        "Exposure": {
            "node_shape": "o",
            "node_size": 1000,
            "node_color": "lightgray",

            "node_border_color": "black",
            "node_border_width": 1,
            "node_border_style": "-",

            "node_label_color": "black",
            "node_label_fontweight": "normal",
            "node_label_fontsize"  : 12,
            "node_label_box" : False,
            "node_label_box_style": 'square',
            "node_label_box_margin": .5,

        },
        "Outcome": {
            "node_shape": "o",
            "node_size": 1000,
            "node_color": "gray",
            
            "node_border_color": "black",
            "node_border_width": 1,
            "node_border_style": "-",

            "node_label_color": "black",
            "node_label_fontweight": "normal",
            "node_label_fontsize"  : 12,
            "node_label_box" : False,
            "node_label_box_style": 'square',
            "node_label_box_margin": .5,
        },
        "Observed": {
            "node_shape": "o",
            "node_size": 1000,
            "node_color": "white",

            "node_border_color": "black",
            "node_border_width": 1,
            "node_border_style": "-",

            "node_label_color": "black",
            "node_label_fontweight": "normal",
            "node_label_fontsize"  : 12,
            "node_label_box" : False,
            "node_label_box_style": 'square',
            "node_label_box_margin": .5,
        },
        "Latent": {
            "node_shape": "o",
            "node_size": 1000,
            "node_color": "white",

            "node_border_color": "black",
            "node_border_width": 1,
            "node_border_style": "--",

            "node_label_color": "black",
            "node_label_fontweight": "normal",
            "node_label_fontsize"  : 12,
            "node_label_box" : False,
            "node_label_box_style": 'square',
            "node_label_box_margin": .5,
        }
    },
    # 
    "edges" : {
        # "edge_label": G.edge_label,
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
                             },
        "edge_label_alpha": {"directed": 1,
                             "bidirected": 1,
                             "undirected": 1
                             },
        "edge_label_size" : {"directed": 13,
                             "bidirected": 13,
                             "undirected": 13
                             },
        "edge_label_color" : {"directed": 'black',
                              "bidirected": 'black',
                              "undirected": 'black'
                              },
        "edge_label_rotate" : {"directed": True,
                               "bidirected": True,
                               "undirected": True
                               },
        "edge_label_position" : {"directed": .5,
                                 "bidirected": .5,
                                 "undirected": .5
                                 },

        "edge_label_color_border" : {"directed": None,
                                     "bidirected": None,
                                     "undirected": None
                                     },
        "edge_label_color_background" : {"directed": None,
                                         "bidirected": None,
                                         "undirected": None
                                         },

    }
})

STYLE_PEARL = freeze({ 
    "nodes" : {
        "Exposure": STYLE_DEFAULT['nodes']['Exposure'] | {
            "node_shape": ".",
            "node_size": 200,
            "node_color": "lightgray",
            "node_border_color": "black",
            "node_border_width": 1,
            "node_border_style": "-"
        },
        "Outcome": STYLE_DEFAULT['nodes']['Outcome'] | {
            "node_shape": ".",
            "node_size": 200,
            "node_color": "gray",
            "node_border_color": "black",
            "node_border_width": 1,
            "node_border_style": "-"
        },
        "Observed": STYLE_DEFAULT['nodes']['Observed'] | {
            "node_shape": ".",
            "node_size": 200,
            "node_color": "black",
            "node_border_color": "black",
            "node_border_width": 1,
            "node_border_style": "-"
        },
        "Latent":  STYLE_DEFAULT['nodes']['Latent'] | {
            "node_shape": ".",
            "node_size": 200,
            "node_color": "white",
            "node_border_color": "black",
            "node_border_width": 1,
            "node_border_style": "--"
        }
    },
    "edges" : STYLE_DEFAULT['edges']
})

STYLE_RECTANGLE = freeze({
    "nodes" : {
        "Exposure": STYLE_DEFAULT['nodes']['Exposure'] | {
            "node_shape": "",
            "node_size": 1000,
            "node_color": "lightgray",
            "node_border_color": "black",
            "node_border_width": 1,
            "node_border_style": "-",
            "node_label_box" : True,
        },
        "Outcome": STYLE_DEFAULT['nodes']['Outcome'] | {
            "node_shape": "",
            "node_size": 1000,
            "node_color": "gray",
            "node_border_color": "black",
            "node_border_width": 1,
            "node_border_style": "-",
            "node_label_box" : True,
        },
        "Observed": STYLE_DEFAULT['nodes']['Observed'] | {
            "node_shape": "",
            "node_size": 1000,
            "node_color": "white",
            "node_border_color": "black",
            "node_border_width": 1,
            "node_border_style": "-",
            "node_label_box" : True,
        },
        "Latent":  STYLE_DEFAULT['nodes']['Latent'] | {
            "node_shape": "",
            "node_size": 1000,
            "node_color": "white",
            "node_border_color": "black",
            "node_border_width": 1,
            "node_border_style": "--",
            "node_label_box" : True,
        }
    },
    "edges" : STYLE_DEFAULT['edges']
})

GRAPH_STYLES = freeze({
    'default'  : STYLE_DEFAULT,
    'rectangle': STYLE_RECTANGLE,
    'pearl'    : STYLE_PEARL
})

