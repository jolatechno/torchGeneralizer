import torch
from torch import nn
import torch.nn.functional as F

import numpy as np

"""
helper functions
"""

def listify(x, dims=1):
	if isinstance(x, list) or dims < 0:
		return x
	return [x for i in range(dims)]

def sequencify(x, nlist=1, dims=1):
	if nlist < 0:
		return x
	if isinstance(x, list):
		if isinstance(x[0], list):
			return x
		return [x for i in range(nlist)]
	return [[x for i in range(dims)] for i in range(nlist)]

def extendedLen(x):
	if isinstance(x, list):
		return len(x)
	return -1

"""
functions for convNdAuto
"""

def calcShape(input_shape, kernel, stride=1, dilation=1, padding=0):
	dim = max(extendedLen(input_shape), extendedLen(kernel), extendedLen(stride), extendedLen(dilation), extendedLen(padding))
	if dim == -1:
		return 0
	
	input_shape = listify(input_shape, dim)
	kernel = listify(kernel, dim)
	stride = listify(stride, dim)
	dilation = listify(dilation, dim)
	padding = listify(padding, dim)
	
	return [calcShape(i, k, s, d, p) for i, k, s, d, p in zip(input_shape, kernel, stride, dilation, padding)]

"""
padding functions
"""

def pad(input, padding, mode='constant', value=0):
	padding = listify(padding, input.ndim)
	padding = np.repeat(padding[::-1], 2)
	return F.pad(input=input, pad=tuple(padding), mode=mode, value=value)

def Pad(padding, mode='constant', value=0):
	return lambda input: pad(input, padding, mode, value)

"""
slicing functions
"""

def view(input, kernel, stride=1):
    strided, kernel, stride = input, listify(kernel, input.ndim), listify(stride, input.ndim)
    
    for dim, (k, s) in enumerate(zip(kernel, stride)):
    	strided = strided.unfold(dim, k, s)

    return strided

def View(kernel, stride=1):
	return lambda input: view(input, kernel, stride)

"""
functions to prepare a convolution
"""

def convPrep(input, kernel, stride=1, padding=0, padding_mode='constant', padding_value=0):
	in_dim = input.ndim
	padded = pad(input, padding, padding_mode, padding_value)
	strided = view(input, kernel, stride)

	shape = strided.shape[:in_dim]
	return strided.flatten(0, in_dim - 1), shape

def ConvPrep(input, kernel, stride=1, padding=0, padding_mode='constant', padding_value=0):
	Fpad = Pad(padding, padding_mode, padding_value)
	Fstride = View(kernel, stride)
	
	return lambda input: Fstride(Fpad(input))

"""
functions to postprocess a convolution result
"""

letters = 'abcdefghijklmnopqrstuvwxyz'

def convPost(input, shape):
	input = input.reshape(*shape, *input.shape[1:])

	dim = input.ndim//2
	command = letters[:2*dim] + " -> "
	for i in range(dim):
	    command = command + letters[i] + letters[i + dim]

	out = torch.einsum(command, input)
	for i in range(dim):
	    out = out.flatten(i, i + 1)

	return out

"""
custom layers
"""

class Flatten(nn.Module):
	def forward(self, input):
		return input.flatten(1)

class Reshape(nn.Module):
	def __init__(self, shape):
		super(Reshape, self).__init__()
		self.shape = shape

	def forward(self, input):
		shape = listify(self.shape, input.ndim)
		return input.reshape(-1, *shape)
