# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/03_adata.ipynb.

# %% auto 0
__all__ = ['QC_VARS', 'PCA_KWARGS', 'PHATE_KWARGS', 'G_KWARGS', 'set_gene_symbol_as_var_names', 'set_var_names_as_gene_ids',
           'remove_mitochondrial_genes', 'score_doublets', 'add_gene_annotations', 'stack', 'stack_batchs',
           'var_starts_with_pattern', 'make_var_starts_with', 'calc_qc_stats', 'filter_by_cutoffs',
           'apply_filter_by_cutoffs', 'add_prenormalization_layer', 'add_gene_detection_layer',
           'sqrt_library_size_normalize', 'add_batch_mean_center_layer',
           'score_genes_cell_cycle_with_batch_mean_center_data', 'load_human_genes', 'select_hvg_per_batch',
           'add_tf_annotations_from_csv', 'add_human_tfs_from_csv', 'add_mouse_tfs_from_csv', 'zscore_markers_in_layer',
           'subset_markers', 'run_pca', 'run_pca_on_hvg', 'run_phate_using_g', 'run_phate_on_hvg', 'run_magic']

# %% ../nbs/03_adata.ipynb 3
# NOTE: needed for python 3.10 forward compatibility with scanpy as 
# scanpy uses Iterable which is deprecated in 3.10
import collections.abc
#hyper needs the four following aliases to be done manually.
collections.Iterable = collections.abc.Iterable
collections.Mapping = collections.abc.Mapping
collections.MutableSet = collections.abc.MutableSet
collections.MutableMapping = collections.abc.MutableMapping

# %% ../nbs/03_adata.ipynb 4
import os, copy

import numpy as np, pandas as pd, scipy
import phate, magic, graphtools as gt
import scprep, anndata as ad, scanpy as sc, scrublet as scr
from scipy.stats import zscore

from typing import TypeAlias, List, Sequence, Tuple, Optional, Dict

# %% ../nbs/03_adata.ipynb 5
from degex.types import (
    AnnData, AnnDatas, Graph, SeriesLike,
    CutoffSpec, CutoffSpecs, CUTOFF,
)
#| export
from degex.utils import (
    arr_toarray, adata_X_toarray, 
    time_to_num_from_idx_to_time
)

# %% ../nbs/03_adata.ipynb 6
from degex.static import (
    SEED,
    GENE_IDS, GENE_SYMBOL, HUMAN_GENE_SYMBOL, HIGHLY_VARIABLE,
    ENSEMBL, HUMAN_TF, MOUSE_TF, HUMAN_ENSEMBLE_ID, MOUSE_ENSEMBLE_ID,
    TOTAL_COUNTS, BATCH, MITO, RIBO, TIMEPOINT,
    DOUBLET_SCORES, PREDICTED_DOUBLETS,
    ADATA, PCA, PHATE,
    X_MAGIC, X_PCA, X_PCA_HVG, X_PHATE, X_PHATE_HVG,
    X_PRENORM, X_DETECTED, X_SCALED_NORMALIZED,
)

# %% ../nbs/03_adata.ipynb 8
def set_gene_symbol_as_var_names(adata: AnnData) -> AnnData:
    """
    Enfoces that `adata.var` names are unique and adds 
    `gene_symbol` to `adata.var`.
    
    Parameters
    ----------
    adata
        AnnData to process
        
    Returns
    -------
    adata
        for function chaining
    """
    adata.var_names_make_unique()
    if GENE_SYMBOL not in adata.var:
        adata.var[GENE_SYMBOL] = adata.var_names
    return adata

def set_var_names_as_gene_ids(adata: AnnData) -> AnnData:
    """
    Adds `gene_ids` to `adata.var`.
    
    Parameters
    ----------
    adata
        AnnData to process
        
    Returns
    -------
    adata
        for function chaining
    """
    adata.var_names = adata.var[GENE_IDS]
    return adata

def remove_mitochondrial_genes(adata: AnnData) -> AnnData:
    """
    Filters `adata` by colums not in `adata.var.mito`.
    
    Parameters
    ----------
    adata
        AnnData to process
        
    Returns
    -------
    adata
        for function chaining
    """
    adata = adata[:, ~(adata.var[MITO])]
    return adata

def score_doublets(adata: AnnData, plot: bool = False, **kwargs) -> AnnData:   
    f"""
    Adds `{DOUBLET_SCORES}` and `{PREDICTED_DOUBLETS}` to `adata.obs`.
    
    Parameters
    ----------
    adata
        AnnData to process. Note that `adata.X` gets passed 
        as `counts_matrix` to `scrublet.Scrublet(...)`.

    plot
        Whether or not to plot scrublet histogram.

    kwargs
        Other key-value arguments to passed to `scrublet.Scrublet()`.
    
    Returns
    -------
    adata
        for function chaining
    """
    assert 'counts_matrix' not in kwargs
    scrub = scr.Scrublet(counts_matrix=adata.X, **kwargs)
    adata.obs[DOUBLET_SCORES], adata.obs[PREDICTED_DOUBLETS] =\
        scrub.scrub_doublets()
    if plot:
        scrub.plot_histogram()
    return adata

# %% ../nbs/03_adata.ipynb 10
def add_gene_annotations(
    adata: AnnData,
    annotation_file: str
) -> AnnData:
    """
    Reads CSV and adds Ensembl information to 
    `adata.var.index`
    
    Parameters
    ----------
    adata
        AnnData to process

    annotation_file
        full path to csv file. Assumed to have a column
        called `Ensembl`.
        
    Returns
    -------
    adata
        for function chaining

    Notes
    -----
    Assumes that `annotation_file` has a column `'Ensembl'` in it.
    """
    # Load gene annotation information (extracted from bioconductor)    
    gene_annotation = pd.read_csv(
        annotation_file, index_col=None, header=0
    ).astype(str)

    assert hasattr(gene_annotation, ENSEMBL.capitalize())
    gene_annotation.index = list(gene_annotation.Ensembl)

    # Add to AnnData object
    adata.var = pd.concat(
        [adata.var, gene_annotation], axis=1, join='inner'
    )
    adata.var.index = list(adata.var[GENE_SYMBOL])
    # Enforce uniqueness
    adata.var_names_make_unique()
    return adata


# %% ../nbs/03_adata.ipynb 12
def stack(
    *adatas: AnnDatas,
    key: str = '_idx',    
    replace: Optional[Dict[str,str]] = None,
    replace_key: Optional[str] = None,
    print_counts: bool = False
) -> AnnData:            
    adata = ad.concat([*adatas], index_unique="_", merge="same", join='outer')

    adata.obs[key] = adata.obs.index.astype(str).str[-1]
    if replace is not None:
        rename_key = key if replace_key is None else replace_key
        adata.obs[rename_key] = adata.obs[key].replace(replace)

    if print_counts:
        print(adata.obs[key].value_counts())
    return adata

# %% ../nbs/03_adata.ipynb 13
def stack_batchs(
    *adatas: AnnDatas, 
    idx_to_time: dict,
    idx_to_batch: dict=None,
    batch_to_timepoint: dict = None,
    print_counts: bool = False
) -> AnnData:    
    """
    Concatenates the each one of the `adata`s in  
    `adatas` to a single `adata` instance.
    
    Parameters
    ----------
    *adatas
        AnnData to process. Note that `adata.X` gets passed 
        as `counts_matrix` to `scrublet.Scrublet(...)`.

    idx_to_time
        map of {int|str: str} for indicies to human friendly 
        time values.

    idx_to_batch
        map of {int|str: str} for indicies to batch

    batch_to_timepoint
        map of {str: int} to map each batch (from `idx_to_time` or `idx_to_batch`) to a timepoint

    print_counts
        Whether or not to print batched value counts.
    
    Returns
    -------
    adata
        Concatenated adata.
    
    Examples
    --------
    >>>    idx_to_time = {
            '0': '12hr', 
            '1': '18hr', 
            '2': '24hr'
        }

    >>>   time_to_num = {
            '12hr': '12', 
            '18hr': '18', 
            '24hr': '24'
        }
    """
    time_to_num = time_to_num_from_idx_to_time(idx_to_time)

    replace_batch = idx_to_time if idx_to_batch is None else idx_to_batch
    replace_times = time_to_num if batch_to_timepoint is None else batch_to_timepoint

    adata = stack(*adatas, BATCH, replace=replace_batch)
    adata.obs[TIMEPOINT] = adata.obs[BATCH].replace(replace_times)
    
    if print_counts:
        print(adata.obs[BATCH].value_counts())
    return adata

# %% ../nbs/03_adata.ipynb 15
QC_VARS = dict()
QC_VARS[MITO] = ('mt-', )
QC_VARS[RIBO] = ('rps', 'rpl')

def var_starts_with_pattern(name:str, patterns: Optional[Sequence[str]] = None) -> Tuple[str, tuple]:
    if patterns is None:
        patterns = (f'{name.lower()}_', )
    return name, patterns

def make_var_starts_with(var_starts_with: Optional[Dict[str, tuple]] = dict()):
    return {k: var_starts_with_pattern(v) for k, v in var_starts_with.items()}


def calc_qc_stats(
    adata: AnnData,
    qc_vars: Dict[str, tuple] = QC_VARS,
) -> AnnData:
    f"""
    Calculates {MITO} and {RIBO} qc metrics
    
    Parameters
    ----------
    adata
        AnnData to process

    annotation_file
        full path to csv file. Assumed to have a column
        called `Ensembl`.
        
    Returns
    -------
    adata
        for function chaining
    """
    qc_vars = make_var_starts_with(qc_vars)
    # Calculate QC stats
    for vname, patterns in qc_vars.items():
        adata.var[vname] = adata.var_names.str.startswith(patterns)

    sc.pp.calculate_qc_metrics(adata, qc_vars = list(qc_vars.keys()), inplace = True)

    adata.obs['log10_total_counts'] = np.log10(adata.obs[TOTAL_COUNTS])
    return adata

# %% ../nbs/03_adata.ipynb 16
def filter_by_cutoffs(
    adata: AnnData, 
    lower: float = None, 
    upper: float = None,
    obs_key: CUTOFF = TOTAL_COUNTS,
    print_counts: bool = False,      
) -> AnnData:
    """
    Uses `obs_key` to filter `adata` between `lower` and `upper` if provided e.g. 
    `lower < adata.obs[obs_key] < upper`
    
    Parameters
    ----------
    adata
        AnnData to process.

    lower
        Defaults to `None`. The value which `adata.obs[obs_key]` 
        should be greater than. If `None`, `lower` is not used.
    
    upper
        Defaults to `None`. The value which `adata.obs[obs_key]` 
        should be less than. If `None`, `upper` is not used.

    obs_key
        Which observation to test against.
        One of `'total_counts'`, `'pct_counts_mito'`, 
        `'pct_counts_ribo'`, or `'doublet_score'`. Defaults
        to `'total_counts'`. 

    print_counts
        Whether or not to print counts.
    
    Returns
    -------
    adata
        for function chaining
    """
    assert obs_key is not None    
    if lower is not None:
        adata = adata[adata.obs[obs_key] > lower]

    if upper is not None:
        adata = adata[adata.obs[obs_key] < upper]

    if print_counts:
        print(adata.obs.batch.value_counts())
    return adata


def apply_filter_by_cutoffs(
    adata: AnnData, 
    cutoff_specs: CutoffSpecs,
    print_counts: bool = False   
) -> AnnData:
    """
    Uses `obs_key` to filter `adata` between `lower` and `upper` if provided e.g. 
    `lower < adata.obs[obs_key] < upper`
    
    Parameters
    ----------
    adata
        AnnData to process.

    cutoff_specs
        Specifications in the form of `(obs_key, lower, upper)`
        to be used to `filter_by_cutoffs`.

    print_counts
        Whether or not to print counts.
    
    Returns
    -------
    adata
        for function chaining

    See also
    --------
    filter_by_cutoffs: singular instance of filtering.
    """
    for spec in cutoff_specs:
        adata = filter_by_cutoffs(
            adata, spec.lower, spec.upper, 
            spec.obs_key, print_counts
        )
    return adata

# %% ../nbs/03_adata.ipynb 18
def add_prenormalization_layer(adata: AnnData) -> AnnData:
    f"""
    Stores `adata.X` to `layers[{X_PRENORM}]`
    
    Parameters
    ----------
    adata
        AnnData to process.
    
    Returns
    -------
    adata
        for function chaining
    """
    # Store unnormalised counts
    adata.layers[X_PRENORM] = adata.X
    return adata

def add_gene_detection_layer(adata: AnnData) -> AnnData:
    f"""
    Stores `adata.X > 0` to `layers[{X_DETECTED}]`
    
    Parameters
    ----------
    adata
        AnnData to process.
    
    Returns
    -------
    adata
        for function chaining
    """
    # Store unnormalised counts
    if X_PRENORM not in adata.layers:
        adata = add_prenormalization_layer(adata)

    # Add layer of gene detection
    adata.layers[X_DETECTED] = scipy.sparse.csr_matrix(
        pd.DataFrame(
        (arr_toarray(adata.layers[X_PRENORM]) > 0), 
        columns = adata.var.index, index=adata.obs.index
    ).replace({True: 1, False: 0}))
    return adata


def sqrt_library_size_normalize(adata: AnnData) -> AnnData:
    f"""
    Runs `sqrt(library_size_normalize(adata.X))` and stores
    it in `adata.X`.
    
    Parameters
    ----------
    adata
        AnnData to process.
    
    Returns
    -------
    adata
        for function chaining
    """
    # Normalise by library size and square-root transform
    adata = adata.copy()
    adata.X = scipy.sparse.csr_matrix(
        scprep.transform.sqrt(
            scprep.normalize.library_size_normalize(
                adata_X_toarray(adata)                
            )
        )
    )
    return adata

# %% ../nbs/03_adata.ipynb 19
def add_batch_mean_center_layer(adata: AnnData) -> AnnData:
    f"""
    Runs `batch_mean_center(adata.X)` and stores
    it in `adata.layers[{X_SCALED_NORMALIZED}]`.
    
    Parameters
    ----------
    adata
        AnnData to process.
    
    Returns
    -------
    adata
        for function chaining
    """
    # Batch mean center before cell cycle scoring
    adata.raw = adata
    adata.X = scipy.sparse.csr_matrix(
        scprep.normalize.batch_mean_center(        
            adata_X_toarray(adata),            
            sample_idx = adata.obs[BATCH]
        )
    )

    adata.layers[X_SCALED_NORMALIZED] = scipy.sparse.csr_matrix(adata.X)
    adata.X = adata.raw.X
    return adata

def score_genes_cell_cycle_with_batch_mean_center_data(
        adata: AnnData,
        s_genes:Sequence[str], 
        g2m_genes:Sequence[str],
) -> AnnData:
    f"""
    Uses `adata.layers[{X_SCALED_NORMALIZED}]` to run
    `sc.tl.score_genes_cell_cycle` and stores results in 
    `adata`.

    
    Parameters
    ----------
    adata
        AnnData to process.

    s_genes
        List of genes associated with S phase.

    g2m_genes
        List of genes associated with G2M phase.
    
    Returns
    -------
    adata
        for function chaining
    """
    sdata = adata.copy()
    sdata.X = np.array(adata.layers[X_SCALED_NORMALIZED].todense())        
    sdata.raw = adata
    # Get normalised counts back instead of mean centered values as pca will mean center
    sc.tl.score_genes_cell_cycle(sdata, s_genes=s_genes, g2m_genes=g2m_genes)

    adata.obs = adata.obs.join(sdata.obs.S_score)
    adata.obs = adata.obs.join(sdata.obs.G2M_score)
    adata.obs = adata.obs.join(sdata.obs.phase)

    return adata

def load_human_genes(
    adata: AnnData, filename: str
) -> List[str]:
    f'''
    Reads the file uses `adata` to confirm validity
    
    Parameters
    ----------
    adata
        AnnData to process.

    filename
        Plaintext file with one column and a single gene
        on each row with in its HumanGeneSymbol form.
    
    Returns
    -------
    adata
        for function chaining

    Notes
    -----
    Assumes `adata.var` has `{HUMAN_GENE_SYMBOL}`. 
    '''
    assert hasattr(adata.var, HUMAN_GENE_SYMBOL)

    with open(filename, 'r') as f:
        genes = f.readlines()
        genes = [gene.strip() for gene in genes]
        genes = adata.var.index[adata.var[HUMAN_GENE_SYMBOL].isin(genes)]
        return genes
    


# %% ../nbs/03_adata.ipynb 21
def select_hvg_per_batch(
    adata: AnnData,
    hvg_kwargs: dict = dict(cutoff=None, percentile=90)
) -> AnnData:
    '''
    Calculates highly variable genes per batch in `adata`
    
    Parameters
    ----------
    adata
        AnnData to process.

    hvg_kwargs
        Options to be passed to `sc.select_highly_variable_genes`.
    
    Returns
    -------
    adata
        for function chaining
    '''
    # Select highly variable genes from any batch
    hvg_all = []
    for batch in adata.obs[BATCH].unique():
        normalised, hgv_vars = scprep.select.highly_variable_genes(
            adata_X_toarray(adata[adata.obs[BATCH] == batch]),
            adata[adata.obs[BATCH] == batch].var.index, 
            **hvg_kwargs
        )
        hvg_all.extend(hgv_vars)
        adata.var[f'{HIGHLY_VARIABLE}_{batch}'] = adata.var.index.isin(hgv_vars)
        del normalised
        print(f"Unique HVGs after {batch} {len(np.unique(np.array(hvg_all)))}")
        
    adata.var[HIGHLY_VARIABLE] = adata.var.index.isin(hvg_all)
    return adata



# %% ../nbs/03_adata.ipynb 23
def add_tf_annotations_from_csv(
    adata: AnnData, filename: str,
    tf_key: str, ensemble_key: str,
    print_counts: bool = False
) -> AnnData:
    assert hasattr(adata.var, ensemble_key)
    df_tfs = pd.read_csv(filename, index_col=None, header=0).astype(str)
    
    adata.var[tf_key] = adata.var[ensemble_key]\
        .isin(df_tfs[ensemble_key])

    if print_counts:
        print(adata.var[tf_key].value_counts())
    return adata

def add_human_tfs_from_csv(
    adata: AnnData, filename:str,
    print_counts:bool=False
) -> AnnData:
    return add_tf_annotations_from_csv(
        adata, filename, HUMAN_TF,
        HUMAN_ENSEMBLE_ID, print_counts
    )

def add_mouse_tfs_from_csv(
    adata: AnnData, filename:str,
    print_counts:bool=False
) -> AnnData:    
    return add_tf_annotations_from_csv(
        adata, filename, MOUSE_TF,
        MOUSE_ENSEMBLE_ID, print_counts
    )



# %% ../nbs/03_adata.ipynb 25
def zscore_markers_in_layer(
    adata: AnnData,
    markers: List[str],
    obs_key: str = 'Markers_zscore',
    layer_key: str = X_MAGIC,    
) -> AnnData:    
    # Score cells based on select marker expression (sum of zscores of smoothed counts)
    col_subset = adata.var.index.isin(markers)
    df_markers = pd.DataFrame(
        arr_toarray(adata.layers[layer_key][:, col_subset]),        
        columns = adata.var.index[col_subset],
        index = adata.obs.index
    )
    df_markers.apply(zscore)
    adata.obs[obs_key] = df_markers.sum(axis=1)
    return adata

def subset_markers(
    adata: AnnData,
    obs_key: str = 'Markers_cell',
    score_key: str = 'Markers_zscore',
    lower: float = 2.2,
    upper: float = None,
    marker_name: str = 'marker',
    other_name: str = 'other'
) -> AnnData:
    u_cut = pd.Series(np.repeat(True, adata.obs.shape[0]))
    l_cut = pd.Series(np.repeat(True, adata.obs.shape[0]))
    if upper is not None:
        u_cut = (adata.obs[score_key] < upper)

    if lower is not None:
        l_cut = (lower < adata.obs[score_key])
    
    found = pd.Series(np.logical_and(u_cut.values, l_cut.values), index=adata.obs[score_key].index, name=obs_key)

    adata.obs[obs_key] = (found).replace({True: marker_name, False: other_name})
    return adata


# %% ../nbs/03_adata.ipynb 27
PCA_KWARGS: dict = dict(n_components=100)
PHATE_KWARGS: dict = dict(t=70)
G_KWARGS: dict = dict(knn=10)

# %% ../nbs/03_adata.ipynb 29
def run_pca(
    adata: AnnData,
    pca_kwargs: dict = PCA_KWARGS,
    plot_scree: bool = False,
    emb_key: str = X_PCA,
    col_subset: SeriesLike = None
) -> AnnData:
    # Compute PCs for initial cell graph
    pca_kwargs['return_singular_values'] = True
    pca_kwargs[SEED] = 3

    if col_subset is not None:        
        x = adata_X_toarray(adata[:, col_subset])
    else:
        x = adata_X_toarray(adata)        

    pcs, svs = scprep.reduce.pca(x, **pca_kwargs)
    adata.obsm[emb_key] = pcs
    if plot_scree:
        scprep.plot.scree_plot(svs, cumulative=False)
    return adata

def run_pca_on_hvg(
    adata: AnnData, pca_kwargs: dict = PCA_KWARGS, plot_scree: bool = False,
) -> AnnData:
    return run_pca(
        adata, pca_kwargs, plot_scree,
        X_PCA_HVG, adata.var[HIGHLY_VARIABLE]
    )

# %% ../nbs/03_adata.ipynb 31
def run_phate_using_g(
    adata: AnnData,
    g: Graph = None,
    phate_kwargs: dict = PHATE_KWARGS,
    g_kwargs: dict = G_KWARGS,
    emb_key: str = X_PHATE,
) -> Tuple[AnnData, Graph]:  
    # Make initial cellwise graph with HVGS (auto t=46)
    g_kwargs['random_state'] = 3
    g_kwargs['n_pca'] = None
    phate_kwargs['random_state'] = 3 

    if g is None:        
        pca_key = emb_key.replace(PHATE, PCA)        
        print((
            f'g is None. Will attempt to calculate with'
            f' {PCA.upper()} stored in {ADATA}.obsm[{pca_key}].'
        ))

        if pca_key not in adata.obsm:
            raise ValueError(f'{pca_key} not in {ADATA}.obsm')
        
        g = gt.Graph(adata.obsm[pca_key], **g_kwargs)

    phate_op = phate.PHATE(**phate_kwargs)
    data_phate = phate_op.fit_transform(g)
    adata.obsm[emb_key] = data_phate
    return adata, g

def run_phate_on_hvg(
    adata: AnnData,    
    g: Graph = None,
    phate_kwargs: dict = PHATE_KWARGS,
    g_kwargs: dict = G_KWARGS,    
    emb_key: str = X_PHATE_HVG,    
) -> Tuple[AnnData, Graph]:
    return run_phate_using_g(
        adata, g, phate_kwargs, g_kwargs, emb_key
    )


# %% ../nbs/03_adata.ipynb 33
def run_magic(
    adata: AnnData, g: Graph, knn_max: int = 60
) -> AnnData:
    G = copy.deepcopy(g)
    G.knn_max = knn_max
    G.data = adata.to_df()
    G.data_nu = adata.to_df()
    magic_op = magic.MAGIC().fit(adata.to_df(), graph=G)
    data_magic = magic_op.transform(genes='all_genes')
    adata.layers[X_MAGIC] = scipy.sparse.csr_matrix(data_magic)
    return adata
