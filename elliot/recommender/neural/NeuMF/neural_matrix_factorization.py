"""
Module description:

"""


__version__ = '0.1'
__author__ = 'Vito Walter Anelli, Claudio Pomo'
__email__ = 'vitowalter.anelli@poliba.it, claudio.pomo@poliba.it'

import time
import numpy as np
import pickle
from ast import literal_eval as make_tuple
from tqdm import tqdm

from dataset.samplers import pointwise_pos_neg_sampler as pws
from evaluation.evaluator import Evaluator
from recommender.neural.NeuMF.neural_matrix_factorization_model import NeuralMatrixFactorizationModel
from recommender.recommender_utils_mixin import RecMixin
from utils.folder import build_model_folder
from utils.write import store_recommendation

from recommender.base_recommender_model import BaseRecommenderModel

np.random.seed(42)


class NeuralMatrixFactorization(RecMixin, BaseRecommenderModel):

    def __init__(self, data, config, params, *args, **kwargs):
        super().__init__(data, config, params, *args, **kwargs)

        self._num_items = self._data.num_items
        self._num_users = self._data.num_users
        self._random = np.random
        self._sample_negative_items_empirically = True

        self._sampler = pws.Sampler(self._data.i_train_dict)

        self._learning_rate = self._params.lr
        self._mf_factors = self._params.mf_factors
        self._mlp_factors = self._params.mlp_factors
        self._mlp_hidden_size = list(make_tuple(self._params.mlp_hidden_size))
        self._prob_keep_dropout = self._params.prob_keep_dropout
        self._is_mf_train = self._params.is_mf_train
        self._is_mlp_train = self._params.is_mlp_train

        if self._batch_size < 1:
            self._batch_size = self._data.transactions

        self._ratings = self._data.train_dict
        self._sp_i_train = self._data.sp_i_train
        self._i_items_set = list(range(self._num_items))
        # self._i_zeros = [list(items_set-set(user_train)) for user_train in self._sp_i_train.tolil().rows]
        self._model = NeuralMatrixFactorizationModel(self._num_users, self._num_items, self._mf_factors,
                                                     self._mlp_factors, self._mlp_hidden_size,
                                                     self._prob_keep_dropout, self._is_mf_train, self._is_mlp_train,
                                                     self._learning_rate)

        self._iteration = 0

        self.evaluator = Evaluator(self._data, self._params)

        self._params.name = self.name

        build_model_folder(self._config.path_output_rec_weight, self.name)
        self._saving_filepath = f'{self._config.path_output_rec_weight}{self.name}/best-weights-{self.name}'

    @property
    def name(self):
        return "NeuMF"\
               + "-e:" + str(self._epochs) \
               + "-mffactors:" + str(self._mf_factors) \
               + "-mlpfactors:" + str(self._mlp_factors) \
               + "-mlpunits:" + str(self._params.mlp_hidden_size).replace(",","-") \
               + "-droppk:" + str(self._prob_keep_dropout) \
               + "-mftrain:" + str(self._is_mf_train)\
               + "-mlptrain:" + str(self._is_mlp_train)

    def predict(self, u: int, i: int):
        pass

    def train(self):

        best_metric_value = 0
        self._update_count = 0

        for it in range(self._epochs):
            self.restore_weights(it)
            loss = 0
            steps = 0
            with tqdm(total=int(self._data.transactions // self._batch_size), disable=not self._verbose) as t:
                for batch in self._sampler.step(self._data.transactions, self._batch_size):
                    steps += 1
                    loss += self._model.train_step(batch)
                    t.set_postfix({'loss': f'{loss.numpy() / steps:.5f}'})
                    t.update()
                    self._update_count += 1

            if not (it + 1) % self._validation_rate:
                recs = self.get_recommendations(self.evaluator.get_needed_recommendations())
                result_dict = self.evaluator.eval(recs)
                self._results.append(result_dict)

                print(f'Epoch {(it + 1)}/{self._epochs} loss {loss/steps:.5f}')

                if self._results[-1][self._validation_k]["val_results"][self._validation_metric] > best_metric_value:
                    print("******************************************")
                    best_metric_value = self._results[-1][self._validation_k]["val_results"][self._validation_metric]
                    if self._save_weights:
                        self._model.save_weights(self._saving_filepath)
                    if self._save_recs:
                        store_recommendation(recs, self._config.path_output_rec_result + f"{self.name}-it:{it + 1}.tsv")

    def get_recommendations(self, k: int = 100):
        predictions_top_k = {}
        for index, offset in enumerate(range(0, self._num_users, self._batch_size)):
            offset_stop = min(offset + self._batch_size, self._num_users)
            predictions = self._model.get_recs(
                (
                    np.repeat(np.array(list(range(offset, offset_stop)))[:, None], repeats=self._num_items, axis=1),
                    np.array([self._i_items_set for _ in range(offset, offset_stop)])
                 )
            )
            v, i = self._model.get_top_k(predictions, self.get_train_mask(offset, offset_stop), k=k)
            items_ratings_pair = [list(zip(map(self._data.private_items.get, u_list[0]), u_list[1]))
                                  for u_list in list(zip(i.numpy(), v.numpy()))]
            predictions_top_k.update(dict(zip(map(self._data.private_users.get,
                                                  range(offset, offset_stop)), items_ratings_pair)))
        return predictions_top_k

    def restore_weights(self, it):
        if self._restore_epochs == it:
            try:
                with open(self._saving_filepath, "rb") as f:
                    self._model.set_model_state(pickle.load(f))
                print(f"Model correctly Restored at Epoch: {self._restore_epochs}")
                return True
            except Exception as ex:
                print(f"Error in model restoring operation! {ex}")
        return False