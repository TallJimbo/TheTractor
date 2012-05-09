# this file is part of the Tractor project.
# Copyright 2011 David W. Hogg.

import matplotlib
matplotlib.use('Agg')
import pylab as plt
import matplotlib.cm as cm
import numpy as np
import scipy.optimize as op

# note wacky normalization because this is for 2-d Gaussians
# (but only ever called in 1-d).  Wacky!
def not_normal(x, V):
    exparg = -0.5 * x**2 / V
    result = np.zeros_like(x)
    I = ((exparg > -1000) * (exparg < 1000))
    result[I] = 1. / (2. * np.pi * V) * np.exp(exparg[I])
    return result

# magic numbers from Lupton (makeprof.c and phFitobj.h) via dstn
def hogg_exp(x):
    return np.exp(-1.67835 * (x - 1.))

# magic numbers from Lupton (makeprof.c and phFitobj.h) via dstn
def hogg_dev(x):
    return np.exp(-7.66925 * ((x*x + 0.0004)**0.125 - 1.))

# magic numbers from Lupton (makeprof.c and phFitobj.h) via dstn
def hogg_lup(x):
    inner = 7.
    outer = 8.
    lup = hogg_dev(x)
    outside = (x >= outer)
    lup[outside] *= 0.
    middle = (x >= inner) * (x <= outer)
    lup[middle] *= (outer - x[middle]) / (outer - inner)
    return lup

def hogg_model(x, model):
    if model == 'exp':
        return hogg_exp(x)
    if model == 'dev':
        return hogg_dev(x)
    if model == 'lup':
        return hogg_lup(x)
    assert(1 == 0)
    return None

def mixture_of_not_normals(x, pars):
    K = len(pars)/2
    y = 0.
    for k in range(K):
        y += pars[k] * not_normal(x, pars[k+K])
    return y

# note that you can do (x * ymix - x * ytrue)**2 or (ymix - ytrue)**2
# each has disadvantages.
# note magic number in the penalty for large variance
def badness_of_fit(lnpars, model):
    pars = np.exp(lnpars)
    x = np.arange(0.0005, MAX_RADIUS, 0.001)
    badness = np.mean((mixture_of_not_normals(x, pars)
               - hogg_model(x, model))**2) / 10.**LOG10_SQUARED_DEVIATION
    K = len(pars) / 2
    var = pars[K:]
    extrabadness = 0.0001 * np.sum(var) / MAX_RADIUS**2
    return badness + extrabadness

def optimize_mixture(K, pars, model):
    newlnpars = op.fmin_bfgs(badness_of_fit, np.log(pars), args=(model, ))
    return (badness_of_fit(newlnpars, model), np.exp(newlnpars))

def plot_mixture(pars, prefix, model):
    x2 = np.arange(0., 10.*MAX_RADIUS, 0.001)
    y1 = hogg_model(x2, model)
    badness = badness_of_fit(np.log(pars), model)
    K = len(pars) / 2
    y2 = mixture_of_not_normals(x2, pars)
    plt.clf()
    plt.plot(x2, y1, 'k-')
    plt.plot(x2, y2, 'k-', lw=4, alpha=0.25)
    for k in range(K):
        plt.plot(x2, pars[k] * not_normal(x2, pars[k+K]), 'k-', alpha=0.5)
    plt.axvline(MAX_RADIUS, color='k', alpha=0.25)
    plt.title(r"%s / $K=%d$ / maximum radius = $%.1f$ / badness = $%.2f\times 10^{%d}$"
              % (model, len(pars)/2, MAX_RADIUS, badness, LOG10_SQUARED_DEVIATION))
    plt.xlim(-0.1*MAX_RADIUS, 2.*MAX_RADIUS)
    plt.ylim(-0.1*np.max(y1), 1.1*np.max(y1))
    plt.savefig(prefix+'_'+model+'.png')
    plt.loglog()
    plt.xlim(0.001, 10.*MAX_RADIUS)
    plt.ylim(3.e-5, 1.5*np.max(y1))
    plt.savefig(prefix+'_'+model+'_log.png')

def rearrange_pars(pars):
    K = len(pars) / 2
    indx = np.argsort(pars[K:K+K])
    amp = pars[indx]
    var = pars[K+indx]
    return np.append(amp, var)

# run this (possibly with adjustments to the magic numbers at top)
# to find different or better mixtures approximations
def main(model):
    amp = np.array([1.0])
    var = np.array([1.0])
    pars = np.append(amp, var)
    (badness, pars) = optimize_mixture(1, pars, model)
    lastKbadness = badness
    bestbadness = badness
    for K in range(2,20):
        print 'working on K = %d' % K
        newvar = 2.0 * np.max(np.append(var, 1.0))
        newamp = 1.0 * newvar
        amp = np.append(newamp, amp)
        var = np.append(newvar, var)
        pars = np.append(amp, var)
        for i in range(2 * K):
            (badness, pars) = optimize_mixture(K, pars, model)
            if (badness < bestbadness) or (i == 0):
                print '%d %d improved' % (K, i)
                bestpars = pars
                bestbadness = badness
            else:
                print '%d %d not improved' % (K, i)
                print i, len(var), K, np.mod(i, K)
                var[0] = 2.0 * var[np.mod(i, K)]
                amp[0] = 0.5 * amp[np.mod(i, K)]
                pars = np.append(amp, var)
                if (bestbadness < 0.5 * lastKbadness) and (i > 4):
                    print '%d %d improved enough' % (K, i)
                    break
            lastKbadness = bestbadness
            pars = rearrange_pars(bestpars)
            amp = pars[0:K]
            var = pars[K:K+K]
            prefix = 'K%02d_MR%02d_LSD%02d' % (K, int(round(MAX_RADIUS) + 0.01), -1 * LOG10_SQUARED_DEVIATION)
            plot_mixture(pars, prefix, model)
            txtfile = open(prefix + '_' + model + '.txt', "w")
            txtfile.write(str(pars))
            txtfile.close
        if bestbadness < 1.:
            break

if __name__ == '__main__':
    LOG10_SQUARED_DEVIATION = -4
    MAX_RADIUS = 8.
    main('dev')
    main('lup')
    LOG10_SQUARED_DEVIATION = -6
    MAX_RADIUS = 8.
    main('exp')
