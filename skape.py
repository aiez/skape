#!/usr/bin/env python3 -B
import sys
from math import exp, log2
from bisect import bisect_right
from random import random as rand, sample, seed
from types import SimpleNamespace as o
isa = isinstance
BIG, TINY = 1e32, 1e-32

the = o(seed=1234567891, grow=4, keep=0.66, budget=50, cap=1024,
       check=5, leaf=3, repeats=20, eps=0.1, maxd=4,
       file="../optimiz/auto93.csv")

# --- cols ------------------------------------------------------
Sym = dict
def Num(n=0, mu=0, m2=0): return (n, mu, m2)
def n_(x):  return x[0]
def mu_(x): return x[1]
def m2_(x): return x[2]

def sd(num):
  n,mu,m2 = num; return 0 if n<2 else (max(0,m2) / (n-1)) ** 0.5

def welford(num, v, inc=1):
  n, mu, m2 = num
  if (n := n + inc) <= 0: return Num()
  d = v - mu; mu += inc * d / n
  return n, mu, m2 + inc * d * (v - mu)

def norm(num, v):
  if v == "?": return v
  z = (v - mu_(num)) / (sd(num) + TINY)
  return 1 / (1 + exp(-1.7 * max(-3, min(3, z))))

def mix(i, j, inc=1):
  if isa(i, Sym):
    return {k: i.get(k, 0) + inc * j.get(k, 0) for k in i | j}
  (ni, mui, m2i), (nj, muj, m2j) = i, j
  n = ni + inc * nj
  if n <= 0: return Num()
  d  = muj - mui
  mu = (ni * mui + inc * nj * muj) / n
  m2 = m2i + inc * m2j + inc * d * d * ni * nj / n
  return Num(n, mu, m2)

def mid(col):
  return max(col, key=col.get) if isa(col, Sym) else mu_(col)

def mids(data):
  row = data.mid or [mid(data.cols[c]) for c in data.cols]
  return row

def spread(col):
  if not isa(col, Sym): return sd(col)
  n = sum(col.values())
  return -sum(c/n * log2(c/n) for c in col.values() if c)

# --- data ------------------------------------------------------
def Data(src=None):
  src = iter(src or [])
  data = o(names=next(src), cols={}, x=[], y=[], goal={},
          klass=None, rows=[], mid=None)
  return adds(src, roles(data))

def roles(data):
  for at, s in enumerate(data.names):
    data.cols[at] = Num() if s[0].isupper() else Sym()
    if s[-1] == "X": continue
    if s[-1] in "+-!":
      data.y.append(at)
      data.goal[at] = s[-1] == "+"
      if s[-1] == "!": data.klass = at
    else: data.x.append(at)
  return data

def add(i, v, inc=1):
  if isa(i, o):                          
    i.mid = None
    (i.rows.append if inc == 1 else i.rows.remove)(v)
    for at in i.cols: i.cols[at] = add(i.cols[at], v[at], inc)
    return i
  if v == "?": return i                 
  if isa(i, Sym): i[v] = i.get(v, 0) + inc; return i
  return welford(i, v, inc)            

def adds(src, i=None):
  if i is None: i = Num()
  for v in src: i = add(i, v)
  return i

def clone(data, src=[]): return Data([data.names] + src)

# --- dist ---------------------------------------------------
def minkowski(vals, p=2):
  total, n = 0, 0
  for v in vals: total += v ** p; n += 1
  return (total / (n or 1)) ** (1 / p)

def disty(data, row, **kw):
  return minkowski(
    (abs(norm(data.cols[at], row[at]) - data.goal[at])
     for at in data.y if row[at] != "?"), **kw)

def distx(data, r1, r2, **kw):
  return minkowski((gap(data.cols[at], r1[at], r2[at])
                    for at in data.x), **kw)

def gap(col, u, v):
  if u == v == "?": return 1
  if isa(col, Sym): return u != v
  u, v = norm(col, u), norm(col, v)
  if u == "?": u = 1 if v < 0.5 else 0
  if v == "?": v = 1 if u < 0.5 else 0
  return abs(u - v)

# --- project ---------------------------------------------------
def project(rows, d, y):
  far = lambda r: max(rows, key=lambda z: d(z, r))
  east = far(rows[0]); west = far(east)
  if y(east) < y(west): east, west = west, east
  c = d(east, west) + TINY
  return lambda r: (d(east, r)**2 + c*c - d(west, r)**2) / (2*c)

def landscape(data):
  d = lambda r1, r2: distx(data, r1, r2)
  y, ys = memo(lambda r: disty(data, r))
  pool = shuffle(data.rows)
  while len(ys) < the.budget - the.grow and len(pool) >= 2*the.leaf:
    lab, k = [], 0
    for r in pool:
      if r in ys: lab.append(r)
      elif k < the.grow: y(r); lab.append(r); k += 1
    n = max(1, int((1-the.keep)*len(pool)))
    pool = sorted(pool, key=project(lab, d, y))[n:]
  return sorted(list(ys), key=y)

# --- ranges ----------------------------------------------------
def has(v, lo, hi): return v == "?" or lo <= v <= hi
def F(xs, v): return bisect_right(xs, v) / len(xs)

def splits(b, r, lo=-BIG, hi=BIG, d=0):
  cut = [v for v in b + r if lo < v < hi]
  v = max(cut, key=lambda v: abs(F(b,v)-F(r,v)), default=None)
  if v is None or abs(F(b,v)-F(r,v)) < the.eps or d >= the.maxd:
    yield lo, hi, (F(b,hi)-F(b,lo)) - (F(r,hi)-F(r,lo)); return
  yield from splits(b, r, lo, v, d+1)
  yield from splits(b, r, v, hi, d+1)

def bands(data, best, rest):
  nb, nr = len(best), len(rest)
  for at in data.x:
    if isa(data.cols[at], Sym):
      fb, fr = Sym(), Sym()
      for row in best: add(fb, row[at])
      for row in rest: add(fr, row[at])
      for v in fb | fr:
        yield fb.get(v,0)/nb - fr.get(v,0)/nr, at, v, v
    else:
      b = sorted(row[at] for row in best if row[at] != "?")
      r = sorted(row[at] for row in rest if row[at] != "?")
      if b and r:
        for lo, hi, w in splits(b, r): yield w, at, lo, hi

def esample(bnd, k):                            # weighted, no replacement
  return sorted(bnd, key=lambda x: rand()**(1/(abs(x[0]) or TINY)))[-k:]

def rule(sub):                                  # subset -> {at:[(lo,hi)]}
  g = {}
  for w, at, lo, hi in sub: g.setdefault(at, []).append((lo, hi))
  return g

def selects(g, row):                            # all(any( -- a DNF rule
  return all(any(has(row[at], lo, hi) for lo, hi in v)
             for at, v in g.items())

# --- lib -------------------------------------------------------
def thing(s):
  if (s[1:] if s[:1] == "-" else s).isdigit(): return int(s)
  try: return float(s)
  except ValueError: return s=="True" or (s!="False" and s)

def csv(file, clean=lambda s: s.partition("#")[0].split(",")):
  with open(file, encoding="utf-8") as f:
    for line in f:
      row = [x.strip() for x in clean(line)]
      if any(row): yield tuple(thing(x) for x in row)

def shuffle(lst)    : return sample(lst, len(lst))
def some(lst, k=512): return sample(lst, min(k, len(lst)))

def memo(fn):
  cache = {}
  def f(r):
    if r not in cache: cache[r] = fn(r)
    return cache[r]
  return f, cache

# --- run -------------------------------------------------------
def wins(data):
  ys = sorted(disty(data, r) for r in data.rows)
  ten = len(ys)//10
  lo, med, sd = ys[0], ys[5*ten], (ys[9*ten] - ys[ten])/2.56
  def f(row):
    v = disty(data, row)
    if v < lo + 0.35*sd: v = lo
    return max(-100, int(100*(1 - (v-lo)/(med-lo + TINY))))
  return f

def pick(lst, sorter,final):
  return max(sorted(lst, key=sorter)[:the.check], key=final)

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

# --- main -------------------------------------------------------
def main():
  data = Data(csv(the.file))
  print(f"{holdout(data):.0f}\t{the.file.split('/')[-1]}")

def test__the(): print(the) 
def test__csv(): 
  for row in csv(the.file): print(row)

def test__data(): 
  d   = Data(csv(the.file))
  win = wins(d)
  num = Num()
  for _ in range(20):
    rows = shuffle(d.rows)
    n = len(rows)//2
    train,test = rows[:n],rows[n:]
    lab   = clone(d, landscape(clone(d, some(train,2048))))
    best,rest = clone(d,lab.rows[:the.grow]), clone(d,lab.rows[-the.grow:])
    order = lambda r: distx(lab,r,mids(best)) - distx(lab,r,mids(rest))
    best  = pick(test, order, win)
    num   = add(num, win(best))
  print(int(mu_(num)))

def test__ranges():
  d = Data(csv(the.file))
  lab = landscape(clone(d, some(d.rows, the.cap)))
  t = len(lab)//3
  best, rest = lab[:t], lab[-t:]
  fmt = lambda v: "-inf" if v==-BIG else "inf" if v==BIG else f"{v:g}"
  for w, at, lo, hi in sorted(bands(d, best, rest), key=lambda x: -abs(x[0])):
    rng = fmt(lo) if lo==hi else f"{fmt(lo):>8} .. {fmt(hi)}"
    print(f"{w:+.2f}  {d.names[at]:14} {rng}")

def _rules(d, n=300):                            # (a sum-w, b mean-disty) pairs
  lab = landscape(clone(d, some(d.rows, the.cap)))
  t = len(lab)//3
  bnd = [b for b in bands(d, lab[:t], lab[-t:]) if abs(b[0]) >= 0.05]
  ab = []
  for _ in range(n):
    sub = esample(bnd, 1 + int(rand()*5))        # random rule, 1..5 ranges
    sel = [r for r in lab if selects(rule(sub), r)]
    if len(sel) >= 3:                            # gate noisy tiny selections
      a = sum(w for w, *_ in sub)
      ab.append((a, sum(disty(d, r) for r in sel)/len(sel)))
  return ab

def pearson(ab):
  xs = [a for a, _ in ab]; ys = [b for _, b in ab]
  mx, my = sum(xs)/len(xs), sum(ys)/len(ys)
  cov = sum((a-mx)*(b-my) for a, b in ab)
  return cov / ((sum((a-mx)**2 for a in xs)*sum((b-my)**2 for b in ys))**.5 + TINY)

def test__rules():                               # batch-friendly: r<tab>name
  ab = _rules(Data(csv(the.file)))
  print(f"{pearson(ab):+.3f}\t{the.file.split('/')[-1]}")

def test__plot():                                # single dataset -> rules.png
  ab = _rules(Data(csv(the.file))); r = pearson(ab)
  import matplotlib; matplotlib.use("Agg")
  import matplotlib.pyplot as plt
  plt.scatter([a for a,_ in ab], [b for _,b in ab], s=8, alpha=.5)
  plt.xlabel("(a) sum of range weights"); plt.ylabel("(b) mean disty selected")
  plt.title(f"{the.file.split('/')[-1]}  r={r:+.2f}  n={len(ab)}")
  plt.savefig("rules.png", dpi=110, bbox_inches="tight"); print("wrote rules.png", r)

if __name__ == "__main__":
  for k, v in zip(sys.argv, sys.argv[1:]):
    if hasattr(the,k[2:]): setattr(the,k[2:],thing(v))
  for k in sys.argv:
    seed(the.seed)
    if fun := vars().get('test__' + k[2:]): fun()

"""
def has(v, lo, hi): return v == "?" or lo <= v <= hi

def _impurity(col):
  return m2_(col) if isa(col, tuple) else spread(col) * sum(col.values())

def _separate(data, rows, y, Y=Num):
  ys = {r: y(r) for r in rows}
  for at in data.x:
    sym = isa(data.cols[at], Sym)
    rs  = sorted((r for r in rows if r[at] != "?"), key=lambda r: r[at])
    tot = Y()
    for r in rs: tot = add(tot, ys[r])
    yes, run, run_n = Y(), Y(), 0
    for k, r in enumerate(rs):
      run = add(run, ys[r]); run_n += 1
      if k+1 < len(rs) and rs[k+1][at] == r[at]: continue
      if sym: grp, n = run, run_n
      else:   grp, n = (yes := mix(yes, run)), k+1
      run = Y(); run_n = 0
      no  = mix(tot, grp, -1)
      lo  = r[at] if sym else -BIG
      yield _impurity(grp) + _impurity(no), at, lo, r[at], grp, no, n

def treeCut(data, rows, y, leaf=3, Y=Num):
  ok = (c for c in _separate(data, rows, y, Y) if c[6] >= leaf)
  best = min(ok, key=lambda c: c[0], default=None)
  return best and best[1:4]

def tree(data, rows=None, y=None, leaf=3, lvl=0, maxDepth=12, Y=Num):
  rows = data.rows if rows is None else rows
  y    = y or (lambda r: disty(data, r))
  yc   = adds((y(r) for r in rows), Y())
  what = lambda a: Num() if isa(data.cols[a], tuple) else Sym()
  ymid = [mid( adds( (r[a] for r in rows), what(a))) for a in data.y]
  t = o(at=None, mu=mid(yc), n=len(rows), ymid=ymid)
  if len(rows) >= 2*leaf and lvl < maxDepth and _impurity(yc) > 0 and \
     (cut := treeCut(data, rows, y, leaf, Y)):
    at, lo, hi = cut
    yes, no = [], []
    for r in rows:
      (yes if has(r[at], lo, hi) else no).append(r)
    if len(yes) >= leaf and len(no) >= leaf:
      t.at, t.lo, t.hi, t.yes = at, lo, hi, True
      t.left  = tree(data, yes, y, leaf, lvl+1, maxDepth, Y)
      t.right = tree(data, no,  y, leaf, lvl+1, maxDepth, Y)
  return t

def treePredict(t, row):
  while t.at is not None:
    t = t.left if has(row[t.at], t.lo, t.hi) == t.yes else t.right
  return t.mu

"""
