from pathlib import Path

from PyQt6.QtWidgets import *


class RenderSettingsDialog(QDialog):
  def __init__(
    self,
    start_frame=0,
    end_frame=100,
    output_type="MP4",
    output_dir=Path.home() / "Downloads",
    parent=None,
    quality=8,
    speed=1
  ):
    super().__init__(parent)

    self.setWindowTitle("Render Settings")
    self.setMinimumWidth(400)

    # Main layout
    layout = QVBoxLayout(self)

    # Frame range
    frame_group = QGroupBox("Frame Range")
    frame_layout = QFormLayout(frame_group)

    self.start_frame = QSpinBox()
    self.start_frame.setRange(1, 1_000_000)
    self.start_frame.setValue(start_frame)

    self.end_frame = QSpinBox()
    self.end_frame.setRange(1, 1_000_000)
    self.end_frame.setValue(end_frame)

    self.frame_speed = QSpinBox()
    self.frame_speed.setRange(1, 1_000_000)
    self.frame_speed.setValue(speed)

    frame_layout.addRow("Start frame:", self.start_frame)
    frame_layout.addRow("End frame:", self.end_frame)
    frame_layout.addRow("Speed (sim frames per vid frame):", self.frame_speed)

    layout.addWidget(frame_group)

    # Output settings
    output_group = QGroupBox("Output")
    output_layout = QFormLayout(output_group)

    self.output_type = QComboBox()
    self.output_type.addItems(["MP4", "GIF"])
    self.output_type.setCurrentText(output_type.upper())

    output_layout.addRow("Format:", self.output_type)

    # Output directory
    directory_layout = QHBoxLayout()

    self.output_dir = QLineEdit(output_dir)
    self.output_dir.setPlaceholderText("Choose output directory...")

    browse_button = QPushButton("Browse...")
    browse_button.clicked.connect(self.browse_directory)

    directory_layout.addWidget(self.output_dir)
    directory_layout.addWidget(browse_button)

    output_layout.addRow("Directory:", directory_layout)

    # Quality
    self.quality_int = QSpinBox()
    self.quality_int.setRange(1, 9)
    self.quality_int.setValue(quality)

    output_layout.addRow("MP4 Quality:", self.quality_int)

    # FPS
    self.fps_int = QSpinBox()
    self.fps_int.setRange(1, 120)
    self.fps_int.setValue(30)

    output_layout.addRow("FPS:", self.fps_int)

    layout.addWidget(output_group)

    # info
    layout.addWidget(QLabel("Note: Render resolution depends on the current window size.\nUse fullscreen for best resolution"))

    # OK / Cancel buttons
    buttons = QDialogButtonBox(
      QDialogButtonBox.StandardButton.Ok |
      QDialogButtonBox.StandardButton.Cancel
    )
    buttons.accepted.connect(self.accept)
    buttons.rejected.connect(self.reject)

    layout.addWidget(buttons)

  def browse_directory(self):
    directory = QFileDialog.getExistingDirectory(
      self,
      "Select Output Directory",
      self.output_dir.text() or str(Path.home()),
    )

    if directory:
      self.output_dir.setText(directory)

  def accept(self):
    if self.start_frame.value() > self.end_frame.value():
      from PyQt6.QtWidgets import QMessageBox

      QMessageBox.warning(
        self,
        "Invalid Frame Range",
        "The start frame must not exceed the end frame.",
      )
      return

    if not self.output_dir.text().strip():
      from PyQt6.QtWidgets import QMessageBox

      QMessageBox.warning(
        self,
        "Missing Output Directory",
        "Please select an output directory.",
      )
      return

    super().accept()

  def get_settings(self):
    return {
      "start_frame": self.start_frame.value(),
      "end_frame": self.end_frame.value(),
      "output_type": self.output_type.currentText().lower(),
      "output_dir": self.output_dir.text().strip(),
      "quality": self.quality_int.value(),
      "speed": self.frame_speed.value(),
      "fps": self.fps_int.value()
    }