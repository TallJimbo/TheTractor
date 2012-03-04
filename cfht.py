class CfhtPhotoCal(object):
	def __init__(self, hdr=None, bandname=None):
		self.bandname = bandname
		if hdr is not None:
			self.exptime = hdr['EXPTIME']
			self.phot_c = hdr['PHOT_C']
			self.phot_k = hdr['PHOT_K']
			self.airmass = hdr['AIRMASS']
			print 'CFHT photometry:', self.exptime, self.phot_c, self.phot_k, self.airmass
		# FIXME -- NO COLOR TERMS (phot_x)!
		'''
COMMENT   Formula for Photometry, based on keywords given in this header:
COMMENT   m = -2.5*log(DN) + 2.5*log(EXPTIME)
COMMENT   M = m + PHOT_C + PHOT_K*(AIRMASS - 1) + PHOT_X*(PHOT_C1 - PHOT_C2)
'''
	def hashkey(self):
		return ('CfhtPhotoCal', self.exptime, self.phot_c, self.phot_k, self.airmass)

	def getParams(self):
		return (self.phot_c,)
			
	def brightnessToCounts(self, brightness):
		#M = brightness.getValue()
		M = brightness.getMag(self.bandname)
		logc = (M - self.phot_c - self.phot_k * (self.airmass - 1.)) / -2.5
		return self.exptime * 10.**logc
	#def countsToBrightness(self, counts):
	#	return Mag(-2.5 * np.log10(counts / self.exptime) +
	#			   self.phot_c + self.phot_k * (self.airmass - 1.))
		
