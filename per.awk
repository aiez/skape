# per.awk: print the 10,30,50,70,90th percentiles of column c
# (default 1). gawk only (uses asort).
#   ... | gawk -v c=3 -f per.awk      # c=3 -> skape median column
BEGIN { if (!c) c = 1 }
{ a[NR] = $c }
END { n = asort(a)
      for (p = 10; p <= 90; p += 20) {
        i = int(p/100 * n)
        printf "p%-2d %s\t", p, a[i ? i : 1] }
      print "" }
