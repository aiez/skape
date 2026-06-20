#!/usr/bin/env python3 -B
"""forest.py: a stable FFT forest over unsupervised background cuts.

Built on skape's landscape learner. Per rep: split a pool train/test;
landscape acquires <=50 labels on train; discretize the WHOLE train
pool unsupervised (Sym->value, Num->16 logistic-CDF bins) = the
background. Then grow 32 attribute-bagged depth-4 binary trees on the
~50 labels, using only background cuts, scoring splits by ENTROPY of
the y-bins (so Num and Sym sit on one scale -- no m2-vs-entropy). Fan
each tree to <=16 FFTs, keep the lowest-median-leaf-d2h one; min over
the 32; sort test by it; top-`check` win. Mean over `repeats`.

Rule learner sees every X value, but y only for the locally-labelled.

 eg: python3 -B forest.py -file ../optimiz/auto93.csv   (needs skape.py)
"""
import sys, random
from statistics import median
import skape as S
from skape import (o, isa, Sym, Num, add, csv, Data, disty, norm,
                   spread, some, clone, wins, pick, landscape)

the = S.the
the.trees, the.attrs, the.depth = 32, 0.75, 4   # forest knobs
the.nbins, the.ybins, the.guard = 16, 16, 2

# ---- unsupervised discretization (the "background") ----------
def cutid(col, v):
  "Bin v: a Sym's value, or 1 of nbins logistic-CDF bins (Num)."
  if v == "?" or isa(col, Sym): return v
  return min(the.nbins-1, int(the.nbins * norm(col, v)))

def ybin(y): return min(the.ybins-1, int(the.ybins * y))

def ent(ys):
  "Entropy of the y-bins of a list of disty values."
  c = Sym()
  for y in ys: add(c, ybin(y))
  return spread(c)

def labelled(data, rows):
  "Each labelled row -> (ids{at:cutid}, disty); ids use background cols."
  return [({at: cutid(data.cols[at], r[at]) for at in data.x}, disty(data, r))
          for r in rows]

# ---- grow one attribute-bagged binary tree -------------------
def bestcut(data, items, attrs, leaf):
  "Lowest entropy split (at, k, sym, yes, no) over the sampled attrs."
  best = None
  for at in attrs:
    sym = isa(data.cols[at], Sym)
    ks  = sorted({ids[at] for ids, _ in items if ids[at] != "?"})
    for k in (ks if sym else ks[:-1]):           # Num: drop the top bin
      yes = [it for it in items
             if it[0][at] != "?" and (it[0][at] == k if sym else it[0][at] <= k)]
      no  = [it for it in items if it not in yes]
      if len(yes) >= leaf and len(no) >= leaf:
        s = (len(yes)*ent([y for _, y in yes])
             + len(no)*ent([y for _, y in no])) / len(items)
        if best is None or s < best[0]: best = (s, at, k, sym, yes, no)
  return best

def grow(data, items, attrs, depth):
  "Binary tree; every node carries its median d2h (mu) and n."
  ys = [y for _, y in items]
  t = o(at=None, mu=median(ys), n=len(items))
  if depth > 0 and len(items) >= 2*the.leaf:
    if cut := bestcut(data, items, attrs, the.leaf):
      _, at, k, sym, yes, no = cut
      t.at, t.k, t.sym = at, k, sym
      t.left  = grow(data, yes, attrs, depth-1)
      t.right = grow(data, no,  attrs, depth-1)
  return t

# ---- fan a tree into FFTs; keep the best ---------------------
def ffts(t):
  "Each level, one child exits as a leaf -> the 2^depth FFTs."
  if t.at is None:
    yield t
  else:
    for yes in (False, True):                    # which child exits
      ex, cont = (t.left, t.right) if yes else (t.right, t.left)
      lf = o(at=None, mu=ex.mu, n=ex.n)
      for rest in ffts(cont):
        yield o(at=t.at, k=t.k, sym=t.sym, yes=yes, left=lf, right=rest)

def leafmin(f):
  "The lowest median-d2h leaf of an FFT (leaves with n>=guard)."
  ms, t = [], f
  while t.at is not None: ms.append(t.left); t = t.right
  ms.append(t)
  ms = [lf.mu for lf in ms if lf.n >= the.guard]
  return min(ms) if ms else 1e32

def forest(data, items):
  "32 attribute-bagged trees -> the single best FFT (lowest leaf d2h)."
  m, best = max(1, int(the.attrs*len(data.x))), None
  for _ in range(the.trees):
    f = min(ffts(grow(data, items, some(data.x, m), the.depth)), key=leafmin)
    if best is None or leafmin(f) < leafmin(best): best = f
  return best

# ---- predict (X-cuts only) + holdout win ---------------------
def predict(data, f, row):
  "Walk an FFT to a leaf via background cuts; return its median d2h."
  while f.at is not None:
    v  = cutid(data.cols[f.at], row[f.at])
    go = True if v == "?" else (v == f.k if f.sym else v <= f.k)
    f  = f.left if go == f.yes else f.right
  return f.mu

def holdout(data):
  win, out = wins(data), Num()
  for _ in range(the.repeats):
    rows = some(data.rows, the.cap)
    h = len(rows)//2
    d, test = clone(data, rows[:h]), rows[h:]
    items = labelled(d, landscape(d))            # <=50 labels, bg = train pool
    f = forest(d, items)
    best = pick(test, lambda r: predict(d, f, r), data)
    out = add(out, win(best))
  return out[1]

def main():
  data = Data(csv(the.file))
  print(f"{holdout(data):.0f}\t{the.file.split('/')[-1]}")

if __name__ == "__main__":
  for f, v in zip(sys.argv, sys.argv[1:]):
    if f[:1] == "-" and (k := f[1:]) in vars(the):
      old = getattr(the, k)
      setattr(the, k, v if isinstance(old, str) else type(old)(v))
  random.seed(the.seed)
  main()
