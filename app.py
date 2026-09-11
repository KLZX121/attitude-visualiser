import sys
import pyvista as pv
import numpy as np
from types import SimpleNamespace
from helpers import *

from pyvistaqt import QtInteractor
from qtpy.QtCore import Qt, QTimer
from qtpy.QtWidgets import (
  QApplication,
  QMainWindow,
  QPushButton,
  QSlider,
  QGridLayout,
  QVBoxLayout,
  QHBoxLayout,
  QWidget,
  QLabel
)


SETTINGS = SimpleNamespace()

SETTINGS.FILEPATH = 'qdata.txt'
SETTINGS.WINDOW_SIZE = (800, 600)
SETTINGS.AUTOPLAY = False
SETTINGS.LOOP_PLAYBACK = True
SETTINGS.PLAYBACK_SPEED = 5
SETTINGS.TIMER_INT = 17


#TODO: add export option (and settings)
#TODO: add simulation time/frame display option
#TODO: add background


class MainWindow(QMainWindow):
  def __init__(self):
    super().__init__()

    self.setWindowTitle('Attitude Visualiser v0.1')
    self.resize(SETTINGS.WINDOW_SIZE[0], SETTINGS.WINDOW_SIZE[1])

    # read data
    self.dcm_list = self.read_attitude_data(SETTINGS.FILEPATH)
    self.N_FRAMES = len(self.dcm_list)

    # create central widget and layout
    central_widget = QWidget()
    central_layout = QVBoxLayout(central_widget)
    self.setCentralWidget(central_widget)

    # setup PyVista viewport widget
    self.plotter, self.ref_frame, self.body_frame = self.setup_plotter(central_widget)
    central_layout.addWidget(self.plotter.interactor, 5)

    # setup controls widget
    controls_layout = self.setup_controls()
    central_layout.addLayout(controls_layout, 1)

  def closeEvent(self, event):
    self.plotter.close()
    event.accept()

  def setup_plotter(self, central_widget) -> tuple[QtInteractor, Frame, Frame]:
    # create plotter
    pl = QtInteractor(central_widget)

    # base ref frame
    base_frame = Frame(frame_name='ref', opacity=0.3)
    base_frame.setup(np.eye(3), pl)

    # base body frame
    body_frame = Frame(frame_name='body')
    body_frame.setup(np.eye(3), pl)

    # plot centre
    pl.add_mesh(pv.Sphere(radius=0.05), color='grey')

    #pl.background_color = 'black'
    pl.add_axes(viewport=(0, 0.8, 0.2, 1))

    return pl, base_frame, body_frame

  def setup_controls(self) -> QGridLayout:
    # play pause button
    def toggle_play(is_checked):
      SETTINGS.AUTOPLAY = is_checked

      if is_checked:
        self.play_button.setText('Pause')
      else:
        self.play_button.setText('Play')
    
    self.play_button = QPushButton('Pause' if SETTINGS.AUTOPLAY else 'Play')
    self.play_button.setCheckable(True)
    self.play_button.setChecked(SETTINGS.AUTOPLAY)
    self.play_button.toggled.connect(toggle_play)

    # playback slider
    def set_frame(frame):
      self.body_frame.rotate_mesh(self.dcm_list[frame-1])
      self.plotter.render()
    
    set_frame(1)
    self.frame_slider = QSlider(Qt.Orientation.Horizontal)
    self.frame_slider.setRange(1, self.N_FRAMES)
    self.frame_slider.valueChanged.connect(set_frame)

    # autoplay funcionality
    def timer_callback():
      if not SETTINGS.AUTOPLAY:
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

    controls_layout = QGridLayout()
    controls_layout.addWidget(self.play_button, 1, 0)
    controls_layout.addWidget(self.frame_slider, 1, 1)

    return controls_layout

  def read_attitude_data(self, filepath) -> np.ndarray:
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


def main():
  app = QApplication(sys.argv)

  window = MainWindow()
  window.show()

  sys.exit(app.exec())


if __name__ == "__main__":
  main()