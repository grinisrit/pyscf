#!/usr/bin/env python
# Copyright 2014-2018 The PySCF Developers. All Rights Reserved.
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

import unittest
import numpy
from pyscf import gto
from pyscf import lib
from pyscf import dft

def setUpModule():
    global mol, method, mol1
    mol = gto.Mole()
    mol.verbose = 7
    mol.output = '/dev/null'
    mol.atom = [[2, (0.,0.,0.)], ]
    mol.basis = {"He": 'cc-pvdz'}
    mol.build()
    method = dft.RKS(mol)

    mol1 = gto.Mole()
    mol1.verbose = 0
    mol1.output = None
    mol1.atom = 'He'
    mol1.basis = 'cc-pvdz'
    mol1.charge = 1
    mol1.spin = 1
    mol1.build()

def tearDownModule():
    global mol, method, mol1
    mol.stdout.close()
    del mol, method, mol1


class KnownValues(unittest.TestCase):
    def test_nr_lda(self):
        method.xc = 'lda, vwn_rpa'
        self.assertAlmostEqual(method.scf(), -2.8641551904776055, 9)

    def test_dks_lda(self):
        m = mol.DKS()
        self.assertAlmostEqual(m.kernel(), -2.8268242330361373, 9)

        m = mol.DKS().x2c()
        self.assertAlmostEqual(m.kernel(), -2.826788817256218, 9)

    def test_udks_lda(self):
        m = dft.dks.UDKS(mol)
        self.assertAlmostEqual(m.kernel(), -2.8268242330361373, 9)

        m = dft.dks.UDKS(mol).x2c()
        self.assertAlmostEqual(m.kernel(), -2.826788817256218, 9)

    def test_nr_pw91pw91(self):
        method.xc = 'pw91, pw91'
        self.assertAlmostEqual(method.scf(), -2.8914066724838849, 9)

    def test_nr_b88vwn(self):
        method.xc = 'b88, vwn'
        self.assertAlmostEqual(method.scf(), -2.9670729652962606, 9)

    def test_nr_xlyp(self):
        method.xc = 'xlyp'
        self.assertAlmostEqual(method.scf(), -2.9045738259332161, 9)

    def test_nr_b3lypg(self):
        method.xc = 'b3lypg'
        self.assertAlmostEqual(method.scf(), -2.9070540942168002, 9)

        m = mol.UKS()
        m.xc = 'b3lyp'
        self.assertAlmostEqual(m.scf(), -2.89992555753, 9)

    def test_nr_lda_1e(self):
        mf = dft.RKS(mol1).run()
        self.assertAlmostEqual(mf.e_tot, -1.936332393935281, 9)

    def test_nr_b3lypg_1e(self):
        mf = dft.ROKS(mol1).set(xc='b3lypg').run()
        self.assertAlmostEqual(mf.e_tot, -1.9931564410562266, 9)

    def test_xcfun_nr_blyp(self):
        m = mol.RKS()
        m._numint.libxc = dft.xcfun
        m.xc = 'b88,lyp'
        self.assertAlmostEqual(m.scf(), -2.8978518405, 9)

    def test_nr_m06l(self):
        m = mol.RKS()
        m.xc = 'm06l'
        self.assertAlmostEqual(m.scf(), -2.9039230673864243, 9)

        m = mol.UKS()
        m.xc = 'm06l'
        self.assertAlmostEqual(m.scf(), -2.9039230673864243, 9)

if __name__ == "__main__":
    print("Full Tests for He")
    unittest.main()
