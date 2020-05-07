"""
Core definitions of FiftyOne sample collections.

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

# pragma pylint: enable=redefined-builtin
# pragma pylint: enable=unused-wildcard-import
# pragma pylint: enable=wildcard-import

import logging

import eta.core.utils as etau

import fiftyone.core.datautils as fod
import fiftyone.core.labels as fol


logger = logging.getLogger(__name__)


class SampleCollection(object):
    """Abstract class representing a collection of
    :class:`fiftyone.core.sample.Sample` instances.
    """

    def __bool__(self):
        return len(self) > 0

    def __len__(self):
        raise NotImplementedError("Subclass must implement __len__()")

    def __contains__(self, sample_id):
        try:
            self[sample_id]
        except ValueError:
            return False

        return True

    def __getitem__(self, sample_id):
        raise NotImplementedError("Subclass must implement __getitem__()")

    def __iter__(self):
        return self.iter_samples()

    @property
    def _sample_cls(self):
        raise NotImplementedError("Subclass must implement _get_sample_cls()")

    def get_tags(self):
        """Returns the list of tags in the collection.

        Returns:
            a list of tags
        """
        raise NotImplementedError("Subclass must implement get_tags()")

    def get_label_groups(self):
        """Returns the list of label groups attached to at least one sample
        in the collection.

        Returns:
            a list of groups
        """
        raise NotImplementedError("Subclass must implement get_label_groups()")

    def get_insight_groups(self):
        """Returns the list of insight groups attached to at least one sample
        in the collection.

        Returns:
            a list of groups
        """
        raise NotImplementedError(
            "Subclass must implement get_insight_groups()"
        )

    def iter_samples(self):
        """Returns an iterator over the samples in the collection.

        Returns:
            an iterator over :class:`fiftyone.core.sample.Sample` instances
        """
        raise NotImplementedError("Subclass must implement iter_samples()")

    def export(self, group, export_dir):
        """Exports the samples in the collection to disk as a labeled dataset,
        using the given label group as labels.

        The format of the dataset on disk will depend on the
        :class:`fiftyone.core.labels.Label` class of the labels in the
        specified group.

        Args:
            group: the label group to use
            export_dir: the directory to which to export
        """
        data_paths = []
        labels = []
        for sample in self.iter_samples():
            data_paths.append(sample.filepath)
            labels.append(sample.get_label[group])

        if not labels:
            logger.warning("No samples to export; returning now")
            return

        if isinstance(labels[0], fol.ClassificationLabel):
            fod.export_image_classification_dataset(
                data_paths, labels, export_dir
            )
        if isinstance(labels[0], fol.DetectionLabels):
            fod.export_image_detection_dataset(data_paths, labels, export_dir)
        elif isinstance(labels[0], fol.ImageLabels):
            fod.export_image_labels_dataset(data_paths, labels, export_dir)
        else:
            raise ValueError(
                "Cannot export labels of type '%s'"
                % etau.get_class_name(labels[0])
            )