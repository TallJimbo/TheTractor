# Copyright 2011 Dustin Lang and David W. Hogg.  All rights reserved.
import numpy as np

import mixture_profiles as mp
from engine import *
from utils import *

class GalaxyShape(ParamList):
	def getNamedParams(self):
		# re: arcsec
		# ab: axis ratio, dimensionless, in [0,1]
		# phi: deg, "E of N", 0=direction of increasing Dec, 90=direction of increasing RA
		return [('re', 0), ('ab', 1), ('phi', 2)]
	def hashkey(self):
		return ('GalaxyShape',) + tuple(self.vals)
	def __repr__(self):
		return 're=%g, ab=%g, phi=%g' % (self.re, self.ab, self.phi)
	def __str__(self):
		return 're=%.1f, ab=%.2f, phi=%.1f' % (self.re, self.ab, self.phi)
	def copy(self):
		return GalaxyShape(*self.vals)
	def getParamNames(self):
		return ['re', 'ab', 'phi']

	def getStepSizes(self, img):
		abstep = 0.01
		if self.ab >= (1 - abstep):
			abstep = -abstep
		return [ 1., abstep, 1. ]

	def setre(self, re):
		if re < (1./30.):
			#print 'Clamping re from', re, 'to 1/30'
			pass
		self.re = max(1./30., re)
	def setab(self, ab):
		if ab > 1.:
			#print 'Converting ab from', ab, 'to', 1./ab
			self.setab(1./ab)
			self.setphi(self.phi+90.)
		elif ab < (1./30.):
			#print 'Clamping ab from', ab, 'to 1/30'
			self.ab = 1./30
		else:
			self.ab = ab
	def setphi(self, phi):
		# limit phi to [-180,180]
		self.phi = np.fmod(phi, 360.)
		if self.phi < -180.:
			self.phi += 360.
		if self.phi > 180.:
			self.phi -= 360.

	# Note about flipping the galaxy when ab>1:
	#
	# -you might worry that the caller would choose a new ab>1 and
	#  phi, then call setab() then setphi() -- so then the phi would
	#  be reverted.
	#
	# -but in Tractor.tryParamUpdates, it only calls getParams() and
	#  setParams() to revert to original params.
	#
	# -stepping params one at a time works fine, so it's all ok.

	def setParams(self, p):
		assert(len(p) == 3)
		self.setre(p[0])
		self.setab(p[1])
		self.setphi(p[2])
	def setParam(self, i, p):
		oldval = self.vals[i]
		if i == 0:
			self.setre(p)
		elif i == 1:
			self.setab(p)
		elif i == 2:
			self.setphi(p)
		else:
			raise RuntimeError('GalaxyShape: unknown param index: ' + str(i))
		return oldval

	def getTensor(self, cd):
		# convert re, ab, phi into a transformation matrix
		phi = np.deg2rad(90 - self.phi)
		# convert re to degrees
		re_deg = self.re / 3600.
		cp = np.cos(phi)
		sp = np.sin(phi)
		# Squish, rotate, and scale into degrees.
		# G takes unit vectors (in r_e) to degrees (~intermediate world coords)
		G = re_deg * np.array([[ cp, sp * self.ab],
							   [-sp, cp * self.ab]])
		# "cd" takes pixels to degrees (intermediate world coords)
		# T takes pixels to unit vectors.
		#print 'phi', phi, 're', re_deg
		#print 'G', G
		T = np.dot(np.linalg.inv(G), cd)
		return T

class Galaxy(MultiParams):
	def __init__(self, pos, brightness, shape):
		MultiParams.__init__(self, pos, brightness, shape)
		self.name = self.getName()
		self.dname = self.getDName()

	def getName(self):
		return 'Galaxy'

	def getDName(self):
		'''
		Name used in labeling the derivative images d(Dname)/dx, eg
		'''
		return 'gal'
		
	def getSourceType(self):
		return self.name

	def getPosition(self):
		return self.pos

	def getBrightness(self):
		return self.brightness
	def setBrightness(self, brightness):
		self.brightness = brightness

	def getNamedParams(self):
		return [('pos', 0), ('brightness', 1), ('shape', 2)]

	def __getattr__(self, name):
		if name in ['re', 'ab', 'phi']:
			return getattr(self.shape, name)
		return MultiParams.__getattr__(self, name)

	def __setattr__(self, name, val):
		if name in ['re', 'ab', 'phi']:
			setattr(self.shape, name, val)
			return
		MultiParams.__setattr__(self, name, val)

	def hashkey(self):
		return (self.name, self.pos.hashkey(), self.brightness.hashkey(),
				self.re, self.ab, self.phi)
	def __str__(self):
		return (self.name + ' at ' + str(self.pos)
				+ ' with ' + str(self.brightness)
				+ ', re=%.1f, ab=%.2f, phi=%.1f' % (self.re, self.ab, self.phi))
	def __repr__(self):
		return (self.name + '(pos=' + repr(self.pos) +
				', brightness=' + repr(self.brightness) +
				', re=%.1f, ab=%.2f, phi=%.1f)' % (self.re, self.ab, self.phi))

	def copy(self):
		return None

	def getProfile(self):
		return None

	def getUnitFluxModelPatch(self, img, px=None, py=None):
		raise RuntimeError('getUnitFluxModelPatch unimplemented in' +
						   self.getName())

	def getModelPatch(self, img, px=None, py=None):
		counts = img.getPhotoCal().brightnessToCounts(self.brightness)
		p1 = self.getUnitFluxModelPatch(img, px, py)
		if p1 is None:
			return None
		return p1 * counts

	# returns [ Patch, Patch, ... ] of length numberOfParams().
	# Galaxy.
	def getParamDerivatives(self, img, brightnessonly=False):
		pos0 = self.getPosition()
		(px0,py0) = img.getWcs().positionToPixel(self, pos0)
		counts = img.getPhotoCal().brightnessToCounts(self.brightness)
		patch0 = self.getUnitFluxModelPatch(img, px0, py0)
		if patch0 is None:
			return [None] * self.numberOfParams()
		derivs = []

		# derivatives wrt position
		psteps = pos0.getStepSizes(img)
		if brightnessonly or self.isParamPinned('pos'):
			derivs.extend([None] * len(psteps))
		else:
			params = pos0.getParams()
			for i,pstep in enumerate(psteps):
				oldval = pos0.setParam(i, params[i]+pstep)
				(px,py) = img.getWcs().positionToPixel(self, pos0)
				pos0.setParam(i, oldval)
				patchx = self.getUnitFluxModelPatch(img, px, py)
				if patchx is None or patchx.getImage() is None:
					derivs.append(None)
					continue
				dx = (patchx - patch0) * (counts / pstep)
				dx.setName('d(%s)/d(pos%i)' % (self.dname, i))
				derivs.append(dx)

		# derivatives wrt brightness
		bsteps = self.brightness.getStepSizes(img)
		if self.isParamPinned('brightness'):
			derivs.extend([None] * len(bsteps))
		else:
			params = self.brightness.getParams()
			for i,bstep in enumerate(bsteps):
				oldval = self.brightness.setParam(i, params[i] + bstep)
				countsi = img.getPhotoCal().brightnessToCounts(self.brightness)
				self.brightness.setParam(i, oldval)
				df = patch0 * ((countsi - counts) / bstep)
				df.setName('d(%s)/d(bright%i)' % (self.dname, i))
				derivs.append(df)

		# derivatives wrt shape
		gsteps = self.shape.getStepSizes(img)
		if brightnessonly or self.isParamPinned('shape'):
			derivs.extend([None] * len(gsteps))
		else:
			gnames = self.shape.getParamNames()
			oldvals = self.shape.getParams()
			# print 'Galaxy.getParamDerivatives:', self.getName()
			# print '  oldvals:', oldvals
			for i,gstep in enumerate(gsteps):
				oldval = self.shape.setParam(i, oldvals[i]+gstep)
				#print '  stepped', gnames[i], 'by', gsteps[i],
				#print 'to get', self.shape
				patchx = self.getUnitFluxModelPatch(img, px0, py0)
				self.shape.setParam(i, oldval)
				#print '  reverted to', self.shape
				if patchx is None:
					print 'patchx is None:'
					print '  ', self
					print '  stepping galaxy shape', self.shape.getParamNames()[i]
					print '  stepped', gsteps[i]
					print '  to', self.shape.getParams()[i]
					derivs.append(None)

				dx = (patchx - patch0) * (counts / gstep)
				dx.setName('d(%s)/d(%s)' % (self.dname, gnames[i]))
				derivs.append(dx)
		return derivs


class CompositeGalaxy(Galaxy):
	'''
	A galaxy with Exponential and deVaucouleurs components.

	The two components share a position (ie the centers are the same),
	but have different brightnesses and shapes.
	'''
	def __init__(self, pos, brightnessExp, shapeExp, brightnessDev, shapeDev):
		MultiParams.__init__(self, pos, brightnessExp, shapeExp, brightnessDev, shapeDev)
		self.name = self.getName()
	def getName(self):
		return 'CompositeGalaxy'
	def getNamedParams(self):
		return [('pos', 0), ('brightnessExp', 1), ('shapeExp', 2),
				('brightnessDev', 3), ('shapeDev', 4),]
	#def getBrightness(self):
		#return self.brightnessExp + self.brightnessDev

	def hashkey(self):
		return (self.name, self.pos.hashkey(),
				self.brightnessExp.hashkey(), self.shapeExp.hashkey(),
				self.brightnessDev.hashkey(), self.shapeDev.hashkey())
	def __str__(self):
		return (self.name + ' at ' + str(self.pos)
				+ ' with Exp ' + str(self.brightnessExp) + ' ' + str(self.shapeExp)
				+ ' and deV ' + str(self.brightnessDev) + ' ' + str(self.shapeDev))
	def __repr__(self):
		return (self.name + '(pos=' + repr(self.pos) +
				', brightnessExp=' + repr(self.brightnessExp) +
				', shapeExp=' + repr(self.shapeExp) + 
				', brightnessDev=' + repr(self.brightnessDev) +
				', shapeDev=' + repr(self.shapeDev))
	def copy(self):
		return CompositeGalaxy(self.pos.copy(), self.brightnessExp.copy(),
							   self.shapeExp.copy(), self.brightnessDev.copy(),
							   self.shapeDev.copy())
	def getModelPatch(self, img, px=None, py=None):
		e = ExpGalaxy(self.pos, self.brightnessExp, self.shapeExp)
		d = DevGalaxy(self.pos, self.brightnessDev, self.shapeDev)
		pe = e.getModelPatch(img, px, py)
		pd = d.getModelPatch(img, px, py)
		if pe is None:
			return pd
		if pd is None:
			return pe
		return pe + pd
	
	def getUnitFluxModelPatch(self, img, px=None, py=None):
		# this code is un-tested
		assert(False)
		fe = self.brightnessExp / (self.brightnessExp + self.brightnessDev)
		fd = 1. - fe
		assert(fe >= 0.)
		assert(fe <= 1.)
		e = ExpGalaxy(self.pos, fe, self.shapeExp)
		d = DevGalaxy(self.pos, fd, self.shapeDev)
		pe = e.getModelPatch(img, px, py)
		pd = d.getModelPatch(img, px, py)
		if pe is None:
			return pd
		if pd is None:
			return pe
		return pe + pd

	# MAGIC: ORDERING OF EXP AND DEV PARAMETERS
	# MAGIC: ASSUMES EXP AND DEV SHAPES SAME LENGTH
	# CompositeGalaxy.
	def getParamDerivatives(self, img, brightnessonly=False):
		#print 'CompositeGalaxy: getParamDerivatives'
		#print '  Exp brightness', self.brightnessExp, 'shape', self.shapeExp
		#print '  Dev brightness', self.brightnessDev, 'shape', self.shapeDev
		e = ExpGalaxy(self.pos, self.brightnessExp, self.shapeExp)
		d = DevGalaxy(self.pos, self.brightnessDev, self.shapeDev)
		e.dname = 'comp.exp'
		d.dname = 'comp.dev'
		# pin through...
		if self.isParamPinned('brightnessExp'):
			e.pinParam('brightness')
		if self.isParamPinned('shapeExp'):
			e.pinParam('shape')
		if self.isParamPinned('brightnessDev'):
			d.pinParam('brightness')
		if self.isParamPinned('shapeDev'):
			d.pinParam('shape')
		de = e.getParamDerivatives(img, brightnessonly)
		dd = d.getParamDerivatives(img, brightnessonly)
		npos = len(self.pos.getStepSizes(img))
		derivs = []
		if brightnessonly or self.isParamPinned('pos'):
			derivs.extend([None] * npos)
		else:
			for i in range(npos):
				#dp = de[i] + dd[i]   -- but one or both could be None
				dp = de[i]
				if dd[i] is not None:
					if dp is None:
						dp = dd[i]
					else:
						dp += dd[i]
				if dp is not None: 
					dp.setName('d(comp)/d(pos%i)' % i)
				derivs.append(dp)
		derivs.extend(de[npos:])
		derivs.extend(dd[npos:])
		return derivs

class HoggGalaxy(Galaxy):
	ps = PlotSequence('hg', format='%03i')

	def __init__(self, pos, brightness, *args):
		'''
		HoggGalaxy(pos, brightness, GalaxyShape)
		or
		HoggGalaxy(pos, brightness, re, ab, phi)

		re: [arcsec]
		phi: [deg]
		'''
		if len(args) == 3:
			shape = GalaxyShape(*args)
		else:
			assert(len(args) == 1)
			shape = args[0]
		Galaxy.__init__(self, pos, brightness, shape)

	def getName(self):
		return 'HoggGalaxy'

	def copy(self):
		return HoggGalaxy(self.pos.copy(), self.brightness.copy(),
						  self.shape.copy())

	def getUnitFluxModelPatch(self, img, px=None, py=None):
		if px is None or py is None:
			(px,py) = img.getWcs().positionToPixel(self, self.getPosition())
		galmix = self.getProfile()
		# shift and squash
		cd = img.getWcs().cdAtPixel(px, py)
		Tinv = np.linalg.inv(self.shape.getTensor(cd))
		try:
			amix = galmix.apply_affine(np.array([px,py]), Tinv.T)
		except:
			print 'Failed in getModelPatch of', self
			return None

		if False:
			(eval, evec) = np.linalg.eig(amix.var[0])
			print amix.var[0]
			print 'true ab:', self.ab
			print 'eigenval-based ab:', np.sqrt(eval[1]/eval[0])
			print 'true phi:', self.phi
			print 'eigenvec-based phi:', deg2rad(np.arctan2(evec[0,1], evec[0,0])), deg2rad(np.arctan2(evec[1,0], evec[0,0]))
		amix.symmetrize()
		# now convolve with the PSF
		psf = img.getPsf()
		psfmix = psf.getMixtureOfGaussians()
		psfmix.normalize()
		cmix = amix.convolve(psfmix)
		# now choose the patch size
		pixscale = np.sqrt(np.abs(np.linalg.det(cd)))
		if self.ab <= 1:
			halfsize = max(8., 8. * (self.re / 3600.) / pixscale)
		else:
			halfsize = max(8., 8. * (self.re*self.ab / 3600.) / pixscale)
		# now evaluate the mixture on the patch pixels
		(outx, inx) = get_overlapping_region(int(floor(px-halfsize)), int(ceil(px+halfsize+1)), 0., img.getWidth())
		(outy, iny) = get_overlapping_region(int(floor(py-halfsize)), int(ceil(py+halfsize+1)), 0., img.getHeight())
		if inx == [] or iny == []:
			print 'No overlap between model and image'
			return None
		x0 = outx.start
		y0 = outy.start
		x1 = outx.stop
		y1 = outy.stop
		psfconvolvedimg = mp.mixture_to_patch(cmix, np.array([x0,y0]),
											  np.array([x1,y1]))

		#print 'psf sum of ampls:', np.sum(psfmix.amp)
		#print 'unconvolved mixture sum of ampls:', np.sum(amix.amp)
		#print 'convolved mixture sum of ampls:', np.sum(cmix.amp)
		#print 'psf-conv img sum:', psfconvolvedimg.sum()
		# now return a calibrated patch
		#print 'x0,y0', x0,y0
		#print 'patch shape', psfconvolvedimg.shape
		#print 'img w,h', img.getWidth(), img.getHeight()

		if False:
			plt.clf()
			plt.imshow(psfconvolvedimg*counts,
					   interpolation='nearest', origin='lower')
			plt.hot()
			plt.colorbar()
			HoggGalaxy.ps.savefig()

		return Patch(x0, y0, psfconvolvedimg)


class ExpGalaxy(HoggGalaxy):
	profile = mp.get_exp_mixture()
	profile.normalize()
	@staticmethod
	def getExpProfile():
		return ExpGalaxy.profile
	def getName(self):
		return 'ExpGalaxy'
	def getProfile(self):
		return ExpGalaxy.getExpProfile()
	def copy(self):
		return ExpGalaxy(self.pos.copy(), self.brightness.copy(),
						 self.shape.copy())

class DevGalaxy(HoggGalaxy):
	profile = mp.get_dev_mixture()
	profile.normalize()
	@staticmethod
	def getDevProfile():
		return DevGalaxy.profile
	def getName(self):
		return 'DevGalaxy'
	def getProfile(self):
		return DevGalaxy.getDevProfile()
	def copy(self):
		return DevGalaxy(self.pos.copy(), self.brightness.copy(),
						 self.shape.copy())
