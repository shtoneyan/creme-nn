import numpy as np
from . import shuffle 

def context_dependence_test(model, x, tile_pos, num_shuffle, mean=True):
    """
    This test places a sequence pattern bounded by start and end in shuffled 
    background contexts -- in line with a global importance analysis. 

    inputs:
        model: keras model 
        x: a single one-hot sequence shape (L, A)
        tile_pos: list with start index and end index of pattern along L
        num_shuffle: number of shuffles to apply
    """

    # get wild-type prediction
    pred_wt = model.predict(x[np.newaxis])

    # crop pattern of interest
    start, end = tile_pos
    x_pattern = x[start:end,:]

    # loop over shuffles
    pred_mut = []
    for n in range(num_shuffle):
        x_mut = shuffle.dinuc_shuffle(x)
        x_mut[start:end,:] = x_pattern
        pred_mut.append(model.predict(x_mut)[np.newaxis][0])
    pred_mut = np.concatenate(pred_mut, axis=0)

    if mean:
        return pred_wt[0], np.mean(pred_mut, axis=0)
    else:
        return pred_wt, pred_mut 


def context_swap_test(model, x_source, x_targets, tile_pos, mean=True):
    """
    This test places a source sequence pattern bounded by start and end in a 
    target sequence context -- in line with a global importance analysis. 

    inputs:
        model: keras model 
        x_source: a single one-hot sequence shape (L, A) from which a pattern will be taken
        tile_pos: list of start and end index of pattern along L
        x_targets: (N,L,A) multiple target sequences that will inherit a source pattern
    """
    if len(x_targets.shape) == 2:
        x_targets = np.expand_dims(x_targets, axis=0)

    # get wild-type prediction
    pred_wt = model.predict(x_source[np.newaxis])

    start, end = tile_pos

    # loop through target sequences
    pred_mut = []
    for x_target in x_targets:
        x_mut = np.copy(x_target)

        # place source pattern in target sequence
        x_mut[start:end,:] = x_source[start:end,:]

        # predict mutant sequence
        pred_mut.append(model.predict(x_mut[np.newaxis]))
    pred_mut = np.concatenate(pred_mut, axis=0)

    if mean:
        return pred_wt[0], np.mean(pred_mut, axis=0)
    else:
        return pred_wt, pred_mut 




def necessity_test(model, x, tiles, num_shuffle, mean=True):
    """
    This test shuffles a region of the sequence. 
    inputs:
        model: keras model 
        x: a single one-hot sequence shape (L, A) from which a pattern will be taken
        tiles: list of start and end positions for each shuffle
    """

    # get wild-type prediction
    pred_wt = model.predict(x[np.newaxis])

    # loop over shuffle posinate list
    pred_mut = []
    for pos in tiles:
        start, end = pos

        # loop over number of shuffles
        pred_shuffle = []
        for n in range(num_shuffle):
            x_mut = np.copy(x)

            # shuffle tile
            x_mut[start:end,:] = shuffle.dinuc_shuffle(x_mut[start:end,:])

            # predict mutated sequence
            pred_shuffle.append(model.predict(x_mut[np.newaxis])[0])
        pred_mut.append(pred_shuffle)
    pred_mut = np.array(pred_mut)

    if mean:
        return pred_wt[0], np.mean(pred_mut, axis=1)
    else:
        return pred_wt, pred_mut 



def sufficiency_test(model, x, tss_tile, tiles, num_shuffle, mean=True):
    """
    This test measures is a region of the sequence is sufficient for model predictions.
    inputs:
        model: keras model 
        x: a single one-hot sequence shape (L, A) from which a pattern will be taken
        shuffle_poss: list of start and end posinates for each shuffle position
    """

    # get wild-type prediction
    pred_wt = model.predict(x[np.newaxis])

    # loop over number of shuffles
    pred_mut = []
    pred_control = []
    for pos in tiles:
        start, end = pos

        pred_shuffle = []
        pred_shuffle2 = []
        for n in range(num_shuffle):
            x_mut = shuffle.dinuc_shuffle(x)
            
            # embed tss tile
            x_mut[tss_tile[0]:tss_tile[1],:] = x[tss_tile[0]:tss_tile[1],:] 

            # predict shuffled context with just TSS
            pred_shuffle2.append(model.predict(x_mut[np.newaxis])[0])

            # embed tile of interest in 
            x_mut[start:end,:] = x[start:end,:]

            # predict mutated sequence
            pred_shuffle.append(model.predict(x_mut[np.newaxis])[0])

        # store results
        pred_mut.append(pred_shuffle)
        pred_control.append(pred_shuffle2)

    pred_mut = np.array(pred_mut)
    pred_control = np.array(pred_control)

    if mean:
        return pred_wt[0], np.mean(pred_mut, axis=1), np.mean(pred_control, axis=1)
    else:
        return pred_wt, pred_mut, pred_control 



def distance_test(model, x, tile1, tile2, available_tiles, num_shuffle, mean=True):
    """
    This test measures is a region of the sequence is sufficient for model predictions.
    inputs:
        model: keras model 
        x: a single one-hot sequence shape (L, A) from which a pattern will be taken
        shuffle_poss: list of start and end posinates for each shuffle position
    """

    # crop pattern of interest
    x_tile1 = x[tile1[0]:tile1[1],:]  # fixed tile
    x_tile2 = x[tile2[0]:tile2[1],:]  # variable position tile

    # get sufficiency of tiles in original positions
    pred_control = []
    for n in range(num_shuffle):
        # shuffle sequence and place tiles in respective positions
        x_mut = shuffle.dinuc_shuffle(x)
        x_mut[tile1[0]:tile1[1],:] = x_tile1
        x_mut[tile2[0]:tile2[1],:] = x_tile2

        # predict mutant sequence
        pred_control.append(model.predict(x_mut[np.newaxis])[0])
    pred_control = np.array(pred_control)

    # loop over embedding tile2 in avilable position list
    pred_mut = []
    for pos in available_tiles:
        start, end = pos

        # loop over number of shuffles
        pred_shuffle = []
        for n in range(num_shuffle):

            # shuffle sequence
            x_mut = shuffle.dinuc_shuffle(x)

            # place tile 1 in original location
            x_mut[tile1[0]:tile1[1],:] = x_tile1

            # place tile 2 in new position
            x_mut[start:end,:] = x_tile2

            # predict mutant sequence
            pred_shuffle.append(model.predict(x_mut[np.newaxis])[0])
        pred_mut.append(pred_shuffle)
    pred_mut = np.array(pred_mut)

    if mean:
        return np.mean(pred_control, axis=0), np.mean(pred_mut, axis=1)
    else:
        return pred_control, pred_mut 




def higher_order_interaction_test(model, x, fixed_tiles, available_tiles, num_shuffle, num_rounds=10, optimization=np.argmax, reduce_fun=np.mean):
    """
    This test measures is a region of the sequence is sufficient for model predictions.
    inputs:
        model: keras model 
        x: a single one-hot sequence shape (L, A) from which a pattern will be taken
        shuffle_poss: list of start and end posinates for each shuffle position
    """

    # get wild-type prediction
    pred_wt = model.predict(x[np.newaxis])

    # loop through each greedy search round
    pred_per_round = []
    for i in range(num_rounds):

        # loop over shuffle posinate list
        pred_mut = []
        for pos in available_tiles:
            start, end = pos

            # loop over number of shuffles
            pred_shuffle = []
            for n in range(num_shuffle):
                x_mut = np.copy(x)

                # shuffle all tiles from previous round
                for pos2 in fixed_tiles:
                    start2, end2 = pos2
                    x_mut[start2:end2,:] = shuffle.dinuc_shuffle(x_mut[start2:end2,:])

                # shuffle candidate tile
                x_mut[start:end,:] = shuffle.dinuc_shuffle(x_mut[start:end,:])

                # get model prediction
                pred_shuffle.append(model.predict(x_mut[np.newaxis])[0])
            pred_mut.append(pred_shuffle)
        
        # average predictions acrros shuffles
        pred_mut = np.mean(np.array(pred_mut), axis=1)

        # reduce predictions to scalar
        pred_mut = reduce_fun(pred_mut)

        # find largest effect size
        max_index = optimization(pred_mut)
        pred_per_round.append(pred_mut[max_index])

        # add coordinates to fixed_tiles
        fixed_tiles.append(available_tiles[max_index])

        # update available positions 
        utils.remove_tss_tile(available_tiles, max_index)

    return pred_wt[0], pred_per_round, fixed_tiles 



def multiplicity_test(model, x, tile1, tile2, available_tiles, num_shuffle, num_rounds=10, optimization=np.argmax, reduce_fun=np.mean):
    """
    This test measures is a region of the sequence is sufficient for model predictions.
    inputs:
        model: keras model 
        x: a single one-hot sequence shape (L, A) from which a pattern will be taken
        shuffle_poss: list of start and end posinates for each shuffle position
    """


    # crop pattern of interest
    x_tile1 = x[tile1[0]:tile1[1],:]  # fixed tile
    x_tile2 = x[tile2[0]:tile2[1],:]  # variable position tile

    # get sufficiency of tiles in original positions
    pred_control = []
    for n in range(num_shuffle):
        # shuffle sequence and place tiles in respective positions
        x_mut = shuffle.dinuc_shuffle(x)
        x_mut[tile1[0]:tile1[1],:] = x_tile1
        x_mut[tile2[0]:tile2[1],:] = x_tile2

        # predict mutant sequence
        pred_control.append(model.predict(x_mut[np.newaxis])[0])
    pred_control = np.array(pred_control)

    # loop over multiplicity rounds (greedy search)
    pred_per_round = []
    max_positions = []
    for i in range(num_rounds):

        # loop over available positions
        pred_mut = []
        for pos in available_tiles:
            start, end = pos

            # loop over number of shuffles
            pred_shuffle = []
            for n in range(num_shuffle):

                # shuffle sequence
                x_mut = shuffle.dinuc_shuffle(x)

                # place tile 1 in original location
                x_mut[tile1[0]:tile1[1]] = x_tile1

                # place tile 2 in all positions found in previous rounds
                for max_pos in max_positions:
                    x_mut[max_pos[0]:max_pos[1]] = x_tile2

                # get model predictions
                pred_shuffle.append(model.predict(x_mut[np.newaxis])[0])
            pred_mut.append(pred_shuffle)

        # average predictions acrros shuffles
        pred_mut = np.mean(np.array(pred_mut), axis=1)

        # reduce predictions to scalar
        pred_mut = reduce_fun(pred_mut)

        # find largest effect size
        max_index = optimization(pred_mut)
        max_positions.append(available_tiles[max_index])
        pred_per_round.append(pred_mut[max_index])

        # update available positions 
        utils.remove_tss_tile(available_tiles, max_index)

    return pred_control, pred_per_round, max_positions 



########################################################################################
# Normalization functions
########################################################################################


def context_effect_on_tss(pred_wt, pred_mut, bin_index=488):
    """Normalization based on difference between the effect size of the mutation and wt divided by wt"""
    if (pred_mut.shape) == 1:
        return (pred_wt[bin_index] - pred_mut[bin_index]) / pred_wt[bin_index]
    else:
        return (pred_wt[bin_index] - pred_mut[:,bin_index])/pred_wt[bin_index]


def fold_change_over_control(pred_wt, pred_mut, bin_index=488):
    """Normalization based on difference between the effect size of the mutation and wt divided by wt"""
    if (pred_mut.shape) == 1:
        return pred_mut[bin_index] / pred_wt[bin_index]
    else:
        return pred_mut[:,bin_index] / pred_wt[bin_index]


def normalized_tile_effect(pred_wt, pred_mut, pred_control, bin_index=488):
    return (pred_mut[:,bin_index] - pred_control[:,bin_index])/pred_wt[bin_index]


def reduce_pred_index(pred, bin_index=448):
    return pred[:, bin_index]

