import pyvista as pv
import numpy as np
import json

from types import SimpleNamespace

def read_state_data(filepath, i_q, i_r, i_v) -> tuple[list[float], list[float], list[float]]:
  # formatted as a n(t) x n(x) json
  x_list = []
  with open(filepath, 'r') as f:
    json_str = json.load(f)
    x_list = np.array(json_str)

  # compute dcms

  dcm_list = []
  r_list = []
  v_list = []
  for x in x_list:
    # quaternion (scalar first, shuster/JPL convention)
    q = x[i_q[0]:i_q[1]]
    q = q / np.linalg.norm(q)

    dcm = q_to_dcm(q)
    dcm_list.append(dcm)

    # orbital position (ECI)
    if i_r and max(i_r) <= len(x):
      r = x[i_r[0]:i_r[1]]
      r_list.append(r)

    # orbital velocity (ECI)
    if i_v and max(i_v) <= len(x):
      v =x[i_v[0]:i_v[1]]
      v_list.append(v)

  return dcm_list, r_list, v_list

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

def read_surface_data(filepath) -> SimpleNamespace:
  try:
    with open(filepath, 'r') as f:
      data = json.load(f, object_hook=lambda d: SimpleNamespace(**d))
      return data
  except FileNotFoundError:
    print(f'The file \'{filepath}\' could not be found. Make sure your file is named and placed correctly.')

  return None

def read_r_sun_data(filepath) -> list[list[float]]:
  try:
    with open(filepath, 'r') as f:
      data = json.load(f)
      return data
  except FileNotFoundError:
    print(f'The file \'{filepath}\' could not be found. Make sure your file is named and placed correctly.')
    
  return None


def get_lvlh(r, v) -> np.ndarray:
  # lvlh is defined as z towards earth, y towards negative orbit normal, x completing triad

  ur = r / np.linalg.norm(r)
  uv = v / np.linalg.norm(v)

  e_z = -ur
  e_y = np.cross(e_z, uv)
  e_y /= np.linalg.norm(e_y)

  e_x = np.cross(e_y, e_z)
  e_x /= np.linalg.norm(e_x)

  A = np.array([e_x, e_y, e_z])
  A = A

  return A

class Axes:
  def __init__(self, frame_name, cols=('orange_red', 'green', 'blue'), labels=('x', 'y', 'z'), opacity=1):
    self.frame_name = frame_name
    self.cols = cols
    self.labels = labels
    self.opacity = opacity

    self.arrow_actors = [None, None, None]
    self.label_actor = None
   
  def setup(self, basis_vecs, scale, plotter) -> None:
    for i in range(3):
      arrow = pv.Arrow(direction=basis_vecs[i], shaft_radius=0.04, tip_length=0.2, scale=scale)
      self.arrow_actors[i] = plotter.add_mesh(
        arrow, 
        color=self.cols[i], 
        label=self.labels[i], 
        opacity=self.opacity, 
        name=f'{self.frame_name}_{self.labels[i]}',
        ambient=0.5,
        diffuse=0.5
      )

    # create axes labels
    self.label_points_local = (scale * basis_vecs)*1.1
    self.label_points = pv.PolyData(self.label_points_local.copy())
    self.label_points.point_data["label"] = [
      actor.name for actor in self.arrow_actors
    ]
    self.label_actor = plotter.add_point_labels(
      points=self.label_points,
      labels="label",
      show_points=False,
      shape_opacity=0,
      font_family='courier',
      font_size=int(scale*50),
      background_color='white',
      background_opacity=0.2,
      justification_horizontal='center',
      justification_vertical='center'
    )

  def rotate_mesh(self, A, show_labels): 
    # rotate using transpose of attitude (body -> ref)
    for i in range(3):
      self.arrow_actors[i].rotation_from(A.T)

    # positions of arrow tips for placing labels
    if show_labels:
      tip_pts = (A @ self.label_points_local.T)
      self.label_points.points = tip_pts

  def toggle_visibility(self, show_axes, show_labels):
    for actor in self.arrow_actors:
      actor.visibility = show_axes

    if show_axes:
      self.label_actor.visibility = show_labels
    else:
      self.label_actor.visibility = False

class Body:
  def __init__(self, geometry):
    self.geometry = geometry

    self.surf_actors = []
    self.norm_actors = []
    self.force_actors = []

  def setup(self, plotter, show_normals, add_force_actors=False, show_forces=False):
    for surface_obj in self.geometry.surfaces:
      # convert vertex data to PolyData
      vertices = pv.PolyData(surface_obj.vertices)
      # use delaunay triangulation to create surface mesh from vertices
      surface_mesh = vertices.delaunay_2d()

      mesh_col = None
      """ if 'x_pos' in surface_obj.name:
        mesh_col = 'yellow' """
      
      surf_actor = plotter.add_mesh(
        surface_mesh,
        color=mesh_col,
        ambient=0.05,
        diffuse=0.8,
        specular=0.5,
      )
      self.surf_actors.append(surf_actor)

      normal_mesh = pv.Arrow(start=surface_obj.centroid, direction=surface_obj.normal, scale=0.03)
      arrow_col = None
      if '_x_'in surface_obj.name:
        arrow_col = 'red'
      elif '_y_' in surface_obj.name:
        arrow_col = 'green'
      elif '_z_' in surface_obj.name:
        arrow_col = 'blue'
        
      norm_actor = plotter.add_mesh(normal_mesh, color=arrow_col, lighting=False)
      self.norm_actors.append(norm_actor)
      norm_actor.visibility = show_normals

      # surface force actors
      if add_force_actors:
        force_mesh = pv.Arrow(start=(-1, 0, 0), direction=(1, 0, 0), tip_resolution=10, shaft_resolution=10)
        force_actor = plotter.add_mesh(force_mesh, color='red', lighting=False)
        force_actor.scale = 0
        self.force_actors.append(force_actor)
        force_actor.visibility = show_forces

  def toggle_visibility(self, show_surf, show_norms, show_forces):
    for actor in self.surf_actors:
      actor.visibility = show_surf
    for actor in self.norm_actors:
      if not show_surf:
        actor.visibility = False
      else:
        actor.visibility = show_norms
    for actor in self.force_actors:
      if not show_surf:
        actor.visibility = False
      else:
        actor.visibility = show_forces

  def rotate_mesh(self, dcm):
    for actor in self.surf_actors + self.norm_actors + self.force_actors:
      actor.rotation_from(dcm.T)

  def update_forces(self, surface_forces, dcm, scale_factor):    
    forces = surface_forces.a.f
    summed_forces = [np.linalg.norm(f) for f in forces]

    for i, force_actor in enumerate(self.force_actors):
      f = summed_forces[i]
      uf = [0, 0, 0]
      if f: uf = surface_forces.a.f[i] / f

      actor_scale = f * scale_factor

      force_actor.scale = actor_scale
      force_actor.position = self.surf_actors[i].center

      # rotate in direction of uf
      if any(uf):
        rot = pv.Transform().rotate_vector(np.cross([1, 0, 0], uf), np.degrees(np.arccos(np.dot([1, 0, 0], uf))))
        force_actor.rotation_from(dcm.T @ rot.rotation_matrix)


class Earth:
  def __init__(self):
    self.actor = None

  def setup(self, r, dist, radius, plotter):
    self.radius = radius

    earth_mesh = pv.examples.planets.load_planet(radius=self.radius)
    earth_texture = pv.examples.load_globe_texture()

    self.actor = plotter.add_mesh(
      earth_mesh,
      texture=earth_texture,
      smooth_shading=True,
      ambient=0.1
    )
    self.update_position(r, dist)

  def update_position(self, r, dist):
    # r is eci -> satellite
    # convert to unit direction and transform to satellite -> eci
    self.u = -r / np.linalg.norm(r)
    self.actor.position = self.u*self.radius*dist

  def toggle_visibility(self):
    self.actor.visibility = not self.actor.visibility


class Sun:
  def __init__(self):
    self.actor = None
    self.sun_light = None

  def setup(self, r, dist, radius, plotter):
    self.radius = radius
    sun_mesh = pv.examples.planets.load_planet(radius=self.radius)
    self.actor = plotter.add_mesh(sun_mesh, color='yellow', lighting=False)

    # add lighting
    self.sun_light = pv.Light(
      position=self.actor.position,
      focal_point=(0, 0, 0),
      light_type='scenelight',
      intensity=1,
    )

    plotter.add_light(self.sun_light)

    self.update_position(r, dist)
    self.set_scene_lights(plotter)

  def update_position(self, r, dist):
    # r is satellite -> sun
    # convert to unit direction
    self.u = r / np.linalg.norm(r)
    self.actor.position = self.u*self.radius*dist

    self.sun_light.position = self.actor.position

  def toggle_visibility(self, plotter):
    self.actor.visibility = not self.actor.visibility

    # toggle sun lighting
    if self.actor.visibility:
      self.sun_light.switch_on()
    else:
      self.sun_light.switch_off()

    self.set_scene_lights(plotter)

  def set_scene_lights(self, plotter):
    # turn off scene lights if sun is lighting
    for light in plotter.renderer.lights:
      if light is not self.sun_light:
        if self.actor.visibility:
          light.switch_off()
        else:
          light.switch_on()
        


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