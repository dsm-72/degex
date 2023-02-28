# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/01_types.ipynb.

# %% auto 0
__all__ = ['AnnData', 'AnnDatas', 'Graph', 'SeriesLike', 'VAR_GENE_SYMBOL', 'VAR_GENE_IDS', 'VAR_MITO', 'VAR_RIBO',
           'VAR_HIGHLY_VARIABLE', 'OBS_BATCH', 'OBS_TIMEPOINT', 'OBS_TOTAL_COUNTS', 'OBS_DOUBLET_SCORES',
           'OBS_PREDICTED_DOUBLETS', 'VAR_HUMAN_TF', 'VAR_MOUSE_TF', 'VAR_HUMAN_GENE_SYMBOL', 'VAR_HUMAN_ENSEMBLE_ID',
           'VAR_MOUSE_ENSEMBLE_ID', 'LAYER_PRENORM', 'LAYER_DETECTED', 'LAYER_SCALED_NORMALIZED', 'EMB_MAGIC',
           'EMB_PCA', 'EMB_PCA_HVG', 'EMB_PHATE', 'EMB_PHATE_HVG', 'CUTOFF_KIND', 'CUTOFF_SHORTHAND_TO_OBS_KEYS',
           'CutoffSpecifications', 'str_to_cutoff_kind', 'CutoffSpecification']

# %% ../nbs/01_types.ipynb 3
# NOTE: needed for python 3.10 forward compatibility with scanpy as 
# scanpy uses Iterable which is deprecated in 3.10
import collections.abc
#hyper needs the four following aliases to be done manually.
collections.Iterable = collections.abc.Iterable
collections.Mapping = collections.abc.Mapping
collections.MutableSet = collections.abc.MutableSet
collections.MutableMapping = collections.abc.MutableMapping

# %% ../nbs/01_types.ipynb 4
import anndata as ad
import graphtools as gt

from typing import (
    TypeAlias, List, 
    Sequence, Literal,
    Tuple, NamedTuple, 
    Union, get_args
)

# Type Alias for anndata.AnnData
AnnData: TypeAlias = ad.AnnData

# Type Alias for a list of anndata.AnnData objects
AnnDatas: TypeAlias = List[AnnData]

# Type Alias for graphtools.Graph
Graph: TypeAlias = gt.Graph

# Type Alias for series like data
from pandas import Series
from numpy import ndarray
SeriesLike: TypeAlias = Union[Series, list, ndarray]


# Type Alias for adata.var field
VAR_GENE_SYMBOL: TypeAlias = Literal['gene_symbol']

# Type Alias for adata.var field
VAR_GENE_IDS: TypeAlias = Literal['gene_ids']

# Type Alias for adata.var field
VAR_MITO: TypeAlias = Literal['mito']

# Type Alias for adata.var field
VAR_RIBO: TypeAlias = Literal['ribo']

# Type Alias for adata.var field
VAR_HIGHLY_VARIABLE: TypeAlias = Literal['ribo']

# Type Alias for adata.obs field
OBS_BATCH: TypeAlias = Literal['batch']

# Type Alias for adata.obs field
OBS_TIMEPOINT: TypeAlias = Literal['timepoint']

# Type Alias for adata.obs field
OBS_TOTAL_COUNTS: TypeAlias = Literal['total_counts']

# Type Alias for adata.obs field
OBS_DOUBLET_SCORES: TypeAlias = Literal['doublet_scores']

# Type Alias for adata.obs field
OBS_PREDICTED_DOUBLETS: TypeAlias = Literal['predicted_doublets']

# Human Transcription Factor key in adata.var
VAR_HUMAN_TF: TypeAlias = Literal['HumanTFs']

# Mouse Transcription Factor key in adata.var
VAR_MOUSE_TF: TypeAlias = Literal['MouseTFs']

# Human Gene Symbol key in adata.var
VAR_HUMAN_GENE_SYMBOL: TypeAlias = Literal['HumanGeneSymbol']

# Human Ensemble ID key in adata.var
VAR_HUMAN_ENSEMBLE_ID: TypeAlias = Literal['HumanEnsemblID']

# Mouse Ensemble ID key in adata.var
VAR_MOUSE_ENSEMBLE_ID: TypeAlias = Literal['MouseEnsemblID']

# Layer storing prenormalized counts in adata.layers
LAYER_PRENORM: TypeAlias = Literal['X_prenorm']

# Layer storing values where prenormalized counts is at least 0 in adata.layers
LAYER_DETECTED: TypeAlias = Literal['X_detected']

# Layer storing counts normalized
LAYER_SCALED_NORMALIZED: TypeAlias = Literal['X_scaled_normalised']

# Layer storing MAGIC embedding in adata.obsm
EMB_MAGIC:TypeAlias = Literal['X_magic']

# Layer storing PCA embedding in adata.obsm
EMB_PCA: TypeAlias = Literal['X_pca']

# Layer storing PCA embedding just on HVGs in adata.obsm
EMB_PCA_HVG: TypeAlias = Literal['X_pca_hvg']

# Layer storing PHATE embedding just in adata.obsm
EMB_PHATE: TypeAlias = Literal['X_phate']

# Layer storing PHATE embedding just on HVGs in adata.obsm
EMB_PHATE_HVG: TypeAlias = Literal['X_phate_hvg']

# Types of cutoffs that can be used in our cutoff function
CUTOFF_KIND = Literal[
    'total_counts', 'pct_counts_mito', 
    'pct_counts_ribo', 'doublet_score'
]

CUTOFF_SHORTHAND_TO_OBS_KEYS = {
    'default': 'total_counts', # 500 < obs < 10000
    'mito': 'pct_counts_mito', # None < obs < 15
    'ribo': 'pct_counts_ribo', # None < obs < 15
    'doublet': 'doublet_score', # None < obs < 0.4
}


# %% ../nbs/01_types.ipynb 5
from dataclasses import dataclass

def str_to_cutoff_kind(s:str) -> CUTOFF_KIND:
    return CUTOFF_SHORTHAND_TO_OBS_KEYS.get(s, 'total_counts')
    
@dataclass
class CutoffSpecification:
    obs_key: CUTOFF_KIND
    lower: float = None
    upper: float = None    

    def __init__(
        self, 
        obs_key: CUTOFF_KIND, 
        lower: float = None, 
        upper: float = None
    ):
        if obs_key not in get_args(CUTOFF_KIND):
            raise ValueError(
                f'obs_key = {obs_key} is not in {get_args(CUTOFF_KIND)}'
            )
        self.obs_key = obs_key
        self.lower = lower
        self.upper = upper

    def is_valid(self) -> bool:
        return self.obs_key is CUTOFF_KIND
    
# Type Alias for a list of CutoffSpecification
CutoffSpecifications: TypeAlias = List[CutoffSpecification]
