# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/05_preprocessing.ipynb.

# %% auto 0
__all__ = ['prepare_h5ad_file', 'filter_pipeline', 'normalization_pipeline', 'embedding_pipeline']

# %% ../nbs/05_preprocessing.ipynb 3
# NOTE: needed for python 3.10 forward compatibility with scanpy as 
# scanpy uses Iterable which is deprecated in 3.10
import collections.abc
#hyper needs the four following aliases to be done manually.
collections.Iterable = collections.abc.Iterable
collections.Mapping = collections.abc.Mapping
collections.MutableSet = collections.abc.MutableSet
collections.MutableMapping = collections.abc.MutableMapping

# %% ../nbs/05_preprocessing.ipynb 4
from degex.types import (
    AnnData, AnnDatas, Graph, SeriesLike,
    VAR_HUMAN_TF, VAR_MOUSE_TF,
    VAR_HUMAN_ENSEMBLE_ID, VAR_MOUSE_ENSEMBLE_ID,
    LAYER_PRENORM, LAYER_DETECTED,
    LAYER_SCALED_NORMALIZED, EMB_MAGIC,
    EMB_PCA, EMB_PCA_HVG,
    EMB_PHATE, EMB_PHATE_HVG,
    CUTOFF_KIND, CUTOFF_SHORTHAND_TO_OBS_KEYS,
    CutoffSpecification, CutoffSpecifications,
    VAR_GENE_SYMBOL, VAR_GENE_IDS,
    OBS_DOUBLET_SCORES, OBS_PREDICTED_DOUBLETS,
    VAR_MITO
)

# %% ../nbs/05_preprocessing.ipynb 5
import os
import copy

from typing import TypeAlias, List, Sequence, Tuple

import anndata as ad
import numpy as np
import pandas as pd
import scanpy as sc
import scrublet as scr
import scipy
import graphtools as gt
import phate
import magic

# %% ../nbs/05_preprocessing.ipynb 6
from degex.adata import (
    add_gene_ids_to_adata,
    add_gene_symbols_to_adata,
    score_doublets, apply_filter_by_cutoffs,
    remove_mitochondrial_genes,
    add_gene_detection_layer,
    add_prenormalization_layer,
    sqrt_library_size_normalize,
    add_batch_mean_center_layer,
    score_genes_cell_cycle_with_batch_mean_center_data,
    select_hvg_per_batch,
    run_pca, run_pca_on_hvg,
    run_phate_on_hvg, run_phate_using_g, run_magic,
)

# %% ../nbs/05_preprocessing.ipynb 7
def prepare_h5ad_file(filename:str, plot:bool=False) -> AnnData:
    adata = sc.read_10x_h5(filename, gex_only = True)
    adata = add_gene_symbols_to_adata(adata)
    adata = add_gene_ids_to_adata(adata)
    adata = score_doublets(adata, plot)
    return adata


def filter_pipeline(
    adata:AnnData,
    cutoff_specs:CutoffSpecifications = [
        CutoffSpecification('total_counts', 500, 10000),
        CutoffSpecification('pct_counts_mito', None, 15),
        CutoffSpecification('pct_counts_ribo', None, 15),
        CutoffSpecification('doublet_scores', None, 0.4),
    ],
    min_cells:int=5
) -> AnnData:    
    adata = apply_filter_by_cutoffs(adata, cutoff_specs)
    adata = sc.pp.filter_genes(adata, min_cells=min_cells)
    adata = remove_mitochondrial_genes(adata)    
    return adata

def normalization_pipeline(
    adata:AnnData,
    s_genes:Sequence[str]=None,
    g2m_genes:Sequence[str]=None
) -> AnnData:
    adata = add_prenormalization_layer(adata)
    adata = add_gene_detection_layer(adata)
    adata = sqrt_library_size_normalize(adata)
    adata = add_batch_mean_center_layer(adata)
    if s_genes is not None and g2m_genes is not None:
        adata = score_genes_cell_cycle_with_batch_mean_center_data(
            adata, s_genes, g2m_genes
        )
    return adata

def embedding_pipeline(
    adata:AnnData,

    # PCA on adata.X
    pca_kwargs:dict=dict(n_components=100),
    plot_scree:bool=False,
    
    # PHATE on pca
    phate_kwargs=dict(t=70),
    g_kwargs=dict(knn=10),
    
    do_hvg:bool=True,

    # How to calc hvg
    hvg_kwargs:dict=dict(cutoff=None, percentile=90),

    # PCA on hvg
    hvg_pca_kwargs:dict=None,
    
    # PHATE on hvg
    hvg_phate_kwargs:dict=None,
    hvg_g_kwargs:dict=None,
    
    # MAGIC on g_hvg
    magic_knn_max:int=60
) -> Tuple[AnnData, Graph, Graph]:
    g, g_hvg = None, None

    # STEP 1: PCA on adata.X --> X_pca
    adata = run_pca(adata, pca_kwargs=pca_kwargs, plot_scree=plot_scree)
    
    # STEP 2: PHATE on X_pca --> X_phate
    adata, g = run_phate_using_g(adata, g, phate_kwargs, g_kwargs)
    
    if do_hvg:
        # STEP 3: setup HVG params
        if hvg_pca_kwargs is None:
            hvg_pca_kwargs = copy.deepcopy(pca_kwargs)

        if hvg_phate_kwargs is None:
            hvg_phate_kwargs = copy.deepcopy(phate_kwargs)

        if hvg_g_kwargs is None:
            hvg_g_kwargs = copy.deepcopy(g_kwargs)

        # STEP 4: calculate HVGs per batch
        adata = select_hvg_per_batch(adata, hvg_kwargs)

        # STEP 5: PCA on adata.X[:, HVGs] --> X_pca_hvg
        adata = run_pca_on_hvg(adata, hvg_pca_kwargs, plot_scree)

        # STEP 6: PHATE on X_pca_hvg --> X_phate_hvg
        adata, g_hvg = run_phate_on_hvg(adata, g_hvg, hvg_phate_kwargs, hvg_g_kwargs)

        # STEP 7: MAGIC on g_hvg --> X_magic
        adata = run_magic(adata, g_hvg, magic_knn_max)

    return adata, g, g_hvg
