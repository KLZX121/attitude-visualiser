import pyvista as pv
import numpy as np
import json

from types import SimpleNamespace

def read_attitude_data(filepath) -> np.ndarray:
  # formatted as a n x 4 csv
  q_list = np.loadtxt(filepath, delimiter=',')

  # compute dcms
  dcm_list = []

  def q_to_dcm(q):
    # convert to dcm
    qs = q[0]
    qv = q[1:]

    def skew(v):
      return np.array([
        [0, -v[2], v[1]],
        [v[2], 0, -v[0]],
        [-v[1], v[0], 0]
      ])

    dcm = (qs**2 - np.linalg.norm(qv)**2)*np.eye(3) - 2*qs*skew(qv) + 2*np.outer(qv, qv)
    return dcm
  
  for q in q_list:
    # input quaternion (scalar first, shuster/JPL convention)
    q = q / np.linalg.norm(q)

    dcm = q_to_dcm(q)
    dcm_list.append(dcm)

  return dcm_list

def read_geometry_data(filepath, return_type=None):
  try:
    with open(filepath, 'r') as f:
      data = json.load(f, object_hook=lambda d: SimpleNamespace(**d))

      if return_type == 'v':
      # return a list of vertices
        vertices = []

        for surf in data.surfaces:
          vertices.extend(surf.vertices)

        vertices = np.array(vertices)
        return vertices
      else:
      # return json object (SimpleNamespace)
        return data
  except FileNotFoundError:
    print(f'The file \'{filepath}\' could not be found. Make sure your file is named and placed correctly.')
    return None


class Frame:
  def __init__(self, frame_name, cols=('red', 'green', 'blue'), labels=('x', 'y', 'z'), opacity=1):
    self.frame_name = frame_name
    self.cols = cols
    self.labels = labels
    self.opacity = opacity

    self.arrow_actor = [None, None, None]
   
  def setup(self, basis_vecs, plotter) -> None:
    for i in range(3):
      arrow = pv.Arrow(direction=basis_vecs[i], shaft_radius=0.04, tip_length=0.2)
      self.arrow_actor[i] = plotter.add_mesh(arrow, color=self.cols[i], label=self.labels[i], opacity=self.opacity, name=f'{self.frame_name}_{i}')

  def rotate_mesh(self, A):  
    # rotate using transpose of attitude (body -> ref)
    for i in range(3):
      self.arrow_actor[i].rotation_from(A.T)