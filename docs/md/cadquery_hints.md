# Cadquery Beispiele

Setze eine Workplane an einen Punkt in der Welt
```
x, y, z = (10, 20, 30)

# workplane normal in World (0,-1,0) 
cq.Workplane('XZ').workplane(offset=-y, origin=cq.Vector(x, y, z))

# workplane normal in World (0,1,0)
cq.Workplane('XZ').workplane(offset=y, invert=True, origin=cq.Vector(x, y, z))

# workplane normal in World (0,0,1) 
cq.Workplane('XY').workplane(offset=z, origin=cq.Vector(x, y, z))

# workplane normal in World (0,0,-1)
cq.Workplane('XY').workplane(offset=-z, invert=True, origin=cq.Vector(x, y, z))
```