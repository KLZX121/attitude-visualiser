import sys
import time
import pyvista as pv
import numpy as np
from pathlib import Path

from helpers import *
from config import OPT
from ui import setup_controls

from pyvistaqt import QtInteractor
from qtpy.QtCore import QSettings
from qtpy.QtWidgets import *


class MainWindow(QMainWindow):
  user_interacting = False

  def __init__(self):
    super().__init__()

    self.setWindowTitle('Attitude Visualiser v1.2')
    self.resize(OPT.WINDOW_SIZE[0], OPT.WINDOW_SIZE[1])

    self.setup_window(read_data=False)

  def setup_window(self, read_data):
    output('Setting up window')

    persistent_settings = QSettings('AttitudeVisualiser', 'AttitudeVisualiser')
    # load persistent settings
    for name in OPT.PERSISTENT_SETTINGS:
      default = getattr(OPT, name)
      if persistent_settings.contains(name):
        setattr(OPT, name, persistent_settings.value(name, default, type=type(default)))


    self.N_FRAMES = 1

    # read data
    if read_data:
      output('Reading data')

      self.dcm_list, self.r_list, self.v_list = read_state_data(OPT.filepath / OPT.FILENAME_STATE, OPT.I_Q, OPT.I_R, OPT.I_V)

      if self.dcm_list:
        self.N_FRAMES = len(self.dcm_list)
        OPT.FILE_AVAILABLE = True
      else:
        OPT.FILE_AVAILABLE = False
        output(f'The file: \'{OPT.filepath / OPT.FILENAME_STATE}\' could not be found.')

      if self.r_list and self.v_list:
        OPT.EARTH_AVAILABLE = True
      else:
        OPT.EARTH_AVAILABLE = False
        if self.dcm_list: 
          output('Orbital position and velocity data could not be found.')

      self.surface_forces, aero_f_max, srp_f_max = read_surface_data(OPT.filepath / OPT.FILENAME_SURFACE_FORCES)
      if self.surface_forces:
        OPT.FORCES_AVAILABLE = True

        OPT.AERO_F_MAX = aero_f_max
        OPT.SRP_F_MAX = srp_f_max
        OPT.AERO_FORCE_SCALE = (OPT.FORCE_SCALE_MAX - OPT.FORCE_SCALE_MIN)/OPT.AERO_F_MAX
        OPT.SRP_FORCE_SCALE = (OPT.FORCE_SCALE_MAX - OPT.FORCE_SCALE_MIN)/OPT.SRP_F_MAX
      else:
        OPT.FORCES_AVAILABLE = False
        output(f'The file: \'{OPT.filepath / OPT.FILENAME_SURFACE_FORCES}\' could not be found.')

      self.geometry_data, OPT.GEOMETRY_SCALE = read_geometry_data(OPT.filepath / OPT.FILENAME_GEOMETRY)
      if self.geometry_data:
        OPT.GEOMETRY_AVAILABLE = True
      else:
        OPT.GEOMETRY_AVAILABLE = False
        output(f'The file: \'{OPT.filepath / OPT.FILENAME_GEOMETRY}\' could not be found.')

      self.r_sun_list = read_r_sun_data(OPT.filepath / OPT.FILENAME_SUN_POS)
      if self.r_sun_list:
        OPT.SUN_AVAILABLE = True
      else:
        OPT.SUN_AVAILABLE = False
        output(f'The file: \'{OPT.filepath / OPT.FILENAME_SUN_POS}\' could not be found.')


    output('Setting up GUI')
    # create central widget and layout
    central_widget = QWidget()
    central_layout = QVBoxLayout(central_widget)
    self.setCentralWidget(central_widget)


    # setup PyVista viewport
    plotter_widget = self.setup_plotter(central_widget)

    
    # setup control buttons and settings
    setup_controls(self, central_layout, plotter_widget, OPT, persistent_settings)


    # reset camera
    self.plotter.reset_camera(bounds=(-OPT.GEOMETRY_SCALE, OPT.GEOMETRY_SCALE)*3)
    self.end_interaction_cb()

    output('Finished setup')


  def setup_plotter(self, central_widget) -> QWidget:
    # create plotter
    self.plotter = QtInteractor(central_widget)

    # eci frame
    self.eci_axes = Axes(frame_name='eci', opacity=0.3)
    self.eci_axes.setup(np.eye(3), OPT.GEOMETRY_SCALE, self.plotter)
    self.eci_axes.toggle_visibility(OPT.show_eci_axes, OPT.show_axes_labels)

    # base body frame
    self.body_axes = Axes(frame_name='body')
    self.body_axes.setup(np.eye(3), OPT.GEOMETRY_SCALE, self.plotter)
    self.body_axes.toggle_visibility(OPT.show_body_axes, OPT.show_axes_labels)

    # lvlh frame
    self.lvlh_axes = None
    if OPT.EARTH_AVAILABLE:
      self.lvlh_axes = Axes(frame_name='lvlh', cols=('cyan', 'magenta', 'yellow'))
      self.lvlh_axes.setup(np.eye(3), OPT.GEOMETRY_SCALE, self.plotter)
      self.lvlh_axes.toggle_visibility(OPT.show_lvlh_axes, OPT.show_axes_labels)

    # plot satellite com
    self.plotter.add_mesh(pv.Sphere(radius=OPT.GEOMETRY_SCALE*0.05), color='grey')

    # plot satellite body
    if OPT.GEOMETRY_AVAILABLE:              
      self.body_mesh = Body(self.geometry_data)
      self.body_mesh.setup(self.plotter, OPT.FORCES_AVAILABLE)
      self.body_mesh.toggle_visibility(OPT)

    # plot earth
    if OPT.EARTH_AVAILABLE:
      self.earth = Earth()
      self.earth.setup(self.r_list[0], OPT.EARTH_DISTANCE, OPT.GEOMETRY_SCALE*OPT.EARTH_SIZE, self.plotter)
      self.earth.toggle_visibility(OPT.show_earth)

      # save camera position whenever user interacts
      # used for camera orbital tracking
      self.plotter.iren.add_observer(
        "StartInteractionEvent",
        self.start_interaction_cb
      )
      self.plotter.iren.add_observer(
        "EndInteractionEvent",
        self.end_interaction_cb
      )

    # plot sun
    self.sun_vector = None
    if OPT.SUN_AVAILABLE:
      self.sun = Sun()
      self.sun.setup(self.r_sun_list[0], OPT.SUN_DISTANCE, OPT.GEOMETRY_SCALE*OPT.SUN_SIZE, self.plotter)

      if not OPT.show_sun:
        self.sun.toggle_visibility(self.plotter, OPT.show_sun)

      # sun vector
      self.sun_vector = Vector('sun', 'yellow')
      self.sun_vector.setup(OPT.GEOMETRY_SCALE*1.1, self.plotter)

      if not OPT.show_sun_vector:
        self.sun_vector.toggle_visibility(OPT.show_sun_vector, OPT.show_axes_labels)

    # 16k starry skybox (Stars)
    skybox_texture = pv.examples.download_cubemap_space_16k().to_skybox()
    self.bg_stars, _ = self.plotter.add_actor(skybox_texture)
    self.bg_stars.visibility = False

    # create layout
    plotter_widget = QWidget()
    container = QVBoxLayout(plotter_widget)
    container.addWidget(self.plotter.interactor)

    self.hud_label = QLabel('', plotter_widget)
    self.hud_label.setStyleSheet('color: white;')
    self.hud_label.move(20, 20)
    self.hud_label.setMinimumWidth(200)

    self.plotter.add_axes()
    self.change_bg(OPT.background)

    return plotter_widget

  def update_frame(self, frame=None):
    if not OPT.FILE_AVAILABLE:
      return

    # simulation time
    if not frame:
      frame = self.frame_slider.value()

    t = (frame-1)*OPT.simulation_timestep
    self.hud_label.setText(f'Frame: {frame} | t = {format_time(t, OPT.time_format)}')

    dcm = self.dcm_list[frame-1]

    # update body axes orientation
    if OPT.show_body_axes:
      self.body_axes.rotate_mesh(dcm, OPT.show_axes_labels)

    # update satellite body orientation
    if OPT.GEOMETRY_AVAILABLE and OPT.show_body_mesh:
      self.body_mesh.rotate_mesh(dcm, OPT.show_normals)

      # update surface forces
      if OPT.FORCES_AVAILABLE:
        if OPT.show_aero_f:
          self.body_mesh.update_forces(self.surface_forces[frame-1].a.f, dcm, self.body_mesh.aero_f_actors, OPT.AERO_FORCE_SCALE, OPT.FORCE_SCALE_MIN)
        if OPT.show_srp_f:
          self.body_mesh.update_forces(self.surface_forces[frame-1].s.f, dcm, self.body_mesh.srp_f_actors, OPT.SRP_FORCE_SCALE, OPT.FORCE_SCALE_MIN)

      # update SRP panel based lighting
      if OPT.FORCES_AVAILABLE and OPT.lighting:
        normed_srp = np.linalg.norm(self.surface_forces[frame-1].s.f, axis=1) / OPT.SRP_F_MAX
        self.body_mesh.update_lighting(normed_srp, OPT.SAT_AMBIENT_LIGHT)

    if OPT.SUN_AVAILABLE:
      r_s = self.r_sun_list[frame-1]
      # update sun position
      if OPT.show_sun:
        self.sun.update_position(r_s, OPT.SUN_DISTANCE)

      if OPT.show_sun_vector:
        self.sun_vector.rotate_mesh(r_s, OPT.show_axes_labels)


    if OPT.EARTH_AVAILABLE:
      r = self.r_list[frame-1]
      v = self.v_list[frame-1]

      # update lvlh orientation
      if OPT.show_lvlh_axes:
        dcm_lvlh = get_lvlh(r, v)
        self.lvlh_axes.rotate_mesh(dcm_lvlh, OPT.show_axes_labels)

      # update earth position
      if OPT.show_earth:
        self.earth.update_position(r, OPT.EARTH_DISTANCE)

    # use camera tracking
    if OPT.EARTH_AVAILABLE and OPT.tracking_camera != 'Free':
      cam = self.plotter.camera
      cam.focal_point = (0, 0, 0)

      u_r = r / np.linalg.norm(r)
      u_v = v / np.linalg.norm(v)

      if OPT.tracking_camera == 'Down':
        # motion towards top of screen
        cam.position = -self.earth.u * 2
        cam.up = u_v
      elif OPT.tracking_camera == 'Forward':
        # motion into screen
        cam.position = -u_v * 2
        cam.up = u_r
      elif OPT.tracking_camera == 'Side':
        # motion towards right of screen
        cam.position = np.cross(u_v, u_r) * 2
        cam.up = u_r
      elif OPT.tracking_camera == 'Orbital' and not self.user_interacting:
        # arbitrary angle, fixed to orbital frame
        if hasattr(self, 'ref_cam_pos') and hasattr(self, 'ref_earth_pos'):
          ref_earth_dir = self.ref_earth_pos / np.linalg.norm(self.ref_earth_pos)

          axis = np.cross(ref_earth_dir, -u_r)
          axis_norm = np.linalg.norm(axis)

          if axis_norm > 1e-8:
            axis /= axis_norm

            angle = np.degrees(np.arccos(
              np.clip(np.dot(ref_earth_dir, -u_r), -1.0, 1.0)
            ))

            rot = pv.Transform().rotate_vector(axis, angle)
            R = rot.rotation_matrix
            cam.position = R @ self.ref_cam_pos

          view = np.array(cam.direction)
          earth = np.array(u_r)

          right = np.cross(view, earth)
          norm = np.linalg.norm(right)

          if norm > 1e-8:
            right /= norm
            cam.up = np.cross(right, view)
            cam.up /= np.linalg.norm(cam.up)

      elif OPT.tracking_camera == 'Satellite' and not self.user_interacting:
        # arbitrary angle, fixed to body frame
        if hasattr(self, 'ref_cam_pos_body'):
          cam.position = dcm.T @ self.ref_cam_pos_body
          cam.up = dcm.T @ self.ref_cam_up_body

      elif OPT.tracking_camera == 'Inertial':
        # arbitrary angle, inertially fixed
        None

    self.plotter.render()



  def change_bg(self, bg):
    if bg == 'Black':
      self.bg_stars.visibility = False
      self.plotter.background_color = 'black'
    elif bg == 'White':
      self.bg_stars.visibility = False
      self.plotter.background_color = 'white'
    elif bg == 'Stars':
      self.bg_stars.visibility = True

    axes = self.plotter.renderer.axes_widget.GetOrientationMarker()
    if bg == 'White':
      # frame/time counter
      self.hud_label.setStyleSheet('color: black;')

      # pyvista orientation axes
      axes.GetXAxisCaptionActor2D().GetCaptionTextProperty().SetColor(0, 0, 0)
      axes.GetYAxisCaptionActor2D().GetCaptionTextProperty().SetColor(0, 0, 0)
      axes.GetZAxisCaptionActor2D().GetCaptionTextProperty().SetColor(0, 0, 0)

      # axes labels
      for axes in [self.eci_axes, self.body_axes, self.lvlh_axes, self.sun_vector]:
        if hasattr(axes, 'label_actor'):
          text_property = axes.label_actor.GetMapper().GetInputConnection(0, 0).GetProducer().GetTextProperty()
          text_property.SetColor(0, 0, 0)
    else:
      self.hud_label.setStyleSheet('color: white;')
      axes.GetXAxisCaptionActor2D().GetCaptionTextProperty().SetColor(1, 1, 1)
      axes.GetYAxisCaptionActor2D().GetCaptionTextProperty().SetColor(1, 1, 1)
      axes.GetZAxisCaptionActor2D().GetCaptionTextProperty().SetColor(1, 1, 1)
      for axes in [self.eci_axes, self.body_axes, self.lvlh_axes, self.sun_vector]:
        if hasattr(axes, 'label_actor'):
          text_property = axes.label_actor.GetMapper().GetInputConnection(0, 0).GetProducer().GetTextProperty()
          text_property.SetColor(1, 1, 1)

  def render_animation(self, settings):
    start = settings["start_frame"]
    end = settings["end_frame"]
    output_type = settings["output_type"]
    output_path = Path(settings["output_path"])
    quality = settings["quality"]
    speed = settings["speed"]
    fps = settings["fps"]

    if output_type == "mp4":
      self.plotter.open_movie(str(output_path), framerate=fps, quality=quality)
    else:
      self.plotter.open_gif(str(output_path), fps=fps)

    start_time = time.perf_counter()

    for frame in range(start, end+1, speed):
      output(f'Rendering: {frame-start+1}/{end-start+1}', replace_line=True)
      self.update_frame(frame)
      self.plotter.write_frame()

      # clear console (and any imageio warnings)
      if frame == start:
        print("\033[2J\033[H", end="", flush=True)

    if ((end+1) % speed):
      output(f'Rendering: {end-start+1}/{end-start+1}', replace_line=True)
      self.update_frame(end)
      self.plotter.write_frame()

    self.plotter.close()
    QApplication.processEvents()

    end_time = time.perf_counter() - start_time
    output(f'\nRendering complete: {end_time}s elapsed')
    output(f'Render output at: {output_path}')

    self.setup_window(read_data=False)

  def start_interaction_cb(self, *_):
    self.user_interacting = True

  def end_interaction_cb(self, *_):
    self.user_interacting = False
    self.ref_cam_pos = np.array(self.plotter.camera.position)
    if OPT.EARTH_AVAILABLE:
      self.ref_earth_pos = np.array(self.earth.actor.position)

    if OPT.FILE_AVAILABLE:
      dcm = self.dcm_list[self.frame_slider.value()-1]
      self.ref_cam_pos_body = dcm @ np.array(self.plotter.camera.position)
      self.ref_cam_up_body = dcm @ np.array(self.plotter.camera.up)

  def closeEvent(self, event):
    self.plotter.close()
    event.accept()


def main():
  app = QApplication(sys.argv)

  window = MainWindow()
  window.show()

  sys.exit(app.exec())


if __name__ == "__main__":
  main()