#!/usr/bin/env python3 -B
"""test_skape.py: smoke tests (needs the optimiz sibling gist).

  python3 -B test_skape.py
"""
import random
import skape as S

F = S.the.file                                 # DOOT-routed auto93.csv default

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
  "acquires <=budget labels, all from the data, sorted best-first."
  d = S.Data(S.csv(F))
  lab = S.landscape(d)
  assert 0 < len(lab) <= S.the.budget
  assert all(r in d.rows for r in lab)
  ys = [S.disty(d, r) for r in lab]
  assert ys == sorted(ys)

def test_learn():
  "rule learner over the labels selects a nonempty subset."
  d = S.Data(S.csv(F))
  y = lambda r: S.disty(d, r)
  g = S.learn(d, S.landscape(d),
              lambda d, lab: S.edges(lab, y),
              lambda d, lab, g: S.meanof([r for r in lab if S.selects(g, r)], y))
  assert g and all(isinstance(v, list) for v in g.values())
  assert any(S.selects(g, r) for r in d.rows)

def test_holdout():
  "rskape: one win score per repeat, each a sane -100..100."
  xs = S.rskape(S.Data(S.csv(F)))
  assert len(xs) == S.the.repeats
  assert all(-100 <= x <= 100 for x in xs)

if __name__ == "__main__":
  fails = 0
  for name, fn in sorted(vars().items()):
    if name.startswith("test_"):
      random.seed(S.the.seed)
      try: fn(); print("ok  ", name)
      except Exception as e: fails += 1; print("FAIL", name, e)
  raise SystemExit(fails)
