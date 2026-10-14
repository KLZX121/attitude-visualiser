import numpy as np
import json
from types import SimpleNamespace

N = 5
M = 5

with open('./geometry.json', 'r') as f:
  geometry = json.load(f, object_hook=lambda d: SimpleNamespace(**d))

  surfaces = []
  for main_surf in geometry.surfaces:
    P1 = np.array(main_surf.vertices[0])
    a = main_surf.vertices[1] - P1
    b = main_surf.vertices[3] - P1

    p = lambda i, j: P1 + (i/N)*a + (j/M)*b

    for i in range(0, N):
      for j in range(0, M):
        p1 = p(i, j)
        p2 = p(i+1, j)
        p3 = p(i+1, j+1)
        p4 = p(i, j+1)

        subSurf = {
          'vertices': [p1.tolist(), p2.tolist(), p3.tolist(), p4.tolist()],
          'area': 0.5*np.linalg.norm(np.cross(p3-p1, p4-p2)),
          'centroid': ((p1+p2+p3+p4)/4).tolist(),
          'normal': main_surf.normal,
          'Cd': main_surf.Cd,
          'Ca': main_surf.Ca,
          'Crs': main_surf.Crs,
          'Crd': main_surf.Crd
        }

        surfaces.append(subSurf)

  new_geometry = {
    'n_surfaces': N*M*geometry.n_surfaces,
    'surfaces': surfaces
  }

  with open('geometry.json', 'w') as f:
    json.dump(new_geometry, f)