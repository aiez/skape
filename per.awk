# per.awk: print the 10,30,50,70,90th percentiles of a column of
# numbers (one per line). gawk only (uses asort).
#   ... | gawk -f per.awk
{ a[NR] = $1 }
END { n = asort(a)
      for (p = 10; p <= 90; p += 20) {
        i = int(p/100 * n)
        printf "p%-2d %s\t", p, a[i ? i : 1] }
      print "" }
