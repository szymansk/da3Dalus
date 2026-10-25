---
canon: height-above-ground
kind: quantity
symbol: h_AGL
unit: m
role: input
status: draft
tags:
  - canon/quantity
  - module/atmosphere
  - role/input
type: scalar
positive: true
---

# Height above ground · `h_AGL`

Height of the aircraft above the ground it glides to, the starting height of the engine-out glide ([[glide-distance-from-ratio]]). **Not** the altitude of the atmosphere ([[altitude]], above mean sea level). It has no default (maintainer 2026-10-25): without a supplied value the glide distance is not computed (`missing_input`), never 0.

**Unit.** `m`

**Used by.** [[glide-distance-from-ratio]]
