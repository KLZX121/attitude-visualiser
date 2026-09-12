# generates the vertices for a spacecraft composed of rectangular plates
# centre of mass is always at (0, 0, 0)

import numpy as np
import json

# cubesat base structure surface vertices
# default is a 3U
# units in m
def gen_cubesat(Lx=0.1, Ly=0.1, Lz=0.3405, gen_solar_panels=True, solar_panel_height=0.1):
  # vertices
  vert = [
    [1, 1, 1],
    [1, -1, 1],
    [-1, -1, 1],
    [-1, 1, 1],
    [1, 1, -1],
    [1, -1, -1],
    [-1, -1, -1],
    [-1, 1, -1]
  ] @ np.diag([Lx/2, Ly/2, Lz/2])
  # convert from np array back to python list
  vert = vert.tolist()

  surfaces = []

  # body faces
  z_pos = vert[0:4]
  z_neg = vert[4:8]

  x_pos = [vert[0], vert[1], vert[5], vert[4]]
  x_neg = [vert[7], vert[6], vert[2], vert[3]]

  y_pos = [vert[0], vert[4], vert[7], vert[3]]
  y_neg = [vert[5], vert[1], vert[2], vert[6]]

  surfaces = [
    z_pos,
    z_neg,
    x_pos,
    x_neg,
    y_pos,
    y_neg
  ]

  # solar panel surface vertices
  # assumes two longitudinally deployed panels on the +x face
  if gen_solar_panels:
    panel_y_pos = [vert[0], vert[4]]
    panel_y_pos += (np.array(panel_y_pos) + [0, solar_panel_height, 0]).tolist()[::-1]

    panel_y_neg = [vert[1], vert[5]]
    panel_y_neg += (np.array(panel_y_neg) - [0, solar_panel_height, 0]).tolist()[::-1]

    surfaces.extend([panel_y_pos, panel_y_neg])

  return surfaces


# write data to json file
def write_json(surfaces, names):
  surface_objs = []

  for i, surf in enumerate(surfaces):
    surf_obj = {
      'name': names[i],
      'vertices': surf
    }

    surface_objs.append(surf_obj)

  data = {
    'surfaces': surface_objs
  }

  with open('geometry.json', 'w') as f:
    json.dump(data, f)

write_json(gen_cubesat(), ['body_z_pos', 'body_z_neg', 'body_x_pos', 'body_x_neg', 'body_y_pos', 'body_y_neg', 'panel_y_pos', 'panel_y_neg'])