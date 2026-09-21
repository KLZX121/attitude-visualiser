import sys
import pyvista as pv
import numpy as np
from dataclasses import dataclass
from helpers import *

from pyvistaqt import QtInteractor
from qtpy.QtCore import Qt, QTimer, QSignalBlocker
from qtpy.QtWidgets import (
  QApplication,
  QMainWindow,
  QPushButton,
  QSlider,
  QLabel,
  QVBoxLayout,
  QHBoxLayout,
  QWidget,
)

@dataclass
class OPT:
  FILEPATH_STATE: str = 'xdata.json'
  FILEPATH_GEOMETRY: str = 'geometry.json'
  FILEPATH_SURFACE_FORCES: str = 'surfdata.json'

  # simulation stepsize (dt)
  SIMULATION_TIMESTEP: int = 1
  # indices of quaternion, orbital pos, and orbital vel in state data
  I_Q: tuple[int, int] = (6, 10)
  I_R: tuple[int, int] = (0, 3)
  I_V: tuple[int, int] = (3, 6)

  # roughly longest length of satellite, used to resize axes and earth
  GEOMETRY_SCALE: float = 0.3
  # how much bigger the earth is compared to the satellite
  EARTH_SIZE: float = 10
  # order of magnitude of forces
  FORCE_SCALE: float = 0.15*10**5
  
  WINDOW_SIZE: tuple[int, int] = (800, 600)

  autoplay: bool = False
  LOOP_PLAYBACK: bool = True
  # how many frames to increment each playback step
  PLAYBACK_SPEED: int = 5
  # how often (ms) that a playback step occurs (17ms = 1/(60fps))
  TIMER_INT: int = 17

  # whether the camera should track the satellite over its orbit
  # the camera angle to use for tracking
  CAM_LABELS = ['Free', 'Orbital', 'Down', 'Forward', 'Side', 'Inertial']
  tracking_camera: str = 'Orbital'

  # background image/skybox
  BACKGROUNDS = ['Black', 'White', 'Stars']
  background = 'Black'

  show_eci_axes: bool = False
  show_body_axes: bool = False

  FORCES_AVAILABLE: bool = False

  show_body_mesh: bool = True
  show_normals: bool = False
  show_forces: bool = True

  show_earth: bool = True

#TODO: visualise torques
#TODO: add incremental playback (frame by frame)
#TODO: add orientation of earth
#TODO: add sun
#TODO: add export option (and settings)
#TODO: add LVLH


class MainWindow(QMainWindow):
  user_interacting = False

  def __init__(self):
    super().__init__()

    self.setWindowTitle('Attitude Visualiser v0.1')
    self.resize(OPT.WINDOW_SIZE[0], OPT.WINDOW_SIZE[1])

    # read data
    self.dcm_list, self.r_list, self.v_list = read_state_data(OPT.FILEPATH_STATE, OPT.I_Q, OPT.I_R, OPT.I_V)
    self.N_FRAMES = len(self.dcm_list)

    self.surface_forces = read_surface_data(OPT.FILEPATH_SURFACE_FORCES)
    if self.surface_forces:
      OPT.FORCES_AVAILABLE = True

    # create central widget and layout
    central_widget = QWidget()
    central_layout = QVBoxLayout(central_widget)
    self.setCentralWidget(central_widget)

    # setup PyVista viewport
    plotter_widget = self.setup_plotter(central_widget)
    
    # setup control buttons and settings
    toggles_layout, playback_layout = self.setup_controls()

    # add everything to central layout
    central_layout.addLayout(toggles_layout)
    central_layout.addWidget(plotter_widget, 1)
    central_layout.addLayout(playback_layout)

  def setup_plotter(self, central_widget) -> QWidget:
    # create plotter
    self.plotter = QtInteractor(central_widget)

    # base ref frame
    self.eci_axes = Axes(frame_name='ref', opacity=0.3)
    self.eci_axes.setup(np.eye(3), OPT.GEOMETRY_SCALE, self.plotter)
    if not OPT.show_eci_axes:
      self.eci_axes.toggle_visibility()

    # base body frame
    self.body_axes = Axes(frame_name='body')
    self.body_axes.setup(np.eye(3), OPT.GEOMETRY_SCALE, self.plotter)
    if not OPT.show_body_axes:
      self.body_axes.toggle_visibility()

    # plot satellite com
    self.plotter.add_mesh(pv.Sphere(radius=OPT.GEOMETRY_SCALE*0.05), color='grey')

    # plot satellite body
    if OPT.FILEPATH_GEOMETRY:
      geometry_data = read_geometry_data(OPT.FILEPATH_GEOMETRY)

      self.geometry_data = geometry_data
              
      self.body_mesh = Body(self.geometry_data)
      self.body_mesh.setup(self.plotter, OPT.show_normals, OPT.FORCES_AVAILABLE, OPT.show_forces)

      if not OPT.show_body_mesh:
        self.body_mesh.toggle_visibility(OPT.show_body_mesh, OPT.show_normals, OPT.show_forces)

    # plot earth
    if OPT.I_R:
      self.earth = Earth()
      self.earth.setup(self.r_list[0], OPT.GEOMETRY_SCALE*OPT.EARTH_SIZE, self.plotter)
      if not OPT.show_earth:
        self.earth.toggle_visibility()

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

    # 16k starry skybox (Stars)
    skybox_texture = pv.examples.download_cubemap_space_16k().to_skybox()
    self.bg_stars, _ = self.plotter.add_actor(skybox_texture)
    self.bg_stars.visibility = False


    self.plotter.add_axes()

    # create layout
    plotter_widget = QWidget()
    container = QVBoxLayout(plotter_widget)
    container.addWidget(self.plotter.interactor)

    self.hud_label = QLabel('', plotter_widget)
    self.hud_label.setStyleSheet('color: white;')
    self.hud_label.move(20, 20)

    self.change_bg(OPT.background)

    return plotter_widget

  def setup_controls(self) -> tuple[QHBoxLayout, QHBoxLayout]:
    # play pause button
    def toggle_play(is_checked):
      OPT.autoplay = is_checked

      if is_checked:
        self.play_button.setText('Pause')
      else:
        self.play_button.setText('Play')
    
    self.play_button = QPushButton('Pause' if OPT.autoplay else 'Play', checkable=True, checked=OPT.autoplay)
    self.play_button.toggled.connect(toggle_play)


    # playback slider
    self.update_frame(1)
    self.frame_slider = QSlider(Qt.Orientation.Horizontal)
    self.frame_slider.setRange(1, self.N_FRAMES)
    self.frame_slider.valueChanged.connect(self.update_frame)


    # autoplay functionality
    def timer_callback():
      if not OPT.autoplay:
        return
      
      current_frame = self.frame_slider.value()
  
      next_frame = current_frame + OPT.PLAYBACK_SPEED
      if OPT.LOOP_PLAYBACK:
        next_frame = (current_frame % self.N_FRAMES) + OPT.PLAYBACK_SPEED
      elif next_frame >= self.N_FRAMES:
        return
  
      self.frame_slider.setValue(next_frame)
    
    self.timer = QTimer(self)
    self.timer.timeout.connect(timer_callback)
    self.timer.start(OPT.TIMER_INT)


    # camera tracking mode
    def switch_cam(*_):
      curr_label = self.cam_btn.text()
      next_label_i = (OPT.CAM_LABELS.index(curr_label) + 1) % len(OPT.CAM_LABELS)

      OPT.tracking_camera = OPT.CAM_LABELS[next_label_i]
      self.cam_btn.setText(OPT.tracking_camera)

      self.update_frame()

    self.cam_btn = QPushButton(OPT.tracking_camera)
    self.cam_btn.clicked.connect(switch_cam)

    # background switching
    def switch_bg(*_):
      curr_label = self.bg_btn.text()
      next_label_i = (OPT.BACKGROUNDS.index(curr_label) + 1) % len(OPT.BACKGROUNDS)

      OPT.background = OPT.BACKGROUNDS[next_label_i]
      self.bg_btn.setText(OPT.background)

      self.change_bg(OPT.background)

    self.bg_btn = QPushButton(OPT.background)
    self.bg_btn.clicked.connect(switch_bg)

    # earth toggle
    def toggle_earth(is_checked):
      OPT.show_earth = is_checked
      self.earth.toggle_visibility()
      self.update_frame()
    self.earth_btn = QPushButton('Earth', checkable=True, checked=OPT.show_earth)
    self.earth_btn.toggled.connect(toggle_earth)

    # ref eci axes toggle
    def toggle_raxes(is_checked):
      OPT.show_eci_axes = is_checked
      self.eci_axes.toggle_visibility()
      self.update_frame()

    self.raxes_btn = QPushButton(
      'ECI Axes',
      checkable=True,
      checked=OPT.show_eci_axes
    )
    self.raxes_btn.toggled.connect(toggle_raxes)


    # body axes toggle
    def toggle_baxes(is_checked):
      OPT.show_body_axes = is_checked
      self.body_axes.toggle_visibility()
      self.update_frame()

    self.baxes_btn = QPushButton(
      'Body Axes',
      checkable=True,
      checked=OPT.show_body_axes
    )
    self.baxes_btn.toggled.connect(toggle_baxes)


    # satellite body toggle
    def toggle_body_mesh(is_checked):
      # toggle visibility of body mesh
      OPT.show_body_mesh = is_checked
      self.body_mesh.toggle_visibility(OPT.show_body_mesh, OPT.show_normals, OPT.show_forces)

      if OPT.show_body_mesh: 
        self.norm_btn.setEnabled(True)
        self.force_btn.setEnabled(True)
      else:
        self.norm_btn.setEnabled(False)
        self.force_btn.setEnabled(False)

      self.update_frame()

    self.body_mesh_btn = QPushButton(
      'Satellite',
      checkable=True
    )
    self.body_mesh_btn.toggled.connect(toggle_body_mesh)

    # satellite normals toggle
    def toggle_norms(is_checked):
      OPT.show_normals = is_checked

      if hasattr(self, 'body_mesh'):
        self.body_mesh.toggle_visibility(OPT.show_body_mesh, OPT.show_normals, OPT.show_forces)

      self.update_frame()

    self.norm_btn = QPushButton(
      'Normals',
      checkable=True,
      enabled=OPT.show_body_mesh
    )
    self.norm_btn.toggled.connect(toggle_norms)

    # satellite forces toggle
    def toggle_forces(is_checked):
      OPT.show_forces = is_checked

      if hasattr(self, 'body_mesh'):
        self.body_mesh.toggle_visibility(OPT.show_body_mesh, OPT.show_normals, OPT.show_forces)

      self.update_frame()

    self.force_btn = QPushButton(
      'Forces',
      checkable=True,
      enabled=OPT.show_body_mesh
    )
    self.force_btn.toggled.connect(toggle_forces)

    self.body_mesh_btn.setChecked(OPT.show_body_mesh)
    self.norm_btn.setChecked(OPT.show_normals)
    self.force_btn.setChecked(OPT.show_forces)

    # controls ui layout
    playback_layout = QHBoxLayout()
    playback_layout.addWidget(self.play_button)
    playback_layout.addWidget(self.frame_slider)

    toggle_layout = QHBoxLayout()
    toggle_layout.addWidget(QLabel('Camera:'), 1)
    toggle_layout.addWidget(self.cam_btn, 2)
    toggle_layout.addWidget(QLabel('Background:'), 1)
    toggle_layout.addWidget(self.bg_btn, 2)
    toggle_layout.addWidget(QLabel('Toggles:'), 1)
    toggle_layout.addWidget(self.earth_btn, 2)
    toggle_layout.addWidget(self.raxes_btn, 2)
    toggle_layout.addWidget(self.baxes_btn, 2)
    toggle_layout.addWidget(self.body_mesh_btn, 2)
    toggle_layout.addWidget(self.norm_btn, 1)
    toggle_layout.addWidget(self.force_btn, 1)

    return toggle_layout, playback_layout

  def update_frame(self, frame=None):
    # simulation time
    if not frame:
      frame = self.frame_slider.value()

    t = (frame-1)*OPT.SIMULATION_TIMESTEP
    self.hud_label.setText(f'Frame: {frame}\nt = {(t // 3600) % 60} h {(t // 60) % 60} m {t % 60} s')

    dcm = self.dcm_list[frame-1]

    # update body axes orientation
    if OPT.show_body_axes:
      self.body_axes.rotate_mesh(dcm)

    # update satellite body orientation
    if OPT.show_body_mesh and hasattr(self, 'body_mesh'):
      self.body_mesh.rotate_mesh(dcm)

      # update surface forces
      if OPT.show_forces:
        self.body_mesh.update_forces(self.surface_forces[frame-1], dcm, OPT.FORCE_SCALE)
      

    if self.r_list and self.v_list:
      r = self.r_list[frame-1]
      v = self.v_list[frame-1]

      u_r = r / np.linalg.norm(r)
      u_v = v / np.linalg.norm(v)

      # update earth position
      if OPT.show_earth:
        self.earth.update_position(r)

      # use camera tracking
      if not OPT.tracking_camera == 'Free':
        cam = self.plotter.camera
        cam.focal_point = (0, 0, 0)

        if OPT.tracking_camera == 'Down':
          # motion towards top of screen
          cam.position = -self.earth.u * 2
          cam.up = u_v
        elif OPT.tracking_camera == 'Forward':
          # motion into screen
          cam.position = -u_v * 2 + u_r * 0.8
          cam.up = u_r
        elif OPT.tracking_camera == 'Side':
          # motion towards right of screen
          cam.position = np.cross(u_v, u_r) * 2
          cam.up = u_r
        elif OPT.tracking_camera == 'Orbital' and not self.user_interacting:
          # arbitrary angle, fixed to orbital frame
          if hasattr(self, 'ref_cam_pos'):
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

    # change axes labels
    axes = self.plotter.renderer.axes_widget.GetOrientationMarker()
    if bg == 'White':
      self.hud_label.setStyleSheet('color: black;')
      axes.GetXAxisCaptionActor2D().GetCaptionTextProperty().SetColor(0, 0, 0)
      axes.GetYAxisCaptionActor2D().GetCaptionTextProperty().SetColor(0, 0, 0)
      axes.GetZAxisCaptionActor2D().GetCaptionTextProperty().SetColor(0, 0, 0)
    else:
      self.hud_label.setStyleSheet('color: white;')
      axes.GetXAxisCaptionActor2D().GetCaptionTextProperty().SetColor(1, 1, 1)
      axes.GetYAxisCaptionActor2D().GetCaptionTextProperty().SetColor(1, 1, 1)
      axes.GetZAxisCaptionActor2D().GetCaptionTextProperty().SetColor(1, 1, 1)

  def start_interaction_cb(self, *_):
    self.user_interacting = True

  def end_interaction_cb(self, *_):
    self.user_interacting = False
    self.ref_cam_pos = np.array(self.plotter.camera.position)
    self.ref_earth_pos = np.array(self.earth.actor.position)

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