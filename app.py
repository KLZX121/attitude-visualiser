import sys

import pyvista as pv
from pyvistaqt import QtInteractor
from qtpy.QtWidgets import (
  QApplication,
  QMainWindow,
  QPushButton,
  QVBoxLayout,
  QWidget,
)


class MainWindow(QMainWindow):
  def __init__(self):
    super().__init__()

    self.setWindowTitle("PyVista App")
    self.resize(1000, 700)

    # Central widget and layout
    central_widget = QWidget()
    layout = QVBoxLayout(central_widget)
    self.setCentralWidget(central_widget)

    # PyVista viewport
    self.plotter = QtInteractor(central_widget)
    layout.addWidget(self.plotter.interactor)

    # Normal Qt controls
    self.button = QPushButton("Reset camera")
    self.button.clicked.connect(self.plotter.reset_camera)
    layout.addWidget(self.button)

    # Initial scene
    mesh = pv.Cube()
    self.plotter.add_mesh(mesh, color="lightblue", show_edges=True)
    self.plotter.add_axes()
    self.plotter.reset_camera()

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