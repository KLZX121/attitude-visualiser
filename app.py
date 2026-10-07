import sys
import time
import pyvista as pv
import numpy as np
from helpers import *
from config import OPT

from pyvistaqt import QtInteractor
from qtpy.QtCore import Qt, QTimer
from PyQt6.QtGui import QDoubleValidator
from qtpy.QtWidgets import *

#TODO: add export option (and settings)

class MainWindow(QMainWindow):
  user_interacting = False

  def __init__(self):
    super().__init__()

    self.setWindowTitle('Attitude Visualiser v0.1')
    self.resize(OPT.WINDOW_SIZE[0], OPT.WINDOW_SIZE[1])

    # read data
    self.dcm_list, self.r_list, self.v_list = read_state_data(OPT.FILEPATH_STATE, OPT.I_Q, OPT.I_R, OPT.I_V)
    self.N_FRAMES = len(self.dcm_list)

    if self.r_list and self.v_list:
      OPT.EARTH_AVAILABLE = True

    self.surface_forces = read_surface_data(OPT.FILEPATH_SURFACE_FORCES)
    if self.surface_forces:
      OPT.FORCES_AVAILABLE = True

    self.geometry_data = read_geometry_data(OPT.FILEPATH_GEOMETRY)
    if self.geometry_data:
      OPT.GEOMETRY_AVAILABLE = True

    self.r_sun_list = read_r_sun_data(OPT.FILEPATH_SUN_POS)
    if self.r_sun_list:
      OPT.SUN_AVAILABLE = True

    # create central widget and layout
    central_widget = QWidget()
    central_layout = QVBoxLayout(central_widget)
    self.setCentralWidget(central_widget)

    # setup PyVista viewport
    plotter_widget = self.setup_plotter(central_widget)
    
    # setup control buttons and settings
    top_layout, bottom_layout, left_layout = self.setup_controls()

    # middle layout
    middle_layout = QHBoxLayout()
    middle_layout.addLayout(left_layout)
    middle_layout.addWidget(plotter_widget, 1)

    # add everything to central layout
    central_layout.addLayout(top_layout)
    central_layout.addLayout(middle_layout)
    central_layout.addLayout(bottom_layout)

    # reset camera
    self.plotter.reset_camera(bounds=(-OPT.GEOMETRY_SCALE, OPT.GEOMETRY_SCALE)*3)
    self.end_interaction_cb()

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
    if OPT.EARTH_AVAILABLE:
      self.lvlh_axes = Axes(frame_name='lvlh', cols=('cyan', 'magenta', 'yellow'))
      self.lvlh_axes.setup(np.eye(3), OPT.GEOMETRY_SCALE, self.plotter)
      self.lvlh_axes.toggle_visibility(OPT.show_lvlh_axes, OPT.show_axes_labels)

    # plot satellite com
    self.plotter.add_mesh(pv.Sphere(radius=OPT.GEOMETRY_SCALE*0.05), color='grey')

    # plot satellite body
    if OPT.GEOMETRY_AVAILABLE:              
      self.body_mesh = Body(self.geometry_data)
      self.body_mesh.setup(self.plotter, OPT.show_normals, OPT.FORCES_AVAILABLE, OPT.show_aero_f, OPT.show_srp_f)

      if not OPT.show_body_mesh:
        self.body_mesh.toggle_visibility(OPT.show_body_mesh, OPT.show_normals, OPT.show_aero_f, OPT.show_srp_f)

    # plot earth
    if OPT.EARTH_AVAILABLE:
      self.earth = Earth()
      self.earth.setup(self.r_list[0], OPT.EARTH_DISTANCE, OPT.GEOMETRY_SCALE*OPT.EARTH_SIZE, self.plotter)
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

    # plot sun
    if OPT.SUN_AVAILABLE:
      self.sun = Sun()
      self.sun.setup(self.r_sun_list[0], OPT.SUN_DISTANCE, OPT.GEOMETRY_SCALE*OPT.SUN_SIZE, self.plotter)

      if not OPT.show_sun:
        self.sun.toggle_visibility(self.plotter)

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

    self.plotter.add_axes()
    self.change_bg(OPT.background)

    return plotter_widget

  def setup_controls(self) -> tuple[QHBoxLayout, QVBoxLayout, QVBoxLayout]:
    # play pause button
    def toggle_play(is_checked):
      OPT.autoplay = is_checked

      if is_checked:
        self.play_button.setText('Pause')
      else:
        self.play_button.setText('Play')
    
    self.play_button = QPushButton('Pause' if OPT.autoplay else 'Play', checkable=True, checked=OPT.autoplay)
    self.play_button.toggled.connect(toggle_play)

    # toggle playback looping
    def toggle_loop(is_checked):
      OPT.loop_playback = is_checked
    self.loop_btn = QPushButton('Loop', checkable=True, checked=OPT.loop_playback)
    self.loop_btn.toggled.connect(toggle_loop)

    # playback speed
    def set_playback_speed(label):
      if label == 'Real Time':
        OPT.real_time = True
        OPT.playback_speed = 1
      else:
        OPT.real_time = False
        OPT.playback_speed = int(label[:-1])
    self.speed_combo = QComboBox()
    self.speed_combo.addItem('Real Time')
    self.speed_combo.addItems([f'{speed}x' for speed in OPT.SPEEDS])
    self.speed_combo.setCurrentText(f'{OPT.playback_speed}x')
    self.speed_combo.currentTextChanged.connect(set_playback_speed)

    # playback slider
    self.update_frame(1)
    self.frame_slider = QSlider(Qt.Orientation.Horizontal)
    self.frame_slider.setRange(1, self.N_FRAMES)
    self.frame_slider.valueChanged.connect(self.update_frame)

    # step frames:
    def step_frame(is_timer, frame_increment):
      if is_timer and not OPT.autoplay:
        return
      elif is_timer and OPT.real_time:
        curr_time = time.perf_counter()
        if (curr_time - OPT.real_time_last_update) >= OPT.SIMULATION_TIMESTEP:
          OPT.real_time_last_update = curr_time
        else:
          return
      
      current_frame = self.frame_slider.value()
      next_frame = current_frame + frame_increment

      if OPT.loop_playback:
        next_frame = next_frame % self.N_FRAMES
        if next_frame < 1:
          next_frame = self.N_FRAMES
      elif next_frame > self.N_FRAMES:
        next_frame = self.N_FRAMES
        self.play_button.toggle()

      self.frame_slider.setValue(next_frame)

    self.step_pos_btn = QPushButton('>')
    self.step_neg_btn = QPushButton('<')
    self.step_pos_btn.clicked.connect(lambda: step_frame(False, OPT.playback_speed))
    self.step_neg_btn.clicked.connect(lambda: step_frame(False, -OPT.playback_speed))
    self.step_pos_btn.setFixedWidth(30)
    self.step_neg_btn.setFixedWidth(30)

    # autoplay functionality
    self.timer = QTimer(self)
    self.timer.timeout.connect(lambda: step_frame(True, OPT.playback_speed))
    self.timer.start(OPT.TIMER_INT)

    # change simulation timestep
    def update_dt(text):
      if text:
        OPT.SIMULATION_TIMESTEP = float(text)
    self.dt_input = QLineEdit()
    self.dt_input.setValidator(QDoubleValidator(bottom=0))
    self.dt_input.setText(str(OPT.SIMULATION_TIMESTEP))
    self.dt_input.textChanged.connect(update_dt)
    self.dt_input.setMaximumWidth(80)

    # camera tracking mode
    def switch_cam(label):
      OPT.tracking_camera = label
      self.update_frame()
    self.cam_combo = QComboBox()
    self.cam_combo.addItems(OPT.CAM_LABELS)
    self.cam_combo.setCurrentText(OPT.tracking_camera)
    self.cam_combo.currentTextChanged.connect(switch_cam)

    # background switching
    def switch_bg(label):
      OPT.background = label
      self.change_bg(OPT.background)
    self.bg_combo = QComboBox()
    self.bg_combo.addItems(OPT.BACKGROUNDS)
    self.bg_combo.setCurrentText(OPT.background)
    self.bg_combo.currentTextChanged.connect(switch_bg)

    # time format
    def switch_time_format(label):
      OPT.time_format = label
      self.update_frame()
    self.time_combo = QComboBox()
    self.time_combo.addItems(OPT.TIME_FORMATS)
    self.time_combo.setCurrentText(OPT.time_format)
    self.time_combo.currentTextChanged.connect(switch_time_format)

    # earth toggle
    def toggle_earth(is_checked):
      OPT.show_earth = is_checked
      self.earth.toggle_visibility()
      self.update_frame()
    self.earth_btn = QPushButton('Earth', checkable=True, checked=OPT.show_earth)
    self.earth_btn.toggled.connect(toggle_earth)

    # sun toggle
    def toggle_sun(is_checked):
      OPT.show_sun = is_checked
      self.sun.toggle_visibility(self.plotter)
      self.update_frame()
    self.sun_btn = QPushButton('Sun', checkable=True, checked=OPT.show_sun)
    self.sun_btn.toggled.connect(toggle_sun)

    # ref eci axes toggle
    def toggle_raxes(is_checked):
      OPT.show_eci_axes = is_checked
      self.eci_axes.toggle_visibility(OPT.show_eci_axes, OPT.show_axes_labels)
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
      self.body_axes.toggle_visibility(OPT.show_body_axes, OPT.show_axes_labels)
      self.update_frame()
    self.baxes_btn = QPushButton(
      'Body Axes',
      checkable=True,
      checked=OPT.show_body_axes
    )
    self.baxes_btn.toggled.connect(toggle_baxes)

    # lvlh axes toggle
    def toggle_lvlh(is_checked):
      OPT.show_lvlh_axes = is_checked
      self.lvlh_axes.toggle_visibility(OPT.show_lvlh_axes, OPT.show_axes_labels)
      self.update_frame()
    self.laxes_btn = QPushButton(
      'LVLH Axes',
      checkable=True,
      checked=OPT.show_lvlh_axes
    )
    self.laxes_btn.toggled.connect(toggle_lvlh)

    # axes labels
    def toggle_labels(is_checked):
      OPT.show_axes_labels = is_checked
      self.eci_axes.toggle_visibility(OPT.show_eci_axes, OPT.show_axes_labels)
      self.body_axes.toggle_visibility(OPT.show_body_axes, OPT.show_axes_labels)
      self.lvlh_axes.toggle_visibility(OPT.show_lvlh_axes, OPT.show_axes_labels)
      self.update_frame()
    self.labels_btn = QPushButton('Axes Labels', checkable=True, checked=OPT.show_axes_labels)
    self.labels_btn.toggled.connect(toggle_labels)


    # satellite body toggle
    def toggle_body_mesh(is_checked):
      OPT.show_body_mesh = is_checked
      self.body_mesh.toggle_visibility(OPT.show_body_mesh, OPT.show_normals, OPT.show_aero_f, OPT.show_srp_f)

      if OPT.show_body_mesh: 
        self.norm_btn.setEnabled(True)
        self.forces_combo.setEnabled(True)
      else:
        self.norm_btn.setEnabled(False)
        self.forces_combo.setEnabled(False)

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
        self.body_mesh.toggle_visibility(OPT.show_body_mesh, OPT.show_normals, OPT.show_aero_f, OPT.show_srp_f)

      self.update_frame()
    self.norm_btn = QPushButton(
      'Normals',
      checkable=True,
      enabled=OPT.show_body_mesh
    )
    self.norm_btn.toggled.connect(toggle_norms)

    # satellite forces combo box
    def change_forces(option):
      OPT.show_aero_f = any(sub in option for sub in ['Aero', 'All'])
      OPT.show_srp_f = any(sub in option for sub in ['SRP', 'All'])

      self.body_mesh.toggle_visibility(OPT.show_body_mesh, OPT.show_normals, OPT.show_aero_f, OPT.show_srp_f)

      self.update_frame()
    self.forces_combo = QComboBox()
    self.forces_combo.addItems(['None', 'Aero', 'SRP', 'All'])
    self.forces_combo.currentTextChanged.connect(change_forces)


    if OPT.GEOMETRY_AVAILABLE:
      self.body_mesh_btn.setChecked(OPT.show_body_mesh)
      self.norm_btn.setChecked(OPT.show_normals)
      if OPT.FORCES_AVAILABLE:
        #current_force = ''
        if OPT.show_srp_f and OPT.show_aero_f:
          current_force = 'All'
        elif OPT.show_aero_f:
          current_force = 'Aero'
        elif OPT.show_srp_f:
          current_force = 'SRP'
        else:
          current_force = 'None'
        self.forces_combo.setCurrentText(current_force)


    top_layout = QHBoxLayout()
    top_layout.addWidget(QLabel('Camera:'), 1)
    top_layout.addWidget(self.cam_combo, 2)
    top_layout.addWidget(QLabel('Background:'), 1)
    top_layout.addWidget(self.bg_combo, 2)
    top_layout.addWidget(QLabel('Time Format:'), 1)
    top_layout.addWidget(self.time_combo, 2)
    top_layout.addStretch(100)

    left_layout = QVBoxLayout()
    left_layout.addSpacing(10)
    add_divider(left_layout, spacing_before=0)
    left_layout.addWidget(self.raxes_btn)
    if OPT.EARTH_AVAILABLE:
      left_layout.addWidget(self.laxes_btn)
    left_layout.addWidget(self.baxes_btn)
    left_layout.addSpacing(10)
    left_layout.addWidget(self.labels_btn)
    add_divider(left_layout)
    if OPT.EARTH_AVAILABLE:
      left_layout.addWidget(self.earth_btn)
    if OPT.SUN_AVAILABLE:
      left_layout.addWidget(self.sun_btn)
    if OPT.GEOMETRY_AVAILABLE:
      add_divider(left_layout)
      left_layout.addWidget(self.body_mesh_btn)
      left_layout.addWidget(self.norm_btn)
    if OPT.FORCES_AVAILABLE:
      left_layout.addWidget(self.forces_combo)
    left_layout.addStretch()

    bot_top = QHBoxLayout()
    bot_top.addWidget(self.play_button)
    bot_top.addWidget(self.step_neg_btn)
    bot_top.addWidget(self.step_pos_btn)
    bot_top.addWidget(self.frame_slider)

    bot_bot = QHBoxLayout()
    bot_bot.addWidget(self.loop_btn)
    bot_bot.addWidget(QLabel('Playback Speed:'))
    bot_bot.addWidget(self.speed_combo)
    bot_bot.addWidget(QLabel('Simulation Timestep (s):'))
    bot_bot.addWidget(self.dt_input)
    bot_bot.addStretch()

    bottom_layout = QVBoxLayout()
    bottom_layout.addLayout(bot_top)
    add_divider(bottom_layout, spacing_before=0, spacing_after=0)
    bottom_layout.addLayout(bot_bot)


    return top_layout, bottom_layout, left_layout

  def update_frame(self, frame=None):
    # simulation time
    if not frame:
      frame = self.frame_slider.value()

    t = (frame-1)*OPT.SIMULATION_TIMESTEP
    self.hud_label.setText(f'Frame: {frame} | t = {format_time(t, OPT.time_format)}')
    self.hud_label.adjustSize()

    dcm = self.dcm_list[frame-1]
    r = self.r_list[frame-1]
    v = self.v_list[frame-1]

    # update body axes orientation
    if OPT.show_body_axes:
      self.body_axes.rotate_mesh(dcm, OPT.show_axes_labels)

    # update lvlh axes orientation
    if OPT.show_lvlh_axes:
      dcm_lvlh = get_lvlh(r, v)
      self.lvlh_axes.rotate_mesh(dcm_lvlh, OPT.show_axes_labels)

    # update satellite body orientation
    if OPT.GEOMETRY_AVAILABLE and OPT.show_body_mesh:
      self.body_mesh.rotate_mesh(dcm)

      # update surface forces
      if OPT.FORCES_AVAILABLE and (OPT.show_aero_f or OPT.show_srp_f):
        self.body_mesh.update_forces(self.surface_forces[frame-1], dcm, OPT.AERO_FORCE_SCALE, OPT.SRP_FORCE_SCALE)

    if OPT.SUN_AVAILABLE and OPT.show_sun:
      r_s = self.r_sun_list[frame-1]
      self.sun.update_position(r_s, OPT.SUN_DISTANCE)
      

    if OPT.EARTH_AVAILABLE:
      r = self.r_list[frame-1]
      v = self.v_list[frame-1]

      u_r = r / np.linalg.norm(r)
      u_v = v / np.linalg.norm(v)

      # update earth position
      if OPT.show_earth:
        self.earth.update_position(r, OPT.EARTH_DISTANCE)

    # use camera tracking
    if OPT.EARTH_AVAILABLE and not OPT.tracking_camera == 'Free':
      cam = self.plotter.camera
      cam.focal_point = (0, 0, 0)

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
      if OPT.show_axes_labels:
        for axes in [self.eci_axes, self.body_axes, self.lvlh_axes]:
          text_property = axes.label_actor.GetMapper().GetInputConnection(0, 0).GetProducer().GetTextProperty()
          text_property.SetColor(0, 0, 0)
    else:
      self.hud_label.setStyleSheet('color: white;')
      axes.GetXAxisCaptionActor2D().GetCaptionTextProperty().SetColor(1, 1, 1)
      axes.GetYAxisCaptionActor2D().GetCaptionTextProperty().SetColor(1, 1, 1)
      axes.GetZAxisCaptionActor2D().GetCaptionTextProperty().SetColor(1, 1, 1)
      if OPT.show_axes_labels:
        for axes in [self.eci_axes, self.body_axes, self.lvlh_axes]:
          text_property = axes.label_actor.GetMapper().GetInputConnection(0, 0).GetProducer().GetTextProperty()
          text_property.SetColor(1, 1, 1)

  def start_interaction_cb(self, *_):
    self.user_interacting = True

  def end_interaction_cb(self, *_):
    self.user_interacting = False
    self.ref_cam_pos = np.array(self.plotter.camera.position)
    self.ref_earth_pos = np.array(self.earth.actor.position)

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