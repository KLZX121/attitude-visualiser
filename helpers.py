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

def read_geometry_data(filepath, return_type=None) -> np.ndarray | SimpleNamespace | None:
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


class Axes:
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

  def toggle_visibility(self):
    for actor in self.arrow_actor:
      actor.visibility = not actor.visibility

class Body:
  def __init__(self, geometry):
    self.geometry = geometry

    self.actors = []

  def setup(self, plotter, show_centroids, show_normals):
    for surface_obj in self.geometry.surfaces:
      # convert vertex data to PolyData
      vertices = pv.PolyData(surface_obj.vertices)
      # use delaunay triangulation to create surface mesh from vertices
      surface_mesh = vertices.delaunay_2d()

      mesh_col = None
      if 'panel' in surface_obj.name or 'x_pos' in surface_obj.name:
        mesh_col = 'yellow'
      
      surf_actor = plotter.add_mesh(surface_mesh, color=mesh_col)
      self.actors.append(surf_actor)

      if show_centroids:
        centroid_mesh = pv.Sphere(radius=0.003, center=surface_obj.centroid)
        cent_actor =  plotter.add_mesh(centroid_mesh, color='white')
        self.actors.append(cent_actor)


      if show_normals:
        normal_mesh = pv.Arrow(start=surface_obj.centroid, direction=surface_obj.normal, scale=0.03)
        arrow_col = None
        if '_x_'in surface_obj.name:
          arrow_col = 'red'
        elif '_y_' in surface_obj.name:
          arrow_col = 'green'
        elif '_z_' in surface_obj.name:
          arrow_col = 'blue'
        
        norm_actor = plotter.add_mesh(normal_mesh, color=arrow_col)
        self.actors.append(norm_actor)

    # scale actors
    for actor in self.actors:
      actor.scale = (5, 5, 5)

  def toggle_visibility(self):
    for actor in self.actors:
      actor.visibility = not actor.visibility

  def rotate_mesh(self, dcm):
    for actor in self.actors:
      actor.rotation_from(dcm.T)