#!/usr/bin/env python
#
# Authors: James D. McClain <jmcclain@princeton.edu>
#
"""Module for running k-point ccsd(t)"""

import time
import tempfile
import numpy
import numpy as np
import h5py

from pyscf import lib
import pyscf.ao2mo
from pyscf.lib import logger
import pyscf.cc
import pyscf.cc.ccsd
from pyscf.pbc import scf
from pyscf.pbc.mp.kmp2 import get_frozen_mask, get_nocc, get_nmo
from pyscf.lib import linalg_helper
from pyscf.pbc.lib import kpts_helper

#einsum = np.einsum
einsum = lib.einsum

def kernel(mycc, eris=None, t1=None, t2=None, max_memory=2000, verbose=logger.INFO):
    """
    This function returns the CCSD(T) energy.
    """
    if isinstance(verbose, logger.Logger):
        log = verbose
    else:
        log = logger.Logger(mycc.stdout, verbose)

    if eris is None: eris = mycc.eris
    if t1 is None: t1 = mycc.t1
    if t2 is None: t2 = mycc.t2

    cell = mycc._scf.cell
    kpts = mycc.kpts

    # The dtype of any local arrays that will be created
    dtype = t1.dtype

    nkpts, nocc, nvir = t1.shape

    mo_energy_occ = [eris.fock[i].diagonal()[:nocc] for i in range(nkpts)]
    mo_energy_vir = [eris.fock[i].diagonal()[nocc:] for i in range(nkpts)]
    fov = eris.fock[:, :nocc, nocc:]

    # Set up class for k-point conservation
    kconserv = kpts_helper.get_kconserv(cell, kpts)

    energy_t = 0.0

    full_t3c = np.zeros((nkpts, nkpts, nkpts, nkpts, nkpts, nocc, nocc, nocc, nvir, nvir, nvir), dtype=dtype)
    full_t3d = np.zeros((nkpts, nkpts, nkpts, nkpts, nkpts, nocc, nocc, nocc, nvir, nvir, nvir), dtype=dtype)
    for ki in range(nkpts):
        for kj in range(nkpts):
            for kk in range(nkpts):

                # eigenvalue denominator: e(i) + e(j) + e(k)
                eijk = lib.direct_sum('i,j,k->ijk', mo_energy_occ[ki], mo_energy_occ[kj], mo_energy_occ[kk])

                for ka in range(nkpts):
                    for kb in range(nkpts):

                        # Find momentum conservation condition for triples
                        # amplitude t3ijkabc
                        kc = kpts_helper.get_kconserv3(cell, kpts, [ki, kj, kk, ka, kb])

                        for a in range(nvir):
                            for b in range(nvir):
                                for c in range(nvir):

                                    # Form energy denominator
                                    eijkabc = (eijk - mo_energy_vir[ka][a] - mo_energy_vir[kb][b] - mo_energy_vir[kc][c])

                                    # Form connected triple excitation amplitude

                                    # First term: 1 - p(ij) - p(ik)
                                    ke = kconserv[kj, ka, kk]
                                    t3c = einsum('jke,ei->ijk', t2[kj, kk, ka, :, :, a, :], eris.oovv[ke, ki, kb, :, :, b, c].conj())
                                    ke = kconserv[ki, ka, kk]
                                    t3c = t3c - einsum('ike,ej->ijk', t2[ki, kk, ka, :, :, a, :], eris.oovv[ke, kj, kb, :, :, b, c].conj())
                                    ke = kconserv[kj, ka, ki]
                                    t3c = t3c - einsum('jie,ek->ijk', t2[kj, ki, ka, :, :, a, :], eris.oovv[ke, kk, kb, :, :, b, c].conj())

                                    km = kconserv[kb, ki, kc]
                                    t3c = t3c - einsum('mi,jkm->ijk', t2[km, ki, kb, :, :, b, c], eris.ooov[kj, kk, km, :, :, :, a])
                                    km = kconserv[kb, kj, kc]
                                    t3c = t3c + einsum('mj,ikm->ijk', t2[km, kj, kb, :, :, b, c], eris.ooov[ki, kk, km, :, :, :, a])
                                    km = kconserv[kb, kk, kc]
                                    t3c = t3c + einsum('mk,jim->ijk', t2[km, kk, kb, :, :, b, c], eris.ooov[kj, ki, km, :, :, :, a])

                                    # Second term: - p(ab) + p(ab) p(ij) + p(ab) p(ik)
                                    ke = kconserv[kj, kb, kk]
                                    t3c = t3c - einsum('jke,ei->ijk', t2[kj, kk, kb, :, :, b, :], eris.oovv[ke, ki, ka, :, :, a, c].conj())
                                    ke = kconserv[ki, ka, kk]
                                    t3c = t3c + einsum('ike,ej->ijk', t2[ki, kk, kb, :, :, b, :], eris.oovv[ke, kj, ka, :, :, a, c].conj())
                                    ke = kconserv[kj, ka, ki]
                                    t3c = t3c + einsum('jie,ek->ijk', t2[kj, ki, kb, :, :, b, :], eris.oovv[ke, kk, ka, :, :, a, c].conj())

                                    km = kconserv[ka, ki, kc]
                                    t3c = t3c + einsum('mi,jkm->ijk', t2[km, ki, ka, :, :, a, c], eris.ooov[kj, kk, km, :, :, :, b])
                                    km = kconserv[ka, kj, kc]
                                    t3c = t3c - einsum('mj,ikm->ijk', t2[km, kj, ka, :, :, a, c], eris.ooov[ki, kk, km, :, :, :, b])
                                    km = kconserv[kb, kk, kc]
                                    t3c = t3c - einsum('mk,jim->ijk', t2[km, kk, ka, :, :, a, c], eris.ooov[kj, ki, km, :, :, :, b])

                                    # Third term: - p(ac) + p(ac) p(ij) + p(ac) p(ik)
                                    ke = kconserv[kj, kc, kk]
                                    t3c = t3c - einsum('jke,ei->ijk', t2[kj, kk, kc, :, :, c, :], eris.oovv[ke, ki, kb, :, :, b, a].conj())
                                    ke = kconserv[ki, kc, kk]
                                    t3c = t3c + einsum('ike,ej->ijk', t2[ki, kk, kc, :, :, c, :], eris.oovv[ke, kj, kb, :, :, b, a].conj())
                                    ke = kconserv[kj, kc, ki]
                                    t3c = t3c + einsum('jie,ek->ijk', t2[kj, ki, kc, :, :, c, :], eris.oovv[ke, kk, kb, :, :, b, a].conj())

                                    km = kconserv[kb, ki, ka]
                                    t3c = t3c + einsum('mi,jkm->ijk', t2[km, ki, kb, :, :, b, a], eris.ooov[kj, kk, km, :, :, :, c])
                                    km = kconserv[kb, kj, ka]
                                    t3c = t3c - einsum('mj,ikm->ijk', t2[km, kj, kb, :, :, b, a], eris.ooov[ki, kk, km, :, :, :, c])
                                    km = kconserv[kb, kk, ka]
                                    t3c = t3c - einsum('mk,jim->ijk', t2[km, kk, kb, :, :, b, a], eris.ooov[kj, ki, km, :, :, :, c])

                                    full_t3c[ki, kj, kk, ka, kb, :, :, :, a, b, c] = t3c.copy()

                                    # Form disconnected triple excitation amplitude contribution
                                    t3d = np.zeros((nocc,nocc,nocc), dtype=dtype)

                                    # First term: 1 - p(ij) - p(ik)
                                    if ki == ka:
                                        t3d = t3d + einsum('i,jk->ijk', t1[ki, :, a], eris.oovv[kj, kk, kb, :, :, b, c])
                                        t3d = t3d + einsum('i,jk->ijk', fov[ki, :, a], t2[kj, kk, kb, :, :, b, c])

                                    if kj == ka:
                                        t3d = t3d - einsum('j,ik->ijk', t1[kj, :, a], eris.oovv[ki, kk, kb, :, :, b, c])
                                        t3d = t3d - einsum('j,ik->ijk', fov[kj, :, a], t2[ki, kk, kb, :, :, b, c])

                                    if kk == ka:
                                        t3d = t3d - einsum('k,ji->ijk', t1[kk, :, a], eris.oovv[kj, ki, kb, :, :, b, c])
                                        t3d = t3d - einsum('k,ji->ijk', fov[kk, :, a], t2[kj, ki, kb, :, :, b, c])

                                    # Second term: - p(ab) + p(ab) p(ij) + p(ab) p(ik)
                                    if ki == kb:
                                        t3d = t3d - einsum('i,jk->ijk', t1[ki, :, b], eris.oovv[kj, kk, ka, :, :, a, c])
                                        t3d = t3d - einsum('i,jk->ijk', fov[ki, :, b], t2[kj, kk, ka, :, :, a, c])

                                    if kj == kb:
                                        t3d = t3d + einsum('j,ik->ijk', t1[kj, :, b], eris.oovv[ki, kk, kb, :, :, a, c])
                                        t3d = t3d + einsum('j,ik->ijk', fov[kj, :, b], t2[ki, kk, kb, :, :, a, c])

                                    if kk == kb:
                                        t3d = t3d + einsum('k,ji->ijk', t1[kk, :, b], eris.oovv[kj, ki, kb, :, :, a, c])
                                        t3d = t3d + einsum('k,ji->ijk', fov[kk, :, b], t2[kj, ki, kb, :, :, a, c])

                                    # Third term: - p(ac) + p(ac) p(ij) + p(ac) p(ik)
                                    if ki == kc:
                                        t3d = t3d - einsum('i,jk->ijk', t1[ki, :, c], eris.oovv[kj, kk, kb, :, :, b, a])
                                        t3d = t3d - einsum('i,jk->ijk', fov[ki, :, c], t2[kj, kk, kb, :, :, b, a])

                                    if kj == kc:
                                        t3d = t3d + einsum('j,ik->ijk', t1[kj, :, c], eris.oovv[ki, kk, kb, :, :, b, a])
                                        t3d = t3d + einsum('j,ik->ijk', fov[kj, :, c], t2[ki, kk, kb, :, :, b, a])

                                    if kk == kc:
                                        t3d = t3d + einsum('k,ji->ijk', t1[kk, :, c], eris.oovv[kj, ki, kb, :, :, b, a])
                                        t3d = t3d + einsum('k,ji->ijk', fov[kk, :, c], t2[kj, ki, kb, :, :, b, a])

                                    t3c_plus_d = t3c + t3d
                                    t3c_plus_d /= eijkabc

                                    full_t3d[ki, kj, kk, ka, kb, :, :, :, a, b, c] = t3d.copy()

                                    energy_t += (1./36) * einsum('ijk,ijk', t3c, t3c_plus_d)
    print "Checking t3c symmetry"
    print check_antiperm_symmetry(full_t3c, 0, 1)
    print check_antiperm_symmetry(full_t3c, 0, 2)
    print check_antiperm_symmetry(full_t3c, 1, 2)
    print check_antiperm_symmetry(full_t3c, 3, 4)
    print "Checking t3d symmetry"
    print check_antiperm_symmetry(full_t3d, 0, 1)
    print check_antiperm_symmetry(full_t3d, 0, 2)
    print check_antiperm_symmetry(full_t3d, 1, 2)
    print check_antiperm_symmetry(full_t3d, 3, 4)
    print energy_t

def check_antiperm_symmetry(array, idx1, idx2, tolerance=1e-10):
    '''
    Checks whether an array with k-point symmetry has antipermutational symmetry
    with respect to switching two indices idx1, idx2.  For 2-particle arrays,
    idx1 and idx2 must be in the range [0,3], while for 3-particle arrays they
    must be in the range [0,6].

    For a 3-particle array, such as the T3 amplitude
        t3[ki, kj, kk, ka, kb, i, j, a, b, c],
    setting `idx1 = 0` and `idx2 = 1` would switch the orbital indices i, j as well
    as the kpoint indices ki, kj.
    '''
    # Checking to make sure bounds of idx1 and idx2 are O.K.
    assert(idx1 >= 0 and idx2 >= 0)
    assert(idx1 != idx2)

    array_shape_len = len(array.shape)
    nparticles = (array_shape_len + 1) / 4
    assert(idx1 < 2 * nparticles and idx2 < 2 * nparticles)

    if (nparticles > 3):
        raise NotImplementedError("Currently set up for only up to 3 particle "
                                  "arrays. Input array has %d particles.")

    kpt_idx1 = idx1
    kpt_idx2 = idx2

    # Start of the orbital index, located after k-point indices
    orb_idx1 = (2 * nparticles - 1) + idx1
    orb_idx2 = (2 * nparticles - 1) + idx2

    sign = (-1)**(abs(idx1 - idx2) + 1)
    sign = 1
    out_array_indices = np.arange(array_shape_len)

    out_array_indices[kpt_idx1], out_array_indices[kpt_idx2] = \
            out_array_indices[kpt_idx2], out_array_indices[kpt_idx1]
    out_array_indices[orb_idx1], out_array_indices[orb_idx2] = \
            out_array_indices[orb_idx2], out_array_indices[orb_idx1]
    return (np.linalg.norm(array + sign*array.transpose(out_array_indices)) <
            tolerance)

if __name__ == '__main__':
    from pyscf.pbc import gto
    from pyscf.pbc import scf
    from pyscf.pbc import cc

    cell = gto.Cell()
    cell.atom = '''
    C 0.000000000000   0.000000000000   0.000000000000
    C 1.685068664391   1.685068664391   1.685068664391
    '''
    cell.basis = 'gth-szv'
    cell.pseudo = 'gth-pade'
    cell.a = '''
    0.000000000, 3.370137329, 3.370137329
    3.370137329, 0.000000000, 3.370137329
    3.370137329, 3.370137329, 0.000000000'''
    cell.unit = 'B'
    cell.verbose = 5
    cell.mesh = [12, 12, 12]
    cell.build()

    kmf = scf.KRHF(cell, kpts=cell.make_kpts([1, 1, 1]), exxdiv=None)
    ehf = kmf.kernel()

    mycc = cc.KGCCSD(kmf)
    ecc, t1, t2 = mycc.kernel()

    kernel(mycc)
