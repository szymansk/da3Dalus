# The graph at cluster level

> Each box is a calculation domain; each arrow is *at least one quantity* computed in one
> domain and consumed in another. These crossings are where a defect travels furthest and
> where a fachlicher test has the most to say.

```mermaid
flowchart LR
  c0["aero-polars<br/>113 nodes"]
  c1["aero-spanwise<br/>103 nodes"]
  c2["aero-strips<br/>128 nodes"]
  c3["mass<br/>51 nodes"]
  c4["perf-envelope<br/>105 nodes"]
  c5["perf-matching<br/>92 nodes"]
  c6["perf-oppoints<br/>81 nodes"]
  c7["powertrain<br/>166 nodes"]
  c8["stability<br/>146 nodes"]
  c9["structure<br/>127 nodes"]
  c1 -- "6" --> c9
  c8 -- "2" --> c3
  c6 -- "1" --> c0
  c9 -- "1" --> c1
  c9 -- "1" --> c3
  c3 -- "1" --> c9
```

## Reading it

An arrow from **mass** to **performance** means a mass quantity feeds a performance one:
a wrong component-tree roll-up moves every published speed. That is the kind of statement
the graph is for — and the kind a unit test on either side alone cannot make.

Per-cluster detail: [[_index-aero-polars|aero-polars]] · [[_index-aero-spanwise|aero-spanwise]] · [[_index-aero-strips|aero-strips]] · [[_index-mass|mass]] · [[_index-perf-envelope|perf-envelope]] · [[_index-perf-matching|perf-matching]] · [[_index-perf-oppoints|perf-oppoints]] · [[_index-powertrain|powertrain]] · [[_index-stability|stability]] · [[_index-structure|structure]]

Mechanical observations across the whole corpus: [[findings]].
