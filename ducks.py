"""
This file is part of the Tractor project.
Copyright 2011, 2012 Dustin Lang and David W. Hogg.
Licensed under the GPLv2; see the file COPYING for details.

`ducks.py`
===========

Duck-type definitions of types used by the Tractor.

Most of this code is not actually used at all.  It's here for
documentation purposes.

"""

class Params(object):
	'''
	A set of parameters that can be optimized by the Tractor.

	This is a duck-type definition.
	'''
	def copy(self):
		return None
		
	def hashkey(self):
		'''
		Returns a tuple containing the state of this `Params` object
		for use as a cache key.

		All elements must be hashable: see
		http://docs.python.org/glossary.html#term-hashable
		'''
		return ()
	def __hash__(self):
		''' Params must be hashable. '''
		return None
	#def __eq__(self, other):

	def getParamNames(self):
		''' Returns a list of strings: the names of the parameters. '''
		return []
	def numberOfParams(self):
		''' Returns the number of parameters (ie, number of scalar
		values).'''
		return len(self.getParams())
	def getParams(self):
		''' Returns a *copy* of the current parameter values as an
		iterable (eg, list)'''
		return []
	def getStepSizes(self, *args, **kwargs):
		''' Returns "reasonable" step sizes for the parameters.'''
		return []
	def setParams(self, p):
		''' Sets the parameter values to the values in the given
		iterable `p`.  The length of `p` will be equal to
		`numberOfParams()`.'''
		pass
	def setParam(self, i, p):
		'''
		Sets parameter index 'i' to new value 'p'.

		i: integer in the range [0, numberOfParams()).
		p: float

		Returns the old value.
		'''
		return None


class Sky(Params):
	'''
	Duck-type definition for a sky model.
	'''
	def getParamDerivatives(self, img):
		'''
		Returns [ Patch, Patch, ... ], of length numberOfParams(),
		containing the derivatives in the given `Image` for each
		parameter.
		'''
		return []
	def addTo(self, mod):
		'''
		Add the sky to the input synthetic image `mod`, a 2-D numpy
		array.
		'''
		pass


class Source(Params):
	'''
	This is the duck-type definition of a Source (star, galaxy, etc)
	that the Tractor uses.
	'''
	def getModelPatch(self, img):
		'''
		Returns a Patch object containing a rendering of this Source
		into the given `Image` object.  This will probably use the
		calibration information of the `Image`: the WCS, PSF, and
		photometric calibration.
		'''
		pass

	def getParamDerivatives(self, img):
		'''
		Returns [ Patch, Patch, ... ], of length numberOfParams(),
		containing the derivatives in the given `Image` for each
		parameter.
		'''
		return []

class Brightness(Params):
	'''
	Duck-type definition of the brightness of an astronomical source.

	Only used as an input to `PhotoCal`.  `Source`s have
	`Brightness`es; `PhotoCal`s convert these into counts in a
	specific `Image`.
	'''
	pass

class PhotoCal(Params):
	'''
	Duck-type definition of photometric calibration.

	A `PhotoCal` belongs to an `Image`; it converts `Brightness`
	values into counts ("data numbers", ADU, etc) in the data space
	(synthetic image) of the `Image`.  It also contains the parameters
	of that conversion so they can be optimized along with everything
	else.

	This relationship need not be linear: the `Brightness` could be an
	astronomical magnitude, for example.  In general, there is a lot
	of freedom in the definition of the `Brightness` object, and
	`PhotoCal` has to be kept consistent with that.
	'''
	def brightnessToCounts(self, brightness):
		'''Converts `brightness`, a `Brightness` duck, into counts.

		Returns: float
		'''
		pass


class Position(Params):
	'''
	Duck-type definition of the position of an astronomical object.

	Only used as an input to a `WCS` object; `Sources` have
	`Positions`, and `WCS` objects convert them into pixel coordinates
	in a specific `Image`.
	'''

class WCS(Params):
	'''
	Duck-type definition of World Coordinate System.
	
	Converts between Position objects and Image pixel coordinates.

	In general, there is a lot of freedom in the definition of the
	`Position` object, and `WCS` has to be kept consistent with that.
	For instance, if the `Positions` used are image-based x-y
	positions (`PixPos`), then `WCS` has to be null (or close to
	that); `NullWCS`.
	'''
	def positionToPixel(self, pos, src=None):
		'''
		Converts a `Position` into x,y pixel coordinates.

		Note that the `Source` may be passed in; your `WCS` could have
		color-specific behavior, for example.

		Returns tuple `(x, y)`, where `x` and `y` are floats.
		'''
		return None

	def cdAtPixel(self, x, y):
		'''
		Returns a local affine relationship between `Position` and
		(x,y) pixel coordinates.  This is used, for example, to
		convert tensor shapes of galaxies from `Position` space to
		image space.

		Returns a numpy array of shape (2,2).

		In FITS celestial coordinates language, this is the CD matrix
		at pixel x,y:

		[ [ dRA/dx * cos(Dec), dRA/dy * cos(Dec) ],
		  [ dDec/dx          , dDec/dy           ] ]

		in FITS these are called:
		[ [ CD11             , CD12              ],
		  [ CD21             , CD22              ] ]
		'''
		return None

class PSF(Params):
	'''
	Duck-type definition of a point-spread function.
	'''
	def getPointSourcePatch(self, px, py):
		'''
		Returns a `Patch`, a rendering of a point source at the given
		pixel coordinates.

		The returned `Patch` should have unit "counts".
		'''
		pass

	def getRadius(self):
		'''
		Returns the size of the support of this PSF.

		This is required because the Tractor has to decide what size
		to make the `Patch`es.
		'''
		return 0

