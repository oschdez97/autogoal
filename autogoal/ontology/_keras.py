# coding: utf8

import datetime
import inspect
import itertools
import re
from pathlib import Path

import keras.layers
import tensorflow_hub as hub

from ._nn import (
    Part_Of_NN,
    NN_Preprocesor,
    NN_Classifier,
    NN_Abtract_Feautures,
    NN_Reduction,
)
from .base import BaseAbstract, BaseObject, register_concrete_class

# ========================================
## New Keras layers that we implement here
# ----------------------------------------

class Bert(keras.layers.Layer):
    """ Permite utilizar Bert junto a queras y representa un embeding basado en Bert
    """

    def __init__(self, n_fine_tune_layers=10, **kwargs):
        self.n_fine_tune_layers = n_fine_tune_layers
        self.trainable = True
        self.output_size = 768
        super(Bert, self).__init__(**kwargs)

    def build(self, input_shape):
        self.bert = hub.Module(
            bert_path, trainable=self.trainable, name="{}_module".format(self.name)
        )
        trainable_vars = self.bert.variables

        # Remove unused layers
        trainable_vars = [var for var in trainable_vars if not "/cls/" in var.name]

        # Select how many layers to fine tune
        trainable_vars = trainable_vars[-self.n_fine_tune_layers :]

        # Add to trainable weights
        for var in trainable_vars:
            self._trainable_weights.append(var)

        # Add non-trainable weights
        for var in self.bert.variables:
            if var not in self._trainable_weights:
                self._non_trainable_weights.append(var)

        super(BertLayer, self).build(input_shape)

    def call(self, inputs):
        inputs = [K.cast(x, dtype="int32") for x in inputs]
        input_ids, input_mask, segment_ids = inputs
        bert_inputs = dict(
            input_ids=input_ids, input_mask=input_mask, segment_ids=segment_ids
        )
        result = self.bert(inputs=bert_inputs, signature="tokens", as_dict=True)[
            "pooled_output"
        ]
        return result

    def compute_output_shape(self, input_shape):
        return (input_shape[0], self.output_size)


# ==================
## Utility functions
# ------------------

def _get_keras_layers(
    ignore=set(["Lambda", "Layer", "Highway", "MaxoutDense", "Input", "InputLayer"])
):
    """Load all `keras.layers` classes that inherit from `Layer`, except those in `ignore`."""

    for layer_name in dir(keras.layers):
        if layer_name in ignore:
            continue
        if layer_name[0].isupper():
            layer_clss = getattr(keras.layers, layer_name)
            try:
                if issubclass(layer_clss, keras.layers.Layer):
                    yield layer_clss
            except:
                pass

    yield Bert


def _get_keras_layer_args(layer):
    """Computes the mandatory args for the constructor of `layer`, which
    are either `int` or `float`.

    Returns a dictionary mapping arg name to its type.
    """

    init_args = inspect.signature(layer.__init__).parameters
    layers_args = {}

    for arg_name, arg in init_args.items():
        if arg_name in ["self", "args", "kwargs"]:
            continue

        if arg.default == arg.empty:
            layers_args[arg_name] = None

    if not layers_args:
        return {}

    input_sample = keras.layers.Input(shape=(1,))

    for p in itertools.combinations_with_replacement([1.33, 32], len(layers_args)):
        for i, key in enumerate(layers_args):
            layers_args[key] = p[i]

        try:
            layer(**layers_args)(input_sample)
            return {k: v.__class__ for k, v in layers_args.items()}
        except:
            pass

    print("Layer %s with args %r is None" % (layer.__name__, layers_args))
    return None


class KerasWrapper(Part_Of_NN):
    def _build_model(self, model):
        return self.keras_class(**self.kwargs)(model)


PARENT_MAPPINGS = {
    "Bert": ['NN_Preprocesor'],
    "Dense": ['NN_Preprocesor','NN_Reduction', 'NN_Abtract_Feautures','Compose_Clasifier'],
    "Sofmax": ['NN_Clasifier'],
    "Convolutional": ['NN_Reduction'],
}


def build_module():
    with (Path(__file__).parent / "_generated" / "_keras.py").open("w") as fp:
        fp.write("# AUTOGENERATED ON {}\n".format(datetime.datetime.now()))
        fp.write("## DO NOT MODIFY THIS FILE MANUALLY\n\n\n")
        fp.write("import keras.layers\n")
        fp.write("from ..base import BaseObject\n")
        fp.write("from ..base import register_concrete_class\n")
        fp.write("from ..base import Discrete\n")
        fp.write("from ..base import Continuous\n")
        fp.write("from .._keras import KerasWrapper\n")
        fp.write("from .._nn import NN_Preprocesor\n")
        fp.write("\n\n")

        for layer in _get_keras_layers():
            args = _get_keras_layer_args(layer)

            if args is None:
                continue

            print(layer.__name__)
            fp.write("@register_concrete_class\n")
            parents = ['BaseObject', 'KerasWrapper']

            for expr, bases in PARENT_MAPPINGS.items():
                if re.match(expr, layer.__name__)

            fp.write(
                "class {}Layer({}):\n".format(layer.__name__, ", ".join(parents))
            )
            fp.write("\tdef __init__(\n")
            fp.write("\t\tself,\n")

            for arg, typ in args.items():
                fp.write("\t\t{}: ".format(arg))
                if typ == int:
                    fp.write("Discrete({}, {}),\n".format(0, 100))
                elif typ == float:
                    fp.write("Continuous({}, {}),\n".format(0.0, 1.0))

            fp.write("\t):\n")
            fp.write("\t\tself.keras_class = keras.layers.{}\n".format(layer.__name__))
            fp.write("\t\tself.kwargs = {}\n")
            for arg, typ in args.items():
                fp.write("\t\tself.kwargs['{}'] = {}\n".format(arg, arg))
            fp.write("\n\n")

            #     print(" -", arg, ":", typ.__name__)
            # layer_instance.hasParameter.append(parameter)


def build_ontology_keras(onto):
    for layer in _get_keras_layers():
        args = _get_keras_layer_args(layer)

        if args is None:
            continue

        print(layer.__name__)
        layer_instance = onto.NeuralNetworkLayer(layer.__name__ + "Layer")

        for arg, typ in args.items():
            if typ == int:
                parameter = onto.DiscreteHyperParameter(layer.__name__ + "__" + arg)
                parameter.hasMinIntValue = 0
                parameter.hasMaxIntValue = 100
            elif typ == float:
                parameter = onto.ContinuousHyperParameter(layer.__name__ + "__" + arg)
                parameter.hasMinFloatValue = 0.0
                parameter.hasMaxFloatValue = 100.0

            print(" -", arg, ":", typ.__name__)
            layer_instance.hasParameter.append(parameter)
