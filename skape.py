#!/usr/bin/env python3 -B
"""skape.py: a FastMap landscape active learner, one stdlib file.

Acquire labels cheaply: each level, label `grow` rows, project the
pool onto a far-pole line (FastMap, by x-distance so unlabelled rows
sort too), keep the better 2/3, recurse -- until the label `budget`
runs out. Feed the labels to a min-variance tree, sort a held-out
half, check the top few, score the best (hold-out win, mean of reps).

Self-contained: the nuff closure it needs (typed csv, Sym/Num
columns, Data, distance, tree) is inlined -- no imports beyond stdlib.

 eg: python3 -B skape.py -file ../optimiz/auto93.csv
"""
import sys, random
from math import exp, log2
from types import SimpleNamespace as o
isa = isinstance
BIG, TINY = 1e32, 1e-32

# ===== nuff (minimal) =========================================
# ---- io: typed rows ------------------------------------------
def thing(s):
  "Coerce a (trimmed) string to int, float, bool, else str."
  if (s[1:] if s[:1] == "-" else s).isdigit(): return int(s)
  try: return float(s)
  except ValueError: return s=="True" or (s!="False" and s)

def csv(file, clean=lambda s: s.partition("#")[0].split(",")):
  "Yield typed, hashable rows from a CSV ('#' starts a comment)."
  with open(file, encoding="utf-8") as f:
    for line in f:
      row = [x.strip() for x in clean(line)]   # strip once, here
      if any(row):                             # skip blank/comment lines
        yield tuple(thing(x) for x in row)

def shuffle(lst, rng=random):
  "Shuffled copy via the given RNG."
  lst = lst[:]; rng.shuffle(lst); return lst

def some(lst, k=512, rng=random):
  "Up to k items sampled without replacement."
  return rng.sample(lst, min(k, len(lst)))

# ---- columns: Sym={value:count}, Num=(n,mu,m2) ---------------
Sym = dict
def Num(n=0, mu=0, m2=0): return (n, mu, m2)
def n_(x):  return x[0]
def mu_(x): return x[1]
def m2_(x): return x[2]

def sd(num):
  "Standard deviation of a Num from its m2."
  n, mu, m2 = num
  return 0 if n < 2 else (max(0, m2) / (n - 1)) ** 0.5

def welford(num, v, inc=1):
  "Num + v (inc=-1 removes); returns a new (n, mu, m2)."
  n, mu, m2 = num
  if (n := n + inc) <= 0: return Num()
  d = v - mu; mu += inc * d / n
  return n, mu, m2 + inc * d * (v - mu)

def norm(num, v):
  "Map v to 0..1 via a logistic on its z-score (Num only)."
  if v == "?": return v
  z = (v - mu_(num)) / (sd(num) + TINY)
  return 1 / (1 + exp(-1.7 * max(-3, min(3, z))))

def mix(i, j, inc=1):
  "Combine two same-type cols; inc=-1 removes j from i."
  if isa(i, Sym):
    return {k: i.get(k, 0) + inc * j.get(k, 0) for k in i | j}
  (ni, mui, m2i), (nj, muj, m2j) = i, j
  n = ni + inc * nj
  if n <= 0: return Num()
  d  = muj - mui
  mu = (ni * mui + inc * nj * muj) / n
  m2 = m2i + inc * m2j + inc * d * d * ni * nj / n
  return Num(n, mu, m2)

# ---- table: roles in Data, columns by at-index ---------------
def Data(src=None):
  "Table o(names, cols{at:col}, x, y, goal, klass, rows)."
  src = iter(src or [])
  data = o(names=[], cols={}, x=[], y=[], goal={}, klass=None, rows=[])
  roles(data, next(src, []))
  return adds(src, data)

def roles(data, names):
  "Read header names into column roles (mutates data)."
  data.names = names
  for at, s in enumerate(names):
    data.cols[at] = Num() if s[0].isupper() else Sym()
    if s[-1] == "X": continue
    if s[-1] in "+-!":
      data.y.append(at)
      data.goal[at] = s[-1] == "+"
      if s[-1] == "!": data.klass = at
    else: data.x.append(at)

def add(it, v, inc=1):
  "Add to a Sym/Num/Data; RETURNS the (new) it. Skips '?'."
  if isa(it, Sym):
    if v != "?": it[v] = it.get(v, 0) + inc
    return it
  if isa(it, tuple):                          # Num
    return welford(it, v, inc) if v != "?" else it
  (it.rows.append if inc == 1 else it.rows.remove)(v)  # row
  for at in it.cols: it.cols[at] = add(it.cols[at], v[at], inc)
  return it

def adds(src, it=None):
  "Fold src into it (a fresh Num by default); returns it."
  if it is None: it = Num()
  for v in src: it = add(it, v)
  return it

def clone(data, src=None):
  "New Data with data's columns; optionally seed src rows."
  return Data([data.names] + (src or []))

def mid(col):
  "Central tendency: mode (Sym) or mean (Num)."
  return max(col, key=col.get) if isa(col, Sym) else mu_(col)

def spread(col):
  "Diversity: entropy (Sym) or stdev (Num)."
  if not isa(col, Sym): return sd(col)        # Num
  n = sum(col.values())
  return -sum(c/n * log2(c/n) for c in col.values() if c)   # 0*log0 = 0

# ---- distance ------------------------------------------------
def minkowski(vals, p=2):
  "Aggregate per-item distances via the p-norm."
  total, n = 0, 0
  for v in vals: total += v ** p; n += 1
  return (total / (n or 1)) ** (1 / p)

def disty(data, row, **kw):
  "Distance of a row to the best goals (0 = ideal)."
  return minkowski(
    (abs(norm(data.cols[at], row[at]) - data.goal[at])
     for at in data.y if row[at] != "?"), **kw)

def distx(data, r1, r2, **kw):
  "Distance between two rows over the x-columns."
  return minkowski((gap(data.cols[at], r1[at], r2[at])
                    for at in data.x), **kw)

def gap(col, u, v):
  "Distance between two values of one column (0..1)."
  if u == v == "?": return 1
  if isa(col, Sym): return u != v
  u, v = norm(col, u), norm(col, v)
  if u == "?": u = 1 if v < 0.5 else 0
  if v == "?": v = 1 if u < 0.5 else 0
  return abs(u - v)

# ---- tree: min-impurity binary tree (regression or classify) -
def has(v, lo, hi): return v == "?" or lo <= v <= hi

def _impurity(col):
  "Split cost: a Num's sum-of-squares, or a Sym's entropy*count."
  return m2_(col) if isa(col, tuple) else spread(col) * sum(col.values())

def _separate(data, rows, y, Y=Num):
  "Yield each (score, at, lo, hi, yes, no, n) split candidate; Y=y-col kind."
  ys = {r: y(r) for r in rows}             # cache y per (hashable) row
  for at in data.x:
    sym = isa(data.cols[at], Sym)
    rs  = sorted((r for r in rows if r[at] != "?"), key=lambda r: r[at])
    tot = Y()
    for r in rs: tot = add(tot, ys[r])
    yes, run, run_n = Y(), Y(), 0           # distinct objs: Sym add mutates in place
    for k, r in enumerate(rs):
      run = add(run, ys[r]); run_n += 1
      if k+1 < len(rs) and rs[k+1][at] == r[at]: continue   # only cut at boundaries
      if sym: grp, n = run, run_n
      else:   grp, n = (yes := mix(yes, run)), k+1
      run = Y(); run_n = 0
      no  = mix(tot, grp, -1)
      lo  = r[at] if sym else -BIG
      yield _impurity(grp) + _impurity(no), at, lo, r[at], grp, no, n

def treeCut(data, rows, y, leaf=3, Y=Num):
  "The (at, lo, hi) of the lowest-impurity cut, or None."
  ok = (c for c in _separate(data, rows, y, Y) if c[6] >= leaf)
  best = min(ok, key=lambda c: c[0], default=None)
  return best and best[1:4]

def tree(data, rows=None, y=None, leaf=3, lvl=0, maxDepth=12, Y=Num):
  """Min-impurity binary tree; yes=match. Y=Num+y=disty -> regression
  (leaf mu=mean); Y=Sym+y=class label -> classification (leaf mu=mode)."""
  rows = data.rows if rows is None else rows
  y    = y or (lambda r: disty(data, r))
  yc   = adds((y(r) for r in rows), Y())
  what = lambda a: Num() if isa(data.cols[a], tuple) else Sym()
  ymid = [mid( adds( (r[a] for r in rows), what(a))) for a in data.y]
  t = o(at=None, mu=mid(yc), n=len(rows), ymid=ymid)
  if len(rows) >= 2*leaf and lvl < maxDepth and _impurity(yc) > 0 and \
     (cut := treeCut(data, rows, y, leaf, Y)):   # stop on a pure node
    at, lo, hi = cut
    yes, no = [], []
    for r in rows:                                # one pass
      (yes if has(r[at], lo, hi) else no).append(r)
    if len(yes) >= leaf and len(no) >= leaf:
      t.at, t.lo, t.hi, t.yes = at, lo, hi, True   # go left on match
      t.left  = tree(data, yes, y, leaf, lvl+1, maxDepth, Y)
      t.right = tree(data, no,  y, leaf, lvl+1, maxDepth, Y)
  return t

def treePredict(t, row):
  "Walk a tree to a leaf; return its value (disty mean / class mode)."
  while t.at is not None:                        # yes-side = left
    t = t.left if has(row[t.at], t.lo, t.hi) == t.yes else t.right
  return t.mu

# ===== skape: the landscape learner ===========================
the = o(seed=1234567891, grow=4, keep=0.66, budget=50, cap=1024,
        check=5, leaf=3, repeats=20, file="../optimiz/auto93.csv")

def memo(fn):
  "Cache fn(row) by value; return (lookup fn, its cache dict)."
  cache = {}
  def f(r):
    if r not in cache: cache[r] = fn(r)
    return cache[r]
  return f, cache

def project(rows, d, y):
  "FastMap poles O(2N), west=better; return a projection key fn."
  far = lambda r: max(rows, key=lambda z: d(z, r))
  east = far(rows[0]); west = far(east)
  if y(east) < y(west): east, west = west, east     # west = better
  c = d(east, west) + TINY
  return lambda r: (d(east, r)**2 + c*c - d(west, r)**2) / (2*c)

def landscape(data):
  "Each level: label grow worst-survivors; poles from local labels."
  d = lambda r1, r2: distx(data, r1, r2)
  y, ys = memo(lambda r: disty(data, r))     # ys: labelled-row cache
  pool = shuffle(data.rows)
  while len(ys) < the.budget - the.grow and len(pool) >= 2*the.leaf:
    lab, k = [], 0
    for r in pool:                           # one pass: poles = survivors
      if r in ys: lab.append(r)
      elif k < the.grow: y(r); lab.append(r); k += 1
    n = max(1, int((1-the.keep)*len(pool)))   # drop >=1 so pool shrinks
    pool = sorted(pool, key=project(lab, d, y))[n:]
  return list(ys)

def wins(data):
  ys = sorted(disty(data, r) for r in data.rows)
  ten = len(ys)//10
  lo, med, sd = ys[0], ys[5*ten], (ys[9*ten] - ys[ten])/2.56
  def f(row):
    v = disty(data, row)
    if v < lo + 0.35*sd: v = lo
    return max(-100, int(100*(1 - (v-lo)/(med-lo + TINY))))
  return f

def pick(hold, score, full):
  "Sort hold by model, check top `check`, best by true disty."
  return min(sorted(hold, key=score)[:the.check],
             key=lambda r: disty(full, r))

def holdout(data):
  win, out = wins(data), Num()
  for _ in range(the.repeats):
    rows = some(data.rows, the.cap)
    h = len(rows)//2
    d, hold = clone(data, rows[:h]), rows[h:]
    t = tree(d, landscape(d))
    best = pick(hold, lambda r: treePredict(t, r), data)
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
