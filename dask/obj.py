
from into import discover, convert
from toolz import merge, concat
from datashape import DataShape
import itertools
from math import ceil
import numpy as np
from . import core
from .array import getem, concatenate


class Array(object):
    __slots__ = 'dask', 'name', 'shape', 'blockshape'

    def __init__(self, dask, name, shape, blockshape):
        self.dask = dask
        self.name = name
        self.shape = shape
        self.blockshape = blockshape

    @property
    def numblocks(self):
        return tuple(int(ceil(a / b))
                     for a, b in zip(self.shape, self.blockshape))

    def _get_block(self, *args):
        return core.get(self.dask, (self.name,) + args)

    @property
    def ndim(self):
        return len(self.shape)

    def block_keys(self, *args):
        ind = len(args)
        if ind + 1 == self.ndim:
            return [(self.name,) + args + (i,)
                        for i in range(self.numblocks[ind])]
        else:
            return [self.block_keys(*(args + (i,)))
                        for i in range(self.numblocks[ind])]


@discover.register(Array)
def discover_dask_array(a, **kwargs):
    block = a._get_block(*([0] * a.ndim))
    return DataShape(*(a.shape + (discover(block).measure,)))


arrays = [np.ndarray]
try:
    import h5py
    arrays.append(h5py.Dataset)
except ImportError:
    pass
try:
    import bcolz
    arrays.append(bcolz.carray)
except ImportError:
    pass


names = concat([iter('xyz'), ('x_%d' % i for i in itertools.count(1))])

@convert.register(Array, tuple(arrays), cost=0.01)
def array_to_dask(x, name=None, blockshape=None, **kwargs):
    name = name or next(names)
    dask = merge({name: x}, getem(name, blockshape, x.shape))

    return Array(dask, name, x.shape, blockshape)


@convert.register(np.ndarray, Array, cost=0.5)
def dask_to_numpy(x, **kwargs):
    return concatenate(core.get(x.dask, x.block_keys()))
