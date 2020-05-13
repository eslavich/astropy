# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from asdf.versioning import AsdfVersion

from astropy.modeling import mappings
from astropy.modeling import functional_models
from astropy.modeling.core import CompoundModel
from astropy.io.misc.asdf.types import AstropyTransformMapper
from . import _parameter_to_value


__all__ = ['TransformMapper', 'IdentityMapper', 'ConstantMapper']


class TransformMapper(AstropyTransformMapper):
    def _from_tree_base_transform_members(self, model, node, ctx):
        if 'inverse' in node:
            model.inverse = node['inverse']

        if 'name' in node:
            model.name = node['name']

        if 'bounding_box' in node:
            model.bounding_box = node['bounding_box']

        if "inputs" in node:
            if model.n_inputs == 1:
                model.inputs = (node["inputs"],)
            else:
                model.inputs = tuple(node["inputs"])

        if "outputs" in node:
            if model.n_outputs == 1:
                model.outputs = (node["outputs"],)
            else:
                model.outputs = tuple(node["outputs"])

        param_and_model_constraints = {}
        for constraint in ['fixed', 'bounds']:
            if constraint in node:
                param_and_model_constraints[constraint] = node[constraint]
        model._initialize_constraints(param_and_model_constraints)

        return model

    def from_tree_transform(self, node, ctx):
        raise NotImplementedError(
            "Must be implemented in TransformMapper subclasses")

    def from_tree(self, node, ctx):
        model = self.from_tree_transform(node, ctx)
        yield model
        self._from_tree_base_transform_members(model, node, ctx)

    def _to_tree_base_transform_members(self, model, node, ctx):
        if getattr(model, '_user_inverse', None) is not None:
            node['inverse'] = model._user_inverse

        if model.name is not None:
            node['name'] = model.name

        try:
            bb = model.bounding_box
        except NotImplementedError:
            bb = None

        if bb is not None:
            if model.n_inputs == 1:
                bb = list(bb)
            else:
                bb = [list(item) for item in model.bounding_box]
            node['bounding_box'] = bb
        if type(model.__class__.inputs) != property:
            node['inputs'] = model.inputs
            node['outputs'] = model.outputs

        # model / parameter constraints
        if not isinstance(model, CompoundModel):
            fixed_nondefaults = {k: f for k, f in model.fixed.items() if f}
            if fixed_nondefaults:
                node['fixed'] = fixed_nondefaults
            bounds_nondefaults = {k: b for k, b in model.bounds.items() if any(b)}
            if bounds_nondefaults:
                node['bounds'] = bounds_nondefaults

    def to_tree_transform(self, model, ctx):
        raise NotImplementedError("Must be implemented in TransformType subclasses")

    def to_tree(self, model, ctx):
        node = self.to_tree_transform(model, ctx)
        self._to_tree_base_transform_members(model, node, ctx)
        return node


class IdentityMapper(TransformMapper):
    schema_ids = [
        "http://astroasdf.org/schemas/transform/identity-1.0.0",
        "http://stsci.edu/schemas/asdf/transform/identity-1.2.0"
        "http://stsci.edu/schemas/asdf/transform/identity-1.1.0",
        "http://stsci.edu/schemas/asdf/transform/identity-1.0.0",
    ]
    types = [mappings.Identity]

    def from_tree_transform(self, node, ctx):
        return mappings.Identity(node.get('n_dims', 1))

    def to_tree_transform(self, data, ctx):
        node = {}
        if data.n_inputs != 1:
            node['n_dims'] = data.n_inputs
        return node


class ConstantMapper(TransformMapper):
    schema_ids = [
        "http://astroasdf.org/schemas/transform/constant-1.0.0",
        "http://stsci.edu/schemas/asdf/transform/constant-1.4.0",
        "http://stsci.edu/schemas/asdf/transform/constant-1.3.0",
        "http://stsci.edu/schemas/asdf/transform/constant-1.2.0",
        "http://stsci.edu/schemas/asdf/transform/constant-1.1.0",
        "http://stsci.edu/schemas/asdf/transform/constant-1.0.0",
    ]
    types = [functional_models.Const1D, functional_models.Const2D]

    def from_tree_transform(self, node, ctx):
        if "stsci.edu" in self.schema_id and self.version < AsdfVersion('1.4.0'):
            # The 'dimensions' property was added in 1.4.0,
            # previously all values were 1D.
            return functional_models.Const1D(node['value'])
        elif node['dimensions'] == 1:
            return functional_models.Const1D(node['value'])
        elif node['dimensions'] == 2:
            return functional_models.Const2D(node['value'])

    def to_tree_transform(self, data, ctx):
        if "stsci.edu" in self.schema_id and self.version < AsdfVersion('1.4.0'):
            if not isinstance(data, functional_models.Const1D):
                raise ValueError(
                    f'{self.schema_id} does not support models with > 1 dimension')
            return {
                'value': _parameter_to_value(data.amplitude)
            }
        else:
            if isinstance(data, functional_models.Const1D):
                dimension = 1
            elif isinstance(data, functional_models.Const2D):
                dimension = 2
            return {
                'value': _parameter_to_value(data.amplitude),
                'dimensions': dimension
            }


class GenericModel(mappings.Mapping):

    def __init__(self, n_inputs, n_outputs):
        mapping = tuple(range(n_inputs))
        super().__init__(mapping)
        self._n_outputs = n_outputs
        self._outputs = tuple('x' + str(idx) for idx in range(n_outputs))

    @property
    def inverse(self):
        raise NotImplementedError()


class GenericMapper(TransformMapper):
    schema_ids = [
        "http://astroasdf.org/schemas/transform/generic-1.0.0",
        "http://stsci.edu/schemas/asdf/transform/generic-1.2.0",
        "http://stsci.edu/schemas/asdf/transform/generic-1.1.0",
        "http://stsci.edu/schemas/asdf/transform/generic-1.0.0",
    ]
    types = [functional_models.Const1D, functional_models.Const2D]
    types = [GenericModel]

    def from_tree_transform(self, node, ctx):
        return GenericModel(
            node['n_inputs'], node['n_outputs'])

    def to_tree_transform(self, data, ctx):
        return {
            'n_inputs': data.n_inputs,
            'n_outputs': data.n_outputs
        }

