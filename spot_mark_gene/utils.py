# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/02_utils.ipynb.

# %% auto 0
__all__ = ['remove_non_numeric_from_str', 'time_to_num_from_idx_to_time', 'make_qc_fig_filename']

# %% ../nbs/02_utils.ipynb 3
# NOTE: needed for python 3.10 forward compatibility with scanpy as 
# scanpy uses Iterable which is deprecated in 3.10
import collections.abc
#hyper needs the four following aliases to be done manually.
collections.Iterable = collections.abc.Iterable
collections.Mapping = collections.abc.Mapping
collections.MutableSet = collections.abc.MutableSet
collections.MutableMapping = collections.abc.MutableMapping

# %% ../nbs/02_utils.ipynb 4
from spot_mark_gene.types import (
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

# %% ../nbs/02_utils.ipynb 5
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

# %% ../nbs/02_utils.ipynb 6
def remove_non_numeric_from_str(s:str) -> str:
    '''
    Removes non-numbers from string.
    Utility function used in `time_to_num_from_idx_to_time`.
    '''
    return str(filter(str.isdigit, s))

def time_to_num_from_idx_to_time(idx_to_time:dict) -> dict:
    '''
    Examples:
        idx_to_time = {
            '0': '12hr', 
            '1': '18hr', 
            '2': '24hr'
        }

        gets converted into

        time_to_num = {
            '12hr': '12', 
            '18hr': '18', 
            '24hr': '24'
        }
    '''
    time_to_num = {
        v: remove_non_numeric_from_str(v)
        for v in idx_to_time.values()
    }
    return time_to_num

def make_qc_fig_filename(
    save_dir:str, 
    study_name:str,
    x:str, y:str, postfix:str=''
) -> str:     
    '''
    Utility function used in make_qc_figs to name files.
    Output files are in the form of:
    `{save_dir}/.QC_{study_name}_{x}_{y}_{postfix}.png`
    '''
    if postfix:
        postfix = f'_{postfix}'
    return os.path.join(
         save_dir,
         f'.QC_{study_name}_{x}_{y}{postfix}.png' 
    )

