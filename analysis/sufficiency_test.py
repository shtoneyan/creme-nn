import glob
import pickle
import pandas as pd
import seaborn as sns
import numpy as np
import matplotlib.pyplot as plt
import pyranges as pr
import sys, os, h5py
import kipoiseq
from tqdm import tqdm
import json
sys.path.append('../creme')
import creme
import custom_model
import utils
import glob






def main():

    model_name = sys.argv[1]
    perturb_window = 5000
    num_shuffle = 10
    data_dir = '../data/'
    fasta_path = f'{data_dir}/GRCh38.primary_assembly.genome.fa'
    result_dir = utils.make_dir(f'../results/sufficiency_test')
    result_dir_model = utils.make_dir(f'{result_dir}/{model_name}/')
    print(f'USING model {model_name}')
    if model_name.lower() == 'enformer':
        track_index = [4824, 5110, 5111]
        model = custom_model.Enformer(track_index=track_index)
        target_df = pd.read_csv(f'{data_dir}/enformer_targets_human.txt', sep='\t')
        cell_lines = [utils.clean_cell_name(target_df.iloc[t]['description']) for t in track_index]


    else:
        print('Unkown model')
        sys.exit(1)


    
    conext_df = pd.concat([pd.read_csv(f'../results/context_dependence_test/{model_name}/{cell_line}_context.csv') for cell_line in cell_lines]).drop_duplicates('path')

    conext_df = conext_df.sample(frac = 1)
    # get coordinates of central tss
    tss_tile, cre_tiles = utils.set_tile_range(model.seq_length, perturb_window)
    tile_df = pd.DataFrame(cre_tiles).T
    tile_df['tss'] = tss_tile
    tile_df.to_csv(f'{result_dir_model}/tile_coordinates.csv')
    # set up sequence parser from fasta
    seq_parser = utils.SequenceParser(fasta_path)


    for i, row in tqdm(conext_df.iterrows(), total=len(conext_df)):
        seq_id = row['path'].split('/')[-1].split('.')[0]
        result_path = f'{result_dir_model}/{seq_id}.pickle'
        print(result_path)
        if not os.path.isfile(result_path):
            chrom, start, strand = seq_id.split('_')[1:]
            # get seq from reference genome and convert to one-hot
            x = seq_parser.extract_seq_centered(chrom, int(start), strand, model.seq_length, onehot=True)

            # perform CRE Necessity Test
            pred_wt, pred_mut_mean, pred_mut_std, pred_control_mean, pred_control_std = creme.sufficiency_test(model, x,
                                                                                                               tss_tile,
                                                                                                             cre_tiles,
                                                                                                             num_shuffle,
                                                                                                             mean=True)
            utils.save_pickle(result_path, {'wt': pred_wt, 'mut': pred_mut_mean, 'mut_std': pred_mut_std,
                                            'control':pred_control_mean, 'control_std':pred_control_std})

if __name__ == '__main__':
    main()


