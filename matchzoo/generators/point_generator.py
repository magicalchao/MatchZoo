"""Matchzoo point generator."""

from matchzoo import engine
from matchzoo import tasks
from matchzoo.datapack import DataPack
from matchzoo import utils

import numpy as np
import typing


class PointGenerator(engine.BaseGenerator):
    """PointGenerator for Matchzoo.

    Ponit generator can be used for classification as well as ranking.

    Examples:
        >>> import pandas as pd
        >>> relation = [['qid0', 'did0', 1]]
        >>> left = [['qid0', [1, 2]]]
        >>> right = [['did0', [2, 3]]]
        >>> relation = pd.DataFrame(relation,
        ...                         columns=['id_left', 'id_right', 'label'])
        >>> left = pd.DataFrame(left, columns=['id_left', 'text_left'])
        >>> left.set_index('id_left', inplace=True)
        >>> left['length_left'] = left.apply(lambda x: len(x['text_left']),
        ...                                  axis=1)
        >>> right = pd.DataFrame(right, columns=['id_right', 'text_right'])
        >>> right.set_index('id_right', inplace=True)
        >>> right['length_right'] = right.apply(lambda x: len(x['text_right']),
        ...                                     axis=1)
        >>> input = datapack.DataPack(relation=relation,
        ...                           left=left,
        ...                           right=right
        ... )
        >>> task = tasks.Classification()
        >>> generator = PointGenerator(input, task, 1, 'train', False)
        >>> x, y = generator[0]
        >>> x['text_left'].tolist()
        [[1, 2]]
        >>> x['text_right'].tolist()
        [[2, 3]]
        >>> x['id_left'].tolist()
        ['qid0']
        >>> x['id_right'].tolist()
        ['did0']
        >>> x['length_left'].tolist()
        [2]
        >>> x['length_right'].tolist()
        [2]
        >>> y.tolist()
        [[0.0, 1.0]]

    """

    def __init__(
        self,
        datapack,
        task: engine.BaseTask = tasks.Classification(2),
        batch_size: int = 32,
        shuffle: bool = True
    ):
        """Construct the point generator.

        :param datapack: the output generated by :class:`DataPack`.
        :param task: the task is a instance of :class:`engine.BaseTask`.
        :param batch_size: number of instances in a batch.
            `evaluate`, or `predict` expected.
        :param shuffle: whether to shuffle the instances while generating a
            batch.
        """
        self._datapack = datapack
        self._task = task
        super().__init__(batch_size, len(datapack.relation), stage, shuffle)

    def _get_batch_of_transformed_samples(
        self,
        index_array: np.array
    ) -> typing.Tuple[dict, typing.Any]:
        """Get a batch of samples based on their ids.

        :param index_array: a list of instance ids.
        :return: A batch of transformed samples.
        """
        batch_y = None

        left_columns = self._datapack.left.columns.values.tolist()
        right_columns = self._datapack.right.columns.values.tolist()
        columns = left_columns + right_columns + ['id_left', 'id_right']

        batch_x = dict.fromkeys(columns, [])

        relation = self._datapack.relation

        if self._datapack.stage == 'train':
            type_ = self._task.output_dtype
            relation['label'] = relation['label'].astype(type_)

            if isinstance(self._task, tasks.Ranking):
                batch_y = relation['label'][index_array].values
            elif isinstance(self._task, tasks.Classification):
                batch_y = np.zeros((len(index_array), self._task.num_classes))
                for idx, label in enumerate(relation['label'][index_array]):
                    batch_y[idx, label] = 1
            else:
                msg = f"{self._task} is not a valid task type."
                msg += ":class:`Ranking` and :class:`Classification` expected."
                raise ValueError(msg)

        batch_x['id_left'] = relation.iloc[index_array, 0]
        for column in self._datapack.left.columns:
            batch_x[column] = self._datapack.left.loc[
                (relation.iloc[index_array, 0]), column].tolist()

        batch_x['id_right'] = relation.iloc[index_array, 1]
        for column in self._datapack.right.columns:
            batch_x[column] = self._datapack.right.loc[
                (relation.iloc[index_array, 1]), column].tolist()

        for key, val in batch_x.items():
            batch_x[key] = np.array(val)

        return batch_x, batch_y
