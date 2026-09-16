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
  FILEPATH_ATTITUDE: str = 'qdata.txt'
  FILEPATH_GEOMETRY: str = 'geometry.json'

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
  
  WINDOW_SIZE: tuple[int, int] = (800, 600)

  autoplay: bool = False
  LOOP_PLAYBACK: bool = True
  # how many frames to increment each playback step
  PLAYBACK_SPEED: int = 5
  # how often (ms) that a playback step occurs (17ms = 1/(60fps))
  TIMER_INT: int = 17

  show_ref_axes: bool = True
  show_body_axes: bool = False

  show_body_mesh: bool = True
  show_normals: bool = False

  show_earth: bool = True


#TODO: add orientation of earth
#TODO: add sun
#TODO: add export option (and settings)
#TODO: add LVLH


class MainWindow(QMainWindow):
  def __init__(self):
    super().__init__()

    self.setWindowTitle('Attitude Visualiser v0.1')
    self.resize(OPT.WINDOW_SIZE[0], OPT.WINDOW_SIZE[1])

    # read data
    self.dcm_list, self.r_list, self.v_list = read_state_data(OPT.FILEPATH_ATTITUDE, OPT.I_Q, OPT.I_R, OPT.I_V)
    self.N_FRAMES = len(self.dcm_list)

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

  def closeEvent(self, event):
    self.plotter.close()
    event.accept()

  def update_frame(self, frame):
    # simulation time
    t = (frame-1)*OPT.SIMULATION_TIMESTEP
    self.label.setText(f'Frame: {frame}\nt = {(t // 3600) % 60} h {(t // 60) % 60} m {t % 60} s')

    dcm = self.dcm_list[frame-1]
    r = self.r_list[frame-1]

    if OPT.show_body_axes:
      self.body_axes.rotate_mesh(dcm)

    if OPT.show_body_mesh and hasattr(self, 'body_mesh'):
      self.body_mesh.rotate_mesh(dcm)

    if OPT.show_earth and hasattr(self, 'earth'):
      self.earth.update_position(r)

    self.plotter.render()

  def setup_plotter(self, central_widget) -> QWidget:
    # create plotter
    self.plotter = QtInteractor(central_widget)

    # base ref frame
    self.ref_axes = Axes(frame_name='ref', opacity=0.3)
    self.ref_axes.setup(np.eye(3), OPT.GEOMETRY_SCALE, self.plotter)
    if not OPT.show_ref_axes:
      self.ref_axes.toggle_visibility()

    # base body frame
    self.body_axes = Axes(frame_name='body')
    self.body_axes.setup(np.eye(3), OPT.GEOMETRY_SCALE, self.plotter)
    if not OPT.show_body_axes:
      self.body_axes.toggle_visibility()

    # plot satellite com
    self.plotter.add_mesh(pv.Sphere(radius=0.05), color='grey')

    # plot earth
    if OPT.I_R:
      self.earth = Earth()
      self.earth.setup(self.r_list[0], OPT.GEOMETRY_SCALE*OPT.EARTH_SIZE, self.plotter)
      if not OPT.show_earth:
        self.earth.toggle_visibility()

    self.plotter.add_axes()

    # create layout
    plotter_widget = QWidget()
    container = QVBoxLayout(plotter_widget)
    container.addWidget(self.plotter.interactor)

    self.label = QLabel('', plotter_widget)
    self.label.setStyleSheet('color: black;')
    self.label.move(20, 20)
    self.raise_()

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


    # ref axes toggle
    def toggle_raxes(is_checked):
      OPT.show_ref_axes = is_checked
      self.raxes_btn.setText('Hide Ref Axes' if OPT.show_ref_axes else 'Show Ref Axes')

      self.ref_axes.toggle_visibility()

      self.plotter.render()

    self.raxes_btn = QPushButton(
      'Hide Ref Axes' if OPT.show_ref_axes else 'Show Ref Axes',
      checkable=True,
      checked=OPT.show_ref_axes
    )
    self.raxes_btn.toggled.connect(toggle_raxes)


    # body axes toggle
    def toggle_baxes(is_checked):
      OPT.show_body_axes = is_checked
      self.baxes_btn.setText('Hide Body Axes' if OPT.show_body_axes else 'Show Body Axes')

      self.body_axes.toggle_visibility()
      if OPT.show_body_axes: 
        self.body_axes.rotate_mesh(self.dcm_list[self.frame_slider.value()-1])

      self.plotter.render()

    self.baxes_btn = QPushButton(
      'Hide Body Axes' if OPT.show_body_axes else 'Show Body Axes',
      checkable=True,
      checked=OPT.show_body_axes
    )
    self.baxes_btn.toggled.connect(toggle_baxes)


    # satellite body toggle
    def toggle_body_mesh(is_checked):
      self.body_mesh_btn.setText('Hide Satellite' if is_checked else 'Show Satellite')

      if not hasattr(self, 'geometry_data'):
        # initialise body mesh
        geometry_data = read_geometry_data(OPT.FILEPATH_GEOMETRY)
        if not geometry_data:
          with QSignalBlocker(self.body_mesh_btn):
            self.body_mesh_btn.setChecked(False)

          self.body_mesh_btn.setText('Show Satellite')
          return

        OPT.show_body_mesh = True
        self.geometry_data = geometry_data
        self.body_mesh = Body(self.geometry_data)
        self.body_mesh.setup(self.plotter, OPT.show_normals)
        self.body_mesh.rotate_mesh(self.dcm_list[self.frame_slider.value()-1])

        self.norm_btn.setEnabled(True)

      else:
        # toggle visibility of body mesh
        OPT.show_body_mesh = is_checked
        self.body_mesh.toggle_visibility(OPT.show_body_mesh, OPT.show_normals)

        if OPT.show_body_mesh: 
          self.body_mesh.rotate_mesh(self.dcm_list[self.frame_slider.value()-1])
          self.norm_btn.setEnabled(True)
        else:
          self.norm_btn.setEnabled(False)

      self.plotter.render()

    self.body_mesh_btn = QPushButton(
      'Hide Satellite' if OPT.show_body_mesh else 'Show Satellite',
      checkable=True
    )
    self.body_mesh_btn.toggled.connect(toggle_body_mesh)

    # satellite normals toggle
    def toggle_norms(is_checked):
      OPT.show_normals = is_checked
      self.norm_btn.setText('Hide Norms' if OPT.show_normals else 'Show Norms')

      if hasattr(self, 'body_mesh'):
        self.body_mesh.toggle_visibility(OPT.show_body_mesh, OPT.show_normals)

      self.plotter.render()

    self.norm_btn = QPushButton(
      'Hide Norms' if OPT.show_normals else 'Show Norms',
      checkable=True,
      enabled=OPT.show_body_mesh
    )
    self.norm_btn.toggled.connect(toggle_norms)

    self.body_mesh_btn.setChecked(OPT.show_body_mesh)
    self.norm_btn.setChecked(OPT.show_normals)


    # controls ui layout
    playback_layout = QHBoxLayout()
    playback_layout.addWidget(self.play_button)
    playback_layout.addWidget(self.frame_slider)

    toggle_layout = QHBoxLayout()
    toggle_layout.addWidget(self.raxes_btn)
    toggle_layout.addWidget(self.baxes_btn)

    toggle_layout.addWidget(self.body_mesh_btn)
    toggle_layout.addWidget(self.norm_btn)

    return toggle_layout, playback_layout

def main():
  app = QApplication(sys.argv)

  window = MainWindow()
  window.show()

  sys.exit(app.exec())


if __name__ == "__main__":
  main()