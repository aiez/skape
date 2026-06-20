#!/usr/bin/env python3 -B
"""test_skape.py: smoke tests (needs ../optimiz/auto93.csv).

  python3 -B test_skape.py
"""
import random
import skape as S

F = "../optimiz/auto93.csv"

def test_data():
  "csv loads typed, hashable rows; columns get roles."
  d = S.Data(S.csv(F))
  assert len(d.rows) == 398 and len(d.y) == 3
  assert isinstance(d.rows[0], tuple)          # hashable

def test_dist():
  "disty in 0..1, self-distx 0, distx symmetric."
  d = S.Data(S.csv(F)); a, b = d.rows[0], d.rows[1]
  assert 0 <= S.disty(d, a) <= 1
  assert S.distx(d, a, a) == 0
  assert abs(S.distx(d, a, b) - S.distx(d, b, a)) < 1e-9

def test_landscape():
  "acquires ~budget labels, all from the data."
  d = S.Data(S.csv(F))
  lab = S.landscape(d)
  assert S.the.budget - 2*S.the.grow <= len(lab) <= S.the.budget
  assert all(r in d.rows for r in lab)

def test_tree():
  "tree over the labels predicts a disty mean in 0..1."
  d = S.Data(S.csv(F))
  t = S.tree(d, S.landscape(d))
  assert 0 <= S.treePredict(t, d.rows[0]) <= 1

def test_holdout():
  "the hold-out win score is a sane 0..100."
  assert 0 <= S.holdout(S.Data(S.csv(F))) <= 100

if __name__ == "__main__":
  fails = 0
  for name, fn in sorted(vars().items()):
    if name.startswith("test_"):
      random.seed(S.the.seed)
      try: fn(); print("ok  ", name)
      except Exception as e: fails += 1; print("FAIL", name, e)
  raise SystemExit(fails)
