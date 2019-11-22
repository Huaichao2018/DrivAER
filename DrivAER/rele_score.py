from .dca_drivaer import dca_drivaer
import tensorflow
import scanpy as sc
import pandas as pd
import os
import anndata as ad
import numpy as np
from sklearn.ensemble import RandomForestRegressor as RFR
from sklearn.ensemble import RandomForestClassifier as RFC
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
import numbers


path = os.path.dirname(os.path.abspath(__file__))

def calc_relevance(count, pheno, tf_targets, min_targets,
                   ae_type="nb-conddisp", epochs=3, early_stop=3,
                   hidden_size=(8, 2, 8), verbose=False):

    sc.pp.filter_genes(count, min_counts=1)
    gene = count.var_names.tolist()
    # Restrict to expressed target genes
    tf_targets = tf_targets.map(lambda x: sorted(list(set(x) & set(gene))))
    # Restrict to TFs with at least min_targets genes
    targets =  tf_targets[tf_targets.map(lambda x: len(x) >= min_targets)]

    my_counter = [0]

    def fun_dca(v):
        my_counter[0] += 1
        print(f'{my_counter[0]} / {len(targets)}')

        tmp = count.copy()
        tmp = ad.AnnData(tmp.X + 1)
        sc.pp.normalize_per_cell(tmp)
        size_factors = tmp.obs.n_counts/np.median(tmp.obs.n_counts)

        tmp = count[:,v]
        tmp = ad.AnnData(tmp.X + 1)
        tmp.obs["size_factors"]=size_factors

        ret = dca_drivaer(tmp, mode='latent',ae_type=ae_type,epochs=epochs,
        early_stop=early_stop,hidden_size=hidden_size,verbose=verbose,copy=True)
        return(ret.obsm["X_dca"])

    embed = targets.map(fun_dca)

    # Random forest
    def fun_rfr(x):
        clf = RFR(n_estimators=500, oob_score = True)
        rf_fit = clf.fit(X = x, y= pheno)
        return rf_fit.oob_score_

    def fun_rfc(x):
        clf = RFC(n_estimators=500, oob_score = True)
        rf_fit = clf.fit(X = x, y= pd.factorize(pheno)[0])
        return rf_fit.oob_score_

    if isinstance(pheno[0], numbers.Number):
        rele_score = embed.map(fun_rfr)
    else:
        rele_score = embed.map(fun_rfc)
        
    return embed,rele_score