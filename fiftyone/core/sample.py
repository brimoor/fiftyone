"""

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

from collections import OrderedDict
import os
import six
import warnings

from mongoengine import (
    EmbeddedDocument,
    BooleanField,
    IntField,
    StringField,
    ListField,
    DictField,
    EmbeddedDocumentField,
)
from mongoengine.fields import BaseField

import fiftyone.core.odm as foo
import fiftyone.core.metadata as fom


class ODMSample(foo.ODMDocument):
    """Abstract ODMSample class that all
    :class:`fiftyone.core.dataset.Dataset._Doc` classes inherit from.
    Instances of the subclasses are samples. I.e.:

        sample = dataset._Doc(...)

    Samples store all information associated with a particular piece of data in
    a dataset, including basic metadata about the data, one or more sets of
    labels (ground truth, user-provided, or FiftyOne-generated), and additional
    features associated with subsets of the data and/or label sets.
    """

    meta = {"abstract": True}

    # the path to the data on disk
    filepath = StringField(unique=True)
    # the set of tags associated with the sample
    tags = ListField(StringField())
    # metadata about the sample media
    metadata = EmbeddedDocumentField(fom.Metadata, null=True)

    @classmethod
    def get_fields(cls, field_type=None):
        """Gets a dictionary of all document fields on elements of this
        collection.

        Args:
            field_type (None): the subclass of ``BaseField`` for primitives
                or ``EmbeddedDocument`` for ``EmbeddedDocumentField``s to
                filter by


        Returns:
             a dictionary of (field name: field type) per field that is a
             subclass of ``field_type``
        """
        if field_type is None:
            field_type = BaseField

        if not issubclass(field_type, BaseField) and not issubclass(
            field_type, EmbeddedDocument
        ):
            raise ValueError(
                "field_type must be subclass of %s or %s" % BaseField,
                EmbeddedDocument,
            )

        d = OrderedDict()

        for field_name in cls._fields_ordered:
            field = cls._fields[field_name]
            if issubclass(field_type, BaseField):
                if isinstance(field, field_type):
                    d[field_name] = field
            elif isinstance(field, EmbeddedDocumentField):
                if issubclass(field.document_type, field_type):
                    d[field_name] = field

        return d

    @property
    def in_dataset(self):
        """Whether the sample has been added to a dataset."""
        # @todo(Tyler) I don't want this function to be lost in the changes
        #   I'm making so I'm leaving it here. May become irrelevant or change
        #   so I'll worry about it later
        raise NotImplementedError("TODO")
        # return self._dataset is not None

    @property
    def dataset_name(self):
        """The name of the dataset to which this sample belongs, or ``None`` if
        it has not been added to a dataset.
        """
        # @todo(Tyler) maybe get rid of this?
        raise NotImplementedError("TODO")

    @property
    def filename(self):
        """The name of the raw data file on disk."""
        return os.path.basename(self.filepath)

    def __setattr__(self, name, value):
        # all attrs starting with "_" or that exist and are not fields are
        # deferred to super
        if name.startswith("_") or (
            hasattr(self, name) and name not in self._fields
        ):
            return super(ODMSample, self).__setattr__(name, value)

        cls = self.__class__

        if hasattr(cls, name):
            if value is not None:
                getattr(cls, name).validate(value)

            result = super(ODMSample, self).__setattr__(name, value)
            if (
                name not in ["_cls", "id"]
                and isinstance(getattr(cls, name), BaseField)
                and self._in_db
            ):
                # autosave the change to existing attrs
                self.save()
            return result

        warnings.warn(
            "Fiftyone doesn't allow fields to be "
            "created via a new attribute name",
            stacklevel=2,
        )
        return super(ODMSample, self).__setattr__(name, value)

    def __getitem__(self, key):
        if isinstance(key, six.string_types) and hasattr(self, key):
            return self.__getattribute__(key)
        return super(ODMSample, self).__getitem__(key)

    def __setitem__(self, key, value):
        return self.set_field(field_name=key, value=value, create=True)

    @classmethod
    def add_field(
        cls, field_name, field_type, embedded_doc_type=None, subfield=None
    ):
        """Add a new field to the dataset

        Args:
            field_name: the string name of the field to add
            field_type: the type (subclass of BaseField) of the field to create
            embedded_doc_type (None): the EmbeddedDocument type, used if
                    field_type=EmbeddedDocumentField
                ignored otherwise
            subfield (None): the optional contained field for lists and dicts,
                if provided

        """
        if field_name in cls._fields:
            raise ValueError("Field '%s' already exists" % field_name)

        if not issubclass(field_type, BaseField):
            raise ValueError(
                "Invalid field type '%s' is not a subclass of '%s'"
                % (field_type, BaseField)
            )

        kwargs = {"db_field": field_name}

        if issubclass(field_type, EmbeddedDocumentField):
            kwargs.update(
                {"document_type": embedded_doc_type, "null": True,}
            )
        elif any(issubclass(field_type, ft) for ft in [ListField, DictField]):
            if subfield is not None:
                kwargs["field"] = subfield

        # Mimicking setting a DynamicField from this code:
        #   https://github.com/MongoEngine/mongoengine/blob/3db9d58dac138dd0e838c524f616ebe3d23db2ff/mongoengine/base/document.py#L170
        field = field_type(**kwargs)
        field.name = field_name
        cls._fields[field_name] = field
        cls._fields_ordered += (field_name,)
        setattr(cls, field_name, field)

    def set_field(self, field_name, value, create=False):
        """Set the value of a field for a sample

        Args:
            field_name: the string name of the field to add
            value: the value to set the field to
            create (False): If True and field_name is not set on the dataset,
                create a field on the dataset of a type implied by value

        Raises:
            ValueError: if:
                the field_name is invalid
                the field_name does not exist and create=False
        """
        if field_name.startswith("_"):
            raise ValueError(
                "Invalid field name: '%s'. Field name cannot start with '_'"
                % field_name
            )

        if hasattr(self, field_name) and field_name not in self._fields:
            raise ValueError("Cannot set reserve word '%s'" % field_name)

        if field_name not in self._fields:
            if create:
                self._add_implied_field(field_name, value)
            else:
                raise ValueError(
                    "Sample does not have field '%s'. Use `create=True` to create a new field."
                )

        return self.__setattr__(field_name, value)

    @classmethod
    def _add_implied_field(cls, field_name, value):
        """Determine the field type from the value type"""
        assert (
            field_name not in cls._fields
        ), "Attempting to add field that already exists"

        if isinstance(value, EmbeddedDocument):
            cls.add_field(
                field_name,
                EmbeddedDocumentField,
                embedded_doc_type=type(value),
            )
        elif isinstance(value, bool):
            cls.add_field(field_name, BooleanField)
        elif isinstance(value, six.integer_types):
            cls.add_field(field_name, IntField)
        elif isinstance(value, six.string_types):
            cls.add_field(field_name, StringField)
        elif isinstance(value, list) or isinstance(value, tuple):
            # @todo(Tyler) set the subfield of ListField and
            #   ensure all elements are of this type
            cls.add_field(field_name, ListField)
        elif isinstance(value, dict):
            cls.add_field(field_name, DictField)
        else:
            raise TypeError(
                "Invalid type: '%s' could not be cast to Field" % type(value)
            )
