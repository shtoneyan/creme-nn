import os
import numpy as np
from six.moves import cPickle
from creme import shuffle
import pandas as pd
import pyranges as pr
from tqdm import tqdm
from creme import utils, custom_model, creme 

########################################################################################
# parameters
########################################################################################

# enformer params
SEQUENCE_LEN = 393216
track_index = 5111
bin_index = 448
tfhub_url = 'https://tfhub.dev/deepmind/enformer/1'
fasta_path = 'hg19.fa'

# tile params
window = 5000
stride = 5000

# test params
num_shuffle = 10
num_rounds = 25
optimization = np.argmax             # argmin to search for enhancers and argmax to search for silencers
reduce_fun = utils.reduce_pred_index # function to reduce prediction of model to scalar

# file paths
enhancer_path = 'enhancers.csv'
cre_start = 'enhancer_start'        # name of column to get the start locations of the CRE positions
save_path = '../results/cre_multiplicity_test.pickle'


########################################################################################
# analysis
########################################################################################


# load TSS dataframe (with all TSS positions)
enhancers_df = pd.read_csv(enhancer_path)

# get coordinates of central tss 
tss_tile, other_tiles = utils.set_tile_range(SEQUENCE_LEN, window, stride)

# load enformer model 
model = custom_model.Enformer(tfhub_url, head='human', track_index=track_index)

# set up sequence parser from fasta 
seq_parser = utils.SequenceParser(fasta_path)

# loop through and predict TSS activity
pred_all = []
positions_all = []
for i, row in tqdm(enhancers_df.iterrows()):

    # get seequence from reference genome and convert to one-hot
    x = seq_parser.extract_seq_centered(row['chrom'], row['start'], SEQUENCE_LEN, onehot=True)

    # get coordinates for enhancer of interest
    cre_tile = [row[cre_start], row[cre_start]+window]

    # perform CRE Higher-order Interaction Test
    pred_wt, pred_per_round, max_positions  = creme.multiplicity_test(model, x, 
                                                                      tss_tile, 
                                                                      cre_tile,
                                                                      other_tiles, 
                                                                      num_shuffle, 
                                                                      num_rounds, 
                                                                      optimization,
                                                                      reduce_fun)

    # normalize predictions
    pred_norm = creme.fold_change_over_control(pred_wt, pred_per_round, bin_index)

    # store predictions
    pred_all.append(pred_norm)
    positions_all.append(max_positions)

# save results
with open(save_path, 'wb') as fout:
    cPickle.dump(np.array(pred_all), fout)
    cPickle.dump(np.array(positions_all), fout)





