import os 
import numpy as np 
import tensorflow as tf
import tensorflow_hub as hub
import glob
import seqnn
import json

########################################################################################
# CREME model
########################################################################################


class ModelBase():
    def __init__(self):
        raise NotImplementedError()

    def predict(self, x):
        raise NotImplementedError()

########################################################################################
# Borzoi model
########################################################################################




class Borzoi(ModelBase):
    """
    Wrapper class for Borzoi.
    inputs:
        head : str
            Borzoi head to get predictions --> head or mouse.
        track_index : int
            Enformer index of prediciton track for a given head.
    """
    def __init__(self, model_path, track_index, aggregate, bin_index=None, params_file='../data/borzoi_params_pred.json'):

        # Read model parameters
        with open(params_file) as params_open:
            params = json.load(params_open)
            params_model = params['model']
            params_model['norm_type'] = 'batch' # makes compatible with 2.11 tf and doesn't change output
        self.seq_length = params_model['seq_length']
        self.models = []
        self.track_index = track_index
        if type(self.track_index)==int:
            self.track_index = [self.track_index]
        self.aggregate = aggregate
        self.bin_index = bin_index
        if type(self.bin_index)==int:
            self.bin_index = [self.bin_index]

        print('Adding models:')
        print(glob.glob(model_path))
        for one_model_path in glob.glob(model_path):

            seqnn_model = seqnn.SeqNN(params_model)
            seqnn_model.restore(one_model_path, 0)
            self.models.append(seqnn_model)


    def predict(self, x):
        """Get full predictions from borzoi in batches."""

        # check to make sure shape is correct
        if len(x.shape) == 2:
            x = x[np.newaxis]
        # get predictions
        preds = []
        for j, m in enumerate(self.models):
            preds.append(m(x)[:, None, ...].astype("float16"))
        preds = np.concatenate(preds, axis=1)
        if self.bin_index:
            preds = preds[:,:,self.bin_index,:]
        if self.aggregate:
            preds = preds.mean(axis=1)
        if self.track_index:

            preds = preds[..., self.track_index]


        return preds






########################################################################################
# Enformer model
########################################################################################


class Enformer(ModelBase):
    """ 
    Wrapper class for Enformer. 
    inputs:
        head : str 
            Enformer head to get predictions --> head or mouse.
        track_index : int
            Enformer index of prediciton track for a given head.
    """
    def __init__(self, track_index=None, head='human'):

        # path to enformer on tensorflow-hub
        tfhub_url = 'https://tfhub.dev/deepmind/enformer/1'
        os.environ['TFHUB_CACHE_DIR'] = '.'
        self.model = hub.load(tfhub_url).model
        self.head = head
        self.track_index = track_index
        self.seq_length = 196608
        self.pseudo_pad = 196608



    def predict(self, x):
        """Get full predictions from enformer in batches."""

        # check to make sure shape is correct
        if len(x.shape) == 2:
            x = x[np.newaxis]

        # get predictions
        if x.shape[1] == self.pseudo_pad:
            x = np.pad(x, ((0, 0), (self.pseudo_pad // 2, self.pseudo_pad // 2), (0, 0)), 'constant')
        preds = self.model.predict_on_batch(x)[self.head].numpy()
        if self.track_index:
            preds = preds[..., self.track_index]
        return preds


    @tf.function
    def contribution_input_grad(self, x, target_mask, head='human', mult_by_input=True):
        """Calculate input gradients"""

        # check to make sure shape is correct
        if len(x.shape) == 2:
            x = x[np.newaxis]

        # calculate saliency maps
        target_mask_mass = tf.reduce_sum(target_mask)
        with tf.GradientTape() as tape:
            tape.watch(x)
            prediction = tf.reduce_sum(
                target_mask[tf.newaxis] * self.model.predict_on_batch(x)[head]
                ) / target_mask_mass
        input_grad = tape.gradient(prediction, x)

        # process saliency maps
        if mult_by_input:
            input_grad *= x
            input_grad = tf.squeeze(input_grad, axis=0)
            return tf.reduce_sum(input_grad, axis=-1)
        else:
            return input_grad



########################################################################################
# Template for custom model 
########################################################################################

# class CustomModel(ModelBase):
#   def __init__(self, model):
#       self.model = model
#   def predict(self, x, class_index, batch_size=64):
#       # insert custom code here to get model predictions
#       # preds = model.predict(x, batch_size=64)
#       # preds = preds[:, class_index]
#       return preds



########################################################################################
# useful functions
########################################################################################


def batch_np(whole_dataset, batch_size):
    """Batch generator for dataset."""
    for i in range(0, whole_dataset.shape[0], batch_size):
        yield whole_dataset[i:i + batch_size]

