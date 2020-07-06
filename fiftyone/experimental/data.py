"""
Experimental dataset definitions.

| Copyright 2017-2020, Voxel51, Inc.
| `voxel51.com <https://voxel51.com/>`_
|
"""
# pragma pylint: disable=redefined-builtin
# pragma pylint: disable=unused-wildcard-import
# pragma pylint: disable=wildcard-import
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from builtins import *
from future.utils import iteritems, itervalues

# pragma pylint: enable=redefined-builtin
# pragma pylint: enable=unused-wildcard-import
# pragma pylint: enable=wildcard-import

import datetime
import os
from uuid import uuid4

import eta.core.datasets as etads
import eta.core.image as etai
from eta.core.serial import Serializable
import eta.core.utils as etau

import fiftyone as fo
import fiftyone.core.utils as fou
import fiftyone.experimental.contexts as foec
import fiftyone.utils.data as foud


def from_image_classification_samples(samples, labels_map=None, name=None):
    """Creates a :class:`fiftyone.experimental.data.Dataset` from the given
    image classification samples.

    The input ``samples`` can be any iterable that emits
    ``(image_path, target)`` tuples, where:

        - ``image_path`` is the path to the image on disk

        - ``target`` is either a label string, or, if a ``labels_map`` is
          provided, a class ID that can be mapped to a label string via
          ``labels_map[target]``

    For example, ``samples`` may be a ``torch.utils.data.Dataset`` or an
    iterable generated by ``tf.data.Dataset.as_numpy_iterator()``.

    This operation will iterate over all provided samples, but the images will
    not be read.

    If your samples do not fit this schema, see
    :func:`from_labeled_image_samples` for details on how to provide your own
    :class:`fiftyone.core.datautils.LabeledImageSampleParser` that can parse
    your samples.

    Args:
        samples: an iterable of samples
        labels_map (None): an optional dict mapping class IDs to label strings.
            If provided, it is assumed that ``target`` is a class ID that
            should be mapped to a label string via ``labels_map[target]``
        name (None): a name for the dataset. By default,
            :func:`get_default_dataset_name` is used

    Returns:
        a :class:`fiftyone.experimental.data.Dataset`
    """
    sample_parser = foud.ImageClassificationSampleParser(labels_map=labels_map)
    return from_labeled_image_samples(
        samples, sample_parser=sample_parser, name=name,
    )


def from_image_detection_samples(samples, labels_map=None, name=None):
    """Creates a :class:`fiftyone.experimental.data.Dataset` from the given
    image detection samples.

    The input ``samples`` can be any iterable that emits
    ``(image_path, target)`` tuples, where:

        - ``image_path`` is the path to the image on disk

        - ``target`` is a list of detections in the following format::

            [
                {
                    "label": label,
                    "bounding_box": [top-left-x, top-left-y, width, height],
                    ...
                },
                ...
            ]

          where ``label`` is either a label string, or, if a ``labels_map`` is
          provided, a class ID that can be mapped to a label string via
          ``labels_map[target]``, and the bounding box coordinates are relative
          values in ``[0, 1] x [0, 1]``

    For example, ``samples`` may be a ``torch.utils.data.Dataset`` or an
    iterable generated by ``tf.data.Dataset.as_numpy_iterator()``.

    This operation will iterate over all provided samples, but the images will
    not be read.

    If your samples do not fit this schema, see
    :func:`from_labeled_image_samples` for details on how to provide your own
    :class:`fiftyone.core.datautils.LabeledImageSampleParser` that can parse
    your samples.

    Args:
        samples: an iterable of samples
        labels_map (None): an optional dict mapping class IDs to label strings.
            If provided, it is assumed that the ``label`` values in ``target``
            are class IDs that should be mapped to label strings via
            ``labels_map[target]``
        name (None): a name for the dataset. By default,
            :func:`get_default_dataset_name` is used

    Returns:
        a :class:`fiftyone.experimental.data.Dataset`
    """
    sample_parser = foud.ImageDetectionSampleParser(labels_map=labels_map)
    return from_labeled_image_samples(
        samples, sample_parser=sample_parser, name=name,
    )


def from_labeled_image_samples(samples, sample_parser=None, name=None):
    """Creates a :class:`fiftyone.experimental.data.Dataset` from the given
    labeled image samples.

    The input ``samples`` can be any iterable that emits
    ``(image_path, image_labels)`` tuples, where:

        - ``image_path`` is the path to the image on disk

        - ``image_labels`` is an ``eta.core.image.ImageLabels`` instance, a
          serialized dict or string representation of one, or an arbitrary
          object that can be converted into this format by passing the sample
          to the :func:`fiftyone.core.datautils.LabeledImageSampleParser.parse_label`
          method of the provided ``sample_parser``

    For example, ``samples`` may be a ``torch.utils.data.Dataset`` or an
    iterable generated by ``tf.data.Dataset.as_numpy_iterator()``.

    This operation will iterate over all provided samples, but the images will
    not be read.

    Args:
        samples: an iterable of samples
        sample_parser (None): an optional
            :class:`fiftyone.core.datautils.LabeledImageSampleParser` whose
            :func:`fiftyone.core.datautils.LabeledImageSampleParser.parse_label`
            method will be used to parse the ``image_labels`` in the provided
            samples
        name (None): a name for the dataset. By default,
            :func:`get_default_dataset_name` is used

    Returns:
        a :class:`fiftyone.experimental.data.Dataset`
    """
    if name is None:
        name = get_default_dataset_name()

    # Ingest labels
    image_paths = []
    labels = []
    for sample in samples:
        image_path, image_labels = sample

        # Ingest image path
        image_paths.append(os.path.abspath(image_path))

        # Ingest labels
        if sample_parser is not None:
            image_labels = sample_parser.parse_label(sample)

        image_labels = fou.parse_serializable(image_labels, etai.ImageLabels)
        labels.append(image_labels)

    return Dataset.from_ground_truth_samples(name, image_paths, labels)


def from_labeled_image_dataset(dataset_dir, name=None):
    """Creates a :class:`fiftyone.experimental.data.Dataset` from the labeled
    image dataset in the given directory stored in
    ``eta.core.datasets.LabeledImageDataset`` format.

    See :func:`fiftyone.core.datautils.to_labeled_image_dataset` to convert
    your own samples into this format, if desired.

    Args:
        dataset_dir: a ``eta.core.datasets.LabeledImageDataset`` directory
        name (None): a name for the dataset. By default,
            :func:`get_default_dataset_name` is used

    Returns:
        a :class:`fiftyone.experimental.data.Dataset`
    """
    if name is None:
        name = get_default_dataset_name()

    labeled_dataset = etads.load_dataset(dataset_dir)
    return Dataset.from_ground_truth_labeled_samples(name, labeled_dataset)


def from_images_dir(images_dir, recursive=False, name=None):
    """Creates a :class:`fiftyone.experimental.data.Dataset` from the given
    directory of images.

    This operation does not read the images.

    Args:
        images_dir: a directory of images
        recursive (False): whether to recursively traverse subdirectories
        name (None): a name for the dataset. By default,
            :func:`get_default_dataset_name` is used

    Returns:
        a :class:`fiftyone.experimental.data.Dataset`
    """
    image_paths = etau.list_files(
        images_dir, abs_paths=True, recursive=recursive
    )
    return from_images(image_paths, name=name)


def from_images_patt(image_patt, name=None):
    """Creates a :class:`fiftyone.experimental.data.Dataset` from the given
    glob pattern of images.

    This operation does not read the images.

    Args:
        image_patt: a glob pattern of images like ``/path/to/images/*.jpg``
        name (None): a name for the dataset. By default,
            :func:`get_default_dataset_name` is used

    Returns:
        a :class:`fiftyone.experimental.data.Dataset`
    """
    image_paths = etau.parse_glob_pattern(image_patt)
    return from_images(image_paths, name=name)


def from_images(image_paths, name=None):
    """Creates a :class:`fiftyone.experimental.data.Dataset` from the given
    list of images.

    This operation does not read the images.

    Args:
        image_paths: a list of image paths
        name (None): a name for the dataset. By default,
            :func:`get_default_dataset_name` is used

    Returns:
        a :class:`fiftyone.experimental.data.Dataset`
    """
    if name is None:
        name = get_default_dataset_name()

    image_paths = [os.path.abspath(p) for p in image_paths]

    return Dataset.from_unlabeled_data(name, image_paths)


def get_default_dataset_name():
    """Returns a default dataset name based on the current time.

    Returns:
        a dataset name
    """
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_default_dataset_dir(name, split=None):
    """Returns the default dataset directory for the dataset with the given
    name.

    Args:
        name: the dataset name
        split (None): an optional split

    Returns:
        the default dataset directory
    """
    dataset_dir = os.path.join(fo.config.default_dataset_dir, name)
    if split is not None:
        dataset_dir = os.path.join(dataset_dir, split)

    return dataset_dir


class DatasetSample(Serializable):
    """Class encapsulating a sample in a dataset.

    Args:
        sample_id: the ID of the sample
        data_path: the path to the data on disk
        gt_labels (None): optional ground truth ``eta.core.image.ImageLabels``
    """

    def __init__(self, sample_id, data_path, gt_labels=None, **kwargs):
        self.sample_id = sample_id
        self.data_path = data_path
        self.gt_labels = gt_labels
        for attr, value in kwargs.items():
            setattr(self, attr, value)

    @property
    def has_gt_labels(self):
        """Whether this sample has ground truth labels."""
        return self.gt_labels is not None

    @classmethod
    def from_dict(cls, d):
        """Creates a DatasetSample from a JSON dictionary.

        Args:
            d: a JSON dictionary

        Returns:
            a DatasetSample
        """
        return cls(**d)


class Dataset(object):
    """Class encapsulating a FiftyOne dataset and its associated samples,
    ground truth annotations, and model(s) predictions.

    Args:
        name: the name of the dataset
        samples (None): a list of :class:`DatasetSample`s
    """

    def __init__(self, name, samples=None):
        if samples is None:
            samples = []

        self._name = name
        self._samples = {sample.sample_id: sample for sample in samples}
        self._models = []

    def __len__(self):
        return len(self._samples)

    def __bool__(self):
        return bool(self._samples)

    def __getitem__(self, sample_id):
        return self._samples[sample_id]

    def __contains__(self, sample_id):
        return sample_id in self._samples

    def __iter__(self):
        return iter(itervalues(self._samples))

    def iter_sample_ids(self):
        """Returns an iterator over the sample IDs in the dataset.

        Returns:
            an iterator over sample IDs
        """
        return iter(self._samples)

    @property
    def name(self):
        """The name of the dataset."""
        return self._name

    @classmethod
    def empty(cls, name):
        """Creates an empty Dataset.

        Args:
            name: the name of the dataset

        Returns:
            a Dataset
        """
        return cls(name)

    @classmethod
    def from_unlabeled_data(cls, name, data_paths):
        """Creates a Dataset from a list of unlabeled data paths.

        Args:
            name: the name of the dataset
            data_paths: a list of data paths

        Returns:
            a Dataset
        """
        samples = []
        for data_path in data_paths:
            sample_id = str(uuid4())  # placeholder UUID
            samples.append(DatasetSample(sample_id, data_path))

        return cls(name, samples=samples)

    @classmethod
    def from_ground_truth_samples(cls, name, data_paths, gt_labels):
        """Creates a Dataset from a set of samples with ground truth
        annotations.

        Args:
            name: the name of the dataset
            data_paths: an iterable of data paths
            gt_labels: an iterable of ground truth labels

        Returns:
            a Dataset
        """
        samples = []
        for data_path, labels in zip(data_paths, gt_labels):
            sample_id = str(uuid4())  # placeholder UUID
            samples.append(
                DatasetSample(sample_id, data_path, gt_labels=labels)
            )

        return cls(name, samples=samples)

    @classmethod
    def from_ground_truth_labeled_samples(cls, name, labeled_dataset):
        """Creates a Dataset from an ``eta.core.datasets.LabeledDataset`` of
        ground truth annotations.

        Args:
            name: the name of the dataset
            labeled_dataset: an ``eta.core.datasets.LabeledDataset``

        Returns:
            a Dataset
        """
        data_paths = labeled_dataset.iter_data_paths()
        gt_labels = labeled_dataset.iter_labels()
        return cls.from_ground_truth_samples(name, data_paths, gt_labels)

    def get_image_context(self):
        """Returns a :class:`fiftyone.core.contexts.ImageContext` for the
        images in the dataset.

        Returns:
            a :class:`fiftyone.core.contexts.ImageContext`
        """
        return foec.ImageContext(self)

    def get_ground_truth_context(self):
        """Returns a :class:`fiftyone.core.contexts.LabeledImageContext` for
        the ground truth annotations on the dataset.

        Returns:
            a :class:`fiftyone.core.contexts.LabeledImageContext`
        """
        return foec.LabeledImageContext(self, "gt_labels")

    def register_model(self, name):
        """Registers a model for use with the dataset.

        Args:
            name: a name for the model
        """
        if name in self._models:
            raise ValueError("Dataset already has a model named '%s'" % name)

        self._models.append(name)

    def get_models(self):
        """Returns the list of models registered with the dataset.

        Returns:
            the list of models
        """
        return self._models

    def get_model_context(self, name):
        """Returns a :class:`fiftyone.core.contexts.ModelContext` for the
        dataset for the model with the given name.

        Args:
            name: the name of the model

        Returns:
            a :class:`fiftyone.core.contexts.ModelContext`
        """
        return foec.ModelContext(self, name)

    def publish_model_context(self, model_context):
        """Publishes the given :class:`fiftyone.core.contexts.ModelContext` to
        the dataset.

        Args:
            model_context: a :class:`fiftyone.core.contexts.ModelContext`
        """
        if model_context.name not in self._models:
            raise ValueError("Dataset has no model '%s'" % model_context.name)

        label_field = model_context.name
        for sample_id, prediction in iteritems(model_context.predictions):
            setattr(self._samples[sample_id], label_field, prediction)