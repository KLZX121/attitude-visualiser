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
  QGridLayout,
  QVBoxLayout,
  QWidget,
)

@dataclass
class SETTINGS:
  FILEPATH_ATTITUDE: str = 'qdata.txt'
  FILEPATH_GEOMETRY: str = 'geometry.json'
  WINDOW_SIZE: tuple[int, int] = (800, 600)

  autoplay: bool = False
  LOOP_PLAYBACK: bool = True
  PLAYBACK_SPEED: int = 5
  TIMER_INT: int = 17

  show_centroids: bool = True
  show_normals: bool = True

  show_body_axes: bool = True
  show_ref_axes: bool = True
  show_body_mesh: bool = True


#TODO: add export option (and settings)
#TODO: add simulation time/frame display option
#TODO: add background


class MainWindow(QMainWindow):
  def __init__(self):
    super().__init__()

    self.setWindowTitle('Attitude Visualiser v0.1')
    self.resize(SETTINGS.WINDOW_SIZE[0], SETTINGS.WINDOW_SIZE[1])

    # read data
    self.dcm_list = read_attitude_data(SETTINGS.FILEPATH_ATTITUDE)
    self.N_FRAMES = len(self.dcm_list)

    # create central widget and layout
    central_widget = QWidget()
    central_layout = QVBoxLayout(central_widget)
    self.setCentralWidget(central_widget)

    # setup PyVista viewport widget
    self.setup_plotter(central_widget)
    central_layout.addWidget(self.plotter.interactor, 5)

    # setup controls widget
    controls_layout = self.setup_controls()
    central_layout.addLayout(controls_layout, 1)

  def closeEvent(self, event):
    self.plotter.close()
    event.accept()

  def setup_plotter(self, central_widget):
    # create plotter
    self.plotter = QtInteractor(central_widget)

    # base ref frame
    self.base_frame = Frame(frame_name='ref', opacity=0.3)
    self.base_frame.setup(np.eye(3), self.plotter)

    # base body frame
    self.body_frame = Frame(frame_name='body')
    self.body_frame.setup(np.eye(3), self.plotter)

    # plot centre
    self.plotter.add_mesh(pv.Sphere(radius=0.05), color='grey')

    #pl.background_color = 'black'
    self.plotter.add_axes(viewport=(0, 0.8, 0.2, 1))

  def setup_controls(self) -> QGridLayout:
    # play pause button
    def toggle_play(is_checked):
      SETTINGS.autoplay = is_checked

      if is_checked:
        self.play_button.setText('Pause')
      else:
        self.play_button.setText('Play')
    
    self.play_button = QPushButton('Pause' if SETTINGS.autoplay else 'Play')
    self.play_button.setCheckable(True)
    self.play_button.setChecked(SETTINGS.autoplay)
    self.play_button.toggled.connect(toggle_play)

    # playback slider
    def set_frame(frame):
      dcm = self.dcm_list[frame-1]
      if SETTINGS.show_body_axes:
        self.body_frame.rotate_mesh(dcm)

      if SETTINGS.show_body_mesh and hasattr(self, 'body_mesh'):
        self.body_mesh.rotate_mesh(dcm)

      self.plotter.render()
    
    set_frame(1)
    self.frame_slider = QSlider(Qt.Orientation.Horizontal)
    self.frame_slider.setRange(1, self.N_FRAMES)
    self.frame_slider.valueChanged.connect(set_frame)

    # autoplay functionality
    def timer_callback():
      if not SETTINGS.autoplay:
        return
      
      current_frame = self.frame_slider.value()
  
      next_frame = current_frame + SETTINGS.PLAYBACK_SPEED
      if SETTINGS.LOOP_PLAYBACK:
        next_frame = (current_frame % self.N_FRAMES) + SETTINGS.PLAYBACK_SPEED
      elif next_frame >= self.N_FRAMES:
        return
  
      self.frame_slider.setValue(next_frame)
    
    self.timer = QTimer(self)
    self.timer.timeout.connect(timer_callback)
    self.timer.start(SETTINGS.TIMER_INT)

    # render satellite body
    def toggle_satellite(is_checked):
      self.show_body_btn.setText('Hide Satellite' if is_checked else 'Show Satellite')

      if not hasattr(self, 'geometry_data'):
        # initialise body mesh
        geometry_data = read_geometry_data(SETTINGS.FILEPATH_GEOMETRY)
        if not geometry_data:
          with QSignalBlocker(self.show_body_btn):
            self.show_body_btn.setChecked(False)

          self.show_body_btn.setText('Show Satellite')
          return

        SETTINGS.show_body_mesh = True
        self.geometry_data = geometry_data
        self.body_mesh = Body(self.geometry_data)
        self.body_mesh.setup(self.plotter, SETTINGS.show_centroids, SETTINGS.show_normals)
        self.body_mesh.rotate_mesh(self.dcm_list[self.frame_slider.value()-1])

      else:
        # toggle visibility of body mesh
        SETTINGS.show_body_mesh = is_checked
        self.body_mesh.toggle_visibility()

        if SETTINGS.show_body_mesh: 
          self.body_mesh.rotate_mesh(self.dcm_list[self.frame_slider.value()-1])

        self.plotter.update()

    self.show_body_btn = QPushButton('Show Satellite')
    self.show_body_btn.setCheckable(True)
    self.show_body_btn.toggled.connect(toggle_satellite)
    self.show_body_btn.setChecked(SETTINGS.show_body_mesh)

    # controls ui layout
    controls_layout = QGridLayout()
    controls_layout.addWidget(self.play_button, 1, 0)
    controls_layout.addWidget(self.frame_slider, 1, 1)
    controls_layout.addWidget(self.show_body_btn, 2, 0)

    return controls_layout


def main():
  app = QApplication(sys.argv)

  window = MainWindow()
  window.show()

  sys.exit(app.exec())


if __name__ == "__main__":
  main()