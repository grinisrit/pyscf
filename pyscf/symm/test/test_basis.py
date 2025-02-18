#!/usr/bin/env python
# Copyright 2014-2020 The PySCF Developers. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Author: Qiming Sun <osirpt.sun@gmail.com>
#

import unittest
import numpy
from pyscf import gto
from pyscf import symm

def get_so(atoms, basis, cart=False):
    atoms = gto.mole.format_atom(atoms)
    gpname, origin, axes = symm.detect_symm(atoms)
    gpname, axes = symm.subgroup(gpname, axes)
    atoms = gto.mole.format_atom(atoms, origin, axes, 'Bohr')
    mol = gto.M(atom=atoms, basis=basis, unit='Bohr', spin=None)
    mol.cart = cart
    so = symm.basis.symm_adapted_basis(mol, gpname)[0]
    n = 0
    for c in so:
        if c.size > 0:
            n += c.shape[1]
    assert n == mol.nao_nr()
    return n, so


class KnowValues(unittest.TestCase):
    def test_symm_orb_h2o(self):
        atoms = [['O' , (1. , 0.    , 0.   ,)],
                 [1   , (0. , -.757 , 0.587,)],
                 [1   , (0. , 0.757 , 0.587,)] ]
        basis = {'H': gto.basis.load('cc_pvqz', 'C'),
                 'O': gto.basis.load('cc_pvqz', 'C'),}
        self.assertEqual(get_so(atoms,basis  )[0], 165)
        self.assertEqual(get_so(atoms,basis,1)[0], 210)

    def test_symm_orb_d2h(self):
        atoms = [[1, (0., 0., 0.)],
                 [1, (1., 0., 0.)],
                 [1, (0., 1., 0.)],
                 [1, (0., 0., 1.)],
                 [1, (-1, 0., 0.)],
                 [1, (0.,-1., 0.)],
                 [1, (0., 0.,-1.)]]
        basis = {'H': gto.basis.load('cc_pvqz', 'C'),}
        self.assertEqual(get_so(atoms,basis  )[0], 385)
        self.assertEqual(get_so(atoms,basis,1)[0], 490)

    def test_symm_orb_c2v(self):
        atoms = [[1, (1., 0., 2.)],
                 [2, (0., 1., 0.)],
                 [1, (-2.,0.,-1.)],
                 [2, (0.,-1., 0.)]]
        basis = {'H' : gto.basis.load('cc_pvqz', 'C'),
                 'He': gto.basis.load('cc_pvqz', 'C'),}
        self.assertEqual(get_so(atoms,basis)[0], 220)

    def test_symm_orb_c2h(self):
        atoms = [[1, (1., 0., 2.)],
                 [2, (0., 1., 0.)],
                 [1, (-1.,0.,-2.)],
                 [2, (0.,-1., 0.)]]
        basis = {'H' : gto.basis.load('cc_pvqz', 'C'),
                 'He': gto.basis.load('cc_pvqz', 'C'),}
        self.assertEqual(get_so(atoms,basis  )[0], 220)
        self.assertEqual(get_so(atoms,basis,1)[0], 280)

        atoms = [[1, (1., 0., 1.)],
                 [1, (1., 0.,-1.)],
                 [2, (0., 0., 2.)],
                 [2, (2., 0.,-2.)],
                 [3, (1., 1., 0.)],
                 [3, (1.,-1., 0.)]]
        basis = {'H' : gto.basis.load('cc_pvqz', 'C'),
                 'He': gto.basis.load('cc_pvqz', 'C'),
                 'Li': gto.basis.load('cc_pvqz', 'C'),}
        self.assertEqual(get_so(atoms,basis  )[0], 330)
        self.assertEqual(get_so(atoms,basis,1)[0], 420)

    def test_symm_orb_d2(self):
        atoms = [[1, (1., 0., 1.)],
                 [1, (1., 0.,-1.)],
                 [2, (0., 0., 2.)],
                 [2, (2., 0., 2.)],
                 [2, (1., 1.,-2.)],
                 [2, (1.,-1.,-2.)]]
        basis = {'H' : gto.basis.load('cc_pvqz', 'C'),
                 'He': gto.basis.load('cc_pvqz', 'C'),}
        self.assertEqual(get_so(atoms,basis  )[0], 330)
        self.assertEqual(get_so(atoms,basis,1)[0], 420)

    def test_symm_orb_ci(self):
        atoms = [[1, ( 1., 0., 0.)],
                 [2, ( 0., 1., 0.)],
                 [3, ( 0., 0., 1.)],
                 [4, ( .5, .5, .5)],
                 [1, (-1., 0., 0.)],
                 [2, ( 0.,-1., 0.)],
                 [3, ( 0., 0.,-1.)],
                 [4, (-.5,-.5,-.5)]]
        basis = {'H' : gto.basis.load('cc_pvqz', 'C'),
                 'He': gto.basis.load('cc_pvqz', 'C'),
                 'Li': gto.basis.load('cc_pvqz', 'C'),
                 'Be': gto.basis.load('cc_pvqz', 'C'),}
        self.assertEqual(get_so(atoms,basis)[0], 440)

    def test_symm_orb_cs(self):
        atoms = [[1, (1., 0., 2.)],
                 [2, (1., 0., 0.)],
                 [3, (2., 0.,-1.)],
                 [4, (0., 0., 1.)]]
        basis = {'H' : gto.basis.load('cc_pvqz', 'C'),
                 'He': gto.basis.load('cc_pvqz', 'C'),
                 'Li': gto.basis.load('cc_pvqz', 'C'),
                 'Be': gto.basis.load('cc_pvqz', 'C'),}
        self.assertEqual(get_so(atoms,basis)[0], 220)

    def test_symm_orb_c1(self):
        atoms = [[1, ( 1., 0., 0.)],
                 [2, ( 0., 1., 0.)],
                 [3, ( 0., 0., 1.)],
                 [4, ( .5, .5, .5)]]
        basis = {'H' : gto.basis.load('cc_pvqz', 'C'),
                 'He': gto.basis.load('cc_pvqz', 'C'),
                 'Li': gto.basis.load('cc_pvqz', 'C'),
                 'Be': gto.basis.load('cc_pvqz', 'C'),}
        self.assertEqual(get_so(atoms,basis)[0], 220)

    def test_symm_orb_c3v_as_cs(self):
        atoms = [['Fe', ( 0.000000  , 0.000000  , 0.015198 )],
                 ['C',  ( 0.000000  , 0.000000  , -1.938396)],
                 ['C',  ( 0.000000  , -1.394127 , -1.614155)],
                 ['C',  ( -1.207349 , 0.697064  , -1.614155)],
                 ['C',  ( 1.207349  , 0.697064  , -1.614155)],
                 ['H',  ( -0.922915 , -1.965174 , -1.708739)],
                 ['H',  ( 0.922915  , -1.965174 , -1.708739)],
                 ['H',  ( -1.240433 , 1.781855  , -1.708739)],
                 ['H',  ( -2.163348 , 0.183319  , -1.708739)],
                 ['H',  ( 2.163348  , 0.183319  , -1.708739)],
                 ['H',  ( 1.240433  , 1.781855  , -1.708739)],
                 ['C',  ( 0.000000  , 1.558543  , 0.887110 )],
                 ['C',  ( 1.349738  , -0.779272 , 0.887110 )],
                 ['C',  ( -1.349738 , -0.779272 , 0.887110 )],
                 ['O',  ( 0.000000  , 2.572496  , 1.441607 )],
                 ['O',  ( 2.227847  , -1.286248 , 1.441607 )],
                 ['O',  ( -2.227847 , -1.286248 , 1.441607 )],]
        basis = {'Fe':gto.basis.load('def2svp', 'C'),
                 'C': gto.basis.load('def2svp', 'C'),
                 'H': gto.basis.load('def2svp', 'C'),
                 'O': gto.basis.load('def2svp', 'C'),}
        n, so = get_so(atoms, basis)
        self.assertEqual([c.shape[1] for c in so], [134, 104])

    def test_symm_orb_so3(self):
        atoms = [['Si', (0, 0, 0)]]
        basis = {'Si': gto.basis.load('ccpvtz', 'Si')}
        n, so = get_so(atoms, basis)
        idx, idy = numpy.where(numpy.hstack(so) != 0)
        self.assertEqual(idy.argsort().tolist(),
                         [0,1,2,3,4,6,9,12,15,7,10,13,16,5,8,11,14,17,22,18,23,19,24,20,25,21,26,27,28,29,30,31,32,33])


if __name__ == "__main__":
    print("Full Tests symm.basis")
    unittest.main()
