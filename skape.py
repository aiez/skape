#!/usr/bin/env python3 -B
import sys, os
from math import exp
from bisect import bisect_right
from random import random as rand, sample, seed
from types import SimpleNamespace as o
isa = isinstance
BIG, TINY = 1e32, 1e-32

def doot(p=os.path.dirname(os.path.abspath(__file__))):
  if d := os.environ.get("DOOT"): return d   # gists root; see konfig/style_gist.md
  while p != os.path.dirname(p):             # else climb for a konfig/ sibling
    if os.path.isdir(p + "/konfig"): return p
    p = os.path.dirname(p)
  return ".."                                # last-resort bootstrap default

DOOT = doot()

the = o(seed=1234567891, grow=4, keep=0.66, budget=50, cap=1024,
        check=5, leaf=3, repeats=20, eps=0.1, maxd=4, fast=100,

        slow=10, few=6, pos=0, file=DOOT + "/optimiz/auto93.csv")

#-- cols -------------------------------------------------------
Sym = dict
def Num(n=0, mu=0, m2=0): return (n, mu, m2)
def mu_(x): return x[1]

def sd(num):
  n, mu, m2 = num
  return 0 if n < 2 else (max(0, m2) / (n-1)) ** 0.5

def welford(num, v, inc=1):
  n, mu, m2 = num
  if (n := n + inc) <= 0: return Num()
  d = v - mu; mu += inc * d / n
  return n, mu, m2 + inc * d * (v - mu)

def norm(num, v):
  if v == "?": return v
  z = (v - mu_(num)) / (sd(num) + TINY)
  return 1 / (1 + exp(-1.7 * max(-3, min(3, z))))

#-- Data -------------------------------------------------------
def Data(src=None):
  src = iter(src or [])
  data = o(names=next(src), cols={}, x=[], y=[], goal={},
           klass=None, protect=[], rows=[])
  return adds(src, roles(data))

def roles(data):
  for at, s in enumerate(data.names):
    data.cols[at] = Num() if s[0].isupper() else Sym()
    if s[-1] == "X": continue
    if s[-1] == "~": data.protect.append(at); continue   # held aside
    if s[-1] in "+-!":
      data.y.append(at); data.goal[at] = s[-1] == "+"
      if s[-1] == "!": data.klass = at
    else: data.x.append(at)
  return data

def add(i, v, inc=1):
  if isa(i, o):
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

#-- dist -------------------------------------------------------
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


#-- sample ------------------------------------------------------
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
  while len(ys) < the.budget-the.grow and len(pool)>=2*the.leaf:
    lab, k = [], 0
    for r in pool:
      if r in ys: lab.append(r)
      elif k < the.grow: y(r); lab.append(r); k += 1
    n = max(1, int((1-the.keep)*len(pool)))
    pool = sorted(pool, key=project(lab, d, y))[n:]
  return sorted(ys, key=y)

#-- bands -------------------------------------------------------
def has(v, lo, hi): return v == "?" or lo <= v <= hi
def F(xs, v): return bisect_right(xs, v) / len(xs)

def splits(b, r, lo=-BIG, hi=BIG, d=0):
  cut = [v for v in b + r if lo < v < hi]
  v = max(cut, key=lambda v: abs(F(b, v)-F(r, v)), default=None)
  if v is None or abs(F(b,v)-F(r,v)) < the.eps or d >= the.maxd:
    yield lo,hi,(F(b,hi) - F(b,lo)) - (F(r,hi) - F(r,lo)); return
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

#-- rules -------------------------------------------------------
def esample(bnd, k):
  key = lambda x:rand()**(1 / (abs(x[0]) or TINY))
  return sorted(bnd, key=key)[-k:]

def rule(sub):
  g={}
  for w,at,lo,hi in sub: g[at] = g.get(at,[]) + [(lo,hi)]
  return g

def selects(g, row):
  return all(any(has(row[at], lo, hi) for lo, hi in v) 
             for at, v in g.items())

def learn(data, lab, split, cost):      # w: sum-weights filter, rescore on lab
  bnd= [x for x in bands(data, *split(data, lab)) if abs(x[0]) >= 0.05]
  lst= [esample(bnd, 1+int(rand()*5)) for _ in range(the.fast)]
  top= sorted(lst,key=lambda s: -sum(w for w,*_ in s))[:the.slow]
  return rule(min(top, key=lambda s: cost(data, lab, rule(s))))

def holdout(data, prep, split, cost, score):
  out = []
  for _ in range(the.repeats):
    rows = shuffle(data.rows)
    h = len(rows)//2
    lab = prep(data, rows[:h])
    g = learn(data, lab, split, cost)
    out.append(score(data, g, rows[h:]))
  return out

def wins(data):
  ys = sorted(disty(data, r) for r in data.rows)
  ten = len(ys)//10
  lo, med, sd = ys[0], ys[5*ten], (ys[9*ten] - ys[ten])/2.56
  def f(row):
    v = disty(data, row)
    if v < lo + 0.35*sd: v = lo
    return max(-100, int(100*(1 - (v-lo)/(med-lo + TINY))))
  return f

def edges(lab, key):
  lab = sorted(lab, key=key)
  return lab[:the.few], lab[-the.few:]

def meanof(rows, y): 
  return mu_(adds(map(y, rows))) if rows else BIG

def chosen(g, test, y):                 # the rule's pick: best of check selected
  return min(some([r for r in test if selects(g,r)] or test, the.check), key=y)

def rskape(data):
  win = wins(data)
  y = lambda r: disty(data, r)
  return holdout(data,
    lambda d,tr: landscape(clone(d, some(tr, the.cap))),
    lambda d,lab: edges(lab, y),
    lambda d,lab,g: meanof([r for r in lab if selects(g,r)], y),
    lambda d,g,test: win(chosen(g, test, y)))

def metrics(data, g, rows, pos):        # rule as classifier -> pd,pf,prec,spd
  got  = [selects(g, r) for r in rows]
  want = [r[data.klass] == pos for r in rows]
  tp = sum(w and h for w,h in zip(want,got))
  fp = sum((not w) and h for w,h in zip(want,got))
  fn = sum(w and not h for w,h in zip(want,got)); tn = len(rows)-tp-fp-fn
  pd, pf = tp/(tp+fn+TINY), fp/(fp+tn+TINY); prec = tp/(tp+fp+TINY)
  spd = 0                               # max selection-rate gap, sym groups
  for at in data.protect:
    if not isa(data.cols[at], Sym): continue
    grp = {}
    for r, h in zip(rows, got): grp[r[at]] = grp.get(r[at], []) + [h]
    rate = [sum(v)/len(v) for v in grp.values()]
    if rate: spd = max(spd, max(rate)-min(rate))
  return pd, pf, prec, spd

def d2h(m): pd, pf, prec, spd = m; return minkowski([1-pd, pf, 1-prec, spd])

def cskape(data):                       # -> (d2h, pd, pf, prec, spd) per rep
  k, pos = data.klass, the.pos
  return holdout(data,
    lambda d,tr: some(tr, the.cap),     # labels free: just sample
    lambda d,lab: ([r for r in lab if r[k]==pos],
                   [r for r in lab if r[k]!=pos]),
    lambda d,lab,g: d2h(metrics(d, g, lab, pos)),
    lambda d,g,test: (lambda m: (d2h(m), *m))(metrics(d, g, test, pos)))

# -- MAP-Elites: illuminate the recall x pf grid (best d2h per cell) -
def colvals(data, best, rest):          # at -> (sorted best vals, sorted rest)
  cv = {}
  for at in data.x:
    if not isa(data.cols[at], Sym):
      b = sorted(r[at] for r in best if r[at] != "?")
      r = sorted(r[at] for r in rest if r[at] != "?")
      if len(b) > 2 and r: cv[at] = (b, r)
  return cv

def randcut(cv):                        # random range on a numeric col, with w
  at = sample(list(cv), 1)[0]; b, r = cv[at]; n = len(b)
  i, j = sorted([int(rand()*(n+1)), int(rand()*(n+1))])
  lo = -BIG if i == 0 else b[i-1]; hi = BIG if j >= n else b[j]
  return (F(b,hi)-F(b,lo)) - (F(r,hi)-F(r,lo)), at, lo, hi

def elites(data, pos, seeds=800, iters=12000, G=14):
  rows = some(data.rows, the.cap)
  best = [r for r in rows if r[data.klass]==pos]
  rest = [r for r in rows if r[data.klass]!=pos]
  cv, pool = colvals(data, best, rest), list(bands(data, best, rest))
  draw = lambda: randcut(cv) if (cv and rand()<.6) else sample(pool, 1)[0]
  def mutate(sub):
    s = sub[:]
    if len(s) > 1 and rand() < .35: s.pop(int(rand()*len(s)))
    elif rand() < .7: s.append(draw())
    else: s[int(rand()*len(s))] = draw()
    return s
  arch = {}
  def place(sub):
    m = metrics(data, rule(sub), rows, pos); dh = d2h(m)
    c = (min(G-1,int(m[0]*G)), min(G-1,int(m[1]*G)))
    if c not in arch or dh < arch[c][0]: arch[c] = (dh, sub, m)
  for _ in range(seeds): place([draw() for _ in range(1+int(rand()*3))])
  for _ in range(iters): place(mutate(arch[sample(list(arch),1)[0]][1]))
  return arch                           # cell -> (d2h, sub, (pd,pf,prec,spd))


#-- plumbing ----------------------------------------------------
def thing(s):
  if (s[1:] if s[:1] == "-" else s).isdigit(): return int(s)
  try: return float(s)
  except ValueError: 
    return s == "True" or (s != "False" and s)

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

def pcts(xs):
  xs = sorted(xs)
  return " ".join(f"{xs[int(p/100*len(xs))]:>4}"
                  for p in (10,30,50,70,90))

#-- main -------------------------------------------------------
def main():
  print(f"{pcts(rskape(Data(csv(the.file))))}",end=" ")
  print(f"{the.file.split('/')[-1][:-4]}")

def test__the():  print(the)
def test__csv():  [print(r) for r in csv(the.file)]
def test__data(): main()
def test__class():                      # cskape d2h percentiles (low=good)
  xs = sorted(r[0] for r in cskape(Data(csv(the.file))))
  s = " ".join(f"{xs[int(p/100*len(xs))]:5.2f}" for p in (10,30,50,70,90))
  print(f"{s}  {the.file.split('/')[-1][:-4]}")

if __name__ == "__main__":
  for k, v in zip(sys.argv, sys.argv[1:]):
    if hasattr(the, k[2:]): setattr(the, k[2:], thing(v))
  for k in sys.argv:
    seed(the.seed)
    if fn := vars().get('test__' + k[2:]): fn()
