<!-- Copyright (c) 2026 Tim Menzies, MIT License https://opensource.org/licenses/MIT -->
<a href="https://timm.fyi"><img align="right" alt="Author" src="https://img.shields.io/badge/Author-timm-dc143c?logo=readme&logoColor=white"></a><img align="right" alt="Language" src="https://img.shields.io/badge/Language-Python%203.12+-000080?logo=python&logoColor=white"><img align="right" alt="Deps" src="https://img.shields.io/badge/Deps-0-32cd32?logo=checkmarx&logoColor=white"><a href="https://choosealicense.com/licenses/mit/"><img align="right" alt="License" src="https://img.shields.io/badge/License-MIT-32cd32?logo=open-source-initiative&logoColor=white"></a><img align="right" alt="Purpose" src="https://img.shields.io/badge/Purpose-Active·Learning-7b68ee?logo=githubcopilot&logoColor=white"><br>

### [https://github.com/aiez/skape](https://github.com/aiez/skape)
skape: a multi-objective optimizer that spends labels like they are
expensive — because they are. Each level it labels a few rows,
projects the whole pool onto a FastMap line (poles = the two most
distant labelled rows, by **x**-distance, so unlabelled rows project
too), keeps the better two-thirds, and recurses. The ~50 labels it
buys then grow a tiny min-variance tree that sorts a held-out half.
One stdlib file, zero dependencies: the nuff closure it needs (typed
CSV, Sym/Num columns, distance, tree) is **inlined**.

```bash
python3 -B skape.py -file ../optimiz/auto93.csv   # -> a 0..100 win
python3 -B skape.py -budget 30 -keep 0.7          # tune any setting
```

**Sections:** [NAME](#name) | [DESIGN](#design) | [USAGE](#usage) | [SETTINGS](#settings) | [STYLE](#style) | [LICENSE](#license) | [AUTHOR](#author)

**Files:** [skape.py](#file-skape-py) | [test_skape.py](#file-test_skape-py) | [Makefile](#file-makefile) | [pyproject.toml](#file-pyproject-toml)

## NAME

    skape - a FastMap landscape active learner (stdlib only)

## DESIGN

    The loop (landscape): poles in O(2N), keep the kept side.
      label `grow` rows  ->  the worst survivors of the last cut
      project the pool   ->  (d(a,r)^2 + c^2 - d(b,r)^2) / 2c, c=d(a,b)
      drop the worst 1/3 ->  recurse until `budget` labels are spent
    Poles come only from the labels still inside the surviving
    region (local poles). Distance is root-stable: norms and goals
    are read off the whole data, so subtrees see no spurious splits.

    The yardstick (holdout): split rows in half, acquire on one half,
    grow a tree, sort the other half by the tree, check the top
    `check`, take the best by true distance, score 0..100 vs the
    data's own spread. Mean over `repeats`.

## USAGE

    python3 -B skape.py [-KEY VAL ...]
      -file F     dataset (CSV; `+`/`-`/`!` header suffix = goal/klass)
      prints      "WIN<tab>basename"  (WIN is the mean hold-out score)

    make test     # smoke tests (needs ../optimiz)
    make sh       # konfig dev shell

## SETTINGS

    seed 1234567891   grow 4     keep 0.66    budget 50
    cap  1024         check 5    leaf 3       repeats 20

    Any `-key val` on the CLI overrides; types follow the default.

## STYLE

    konfig house style (style_code.md): 2-space indent, short names,
    one-line colon bodies, python3 -B. Promoted from sand-box/far.py;
    the nuff primitives are inlined so the file stands alone.

## LICENSE

    MIT (c) 2026 Tim Menzies.

## AUTHOR

    Tim Menzies <timm@ieee.org>, https://timm.fyi
