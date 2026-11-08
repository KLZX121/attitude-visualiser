import time

from render_settings import RenderSettingsDialog
from qtpy.QtCore import Qt, QTimer
from PyQt6.QtGui import QDoubleValidator, QImage, QGuiApplication
from qtpy.QtWidgets import *

from helpers import *


def setup_controls(main_window, central_layout, plotter_widget, OPT, persistent_settings):
  def save_persistent_setting(name):
    value = getattr(OPT, name)
    persistent_settings.setValue(name, value)


  # play pause button
  def toggle_play(is_checked):
    OPT.autoplay = is_checked

    if is_checked:
      OPT.real_time_last_update = time.perf_counter()
      main_window.play_button.setText('Pause')
    else:
      main_window.play_button.setText('Play')
  
  main_window.play_button = QPushButton('Pause' if OPT.autoplay else 'Play', checkable=True, checked=OPT.autoplay)
  main_window.play_button.toggled.connect(toggle_play)

  # toggle playback looping
  def toggle_loop(is_checked):
    OPT.loop_playback = is_checked
    save_persistent_setting('loop_playback')

  main_window.loop_btn = QPushButton('Loop', checkable=True, checked=OPT.loop_playback)
  main_window.loop_btn.toggled.connect(toggle_loop)

  # playback speed
  def set_playback_speed(label):
    if label == 'Real Time':
      OPT.real_time = True
      OPT.playback_speed = 1
    else:
      OPT.real_time = False
      OPT.playback_speed = int(label[:-1])

    save_persistent_setting('playback_speed')
    save_persistent_setting('real_time')      

  main_window.speed_combo = QComboBox()
  main_window.speed_combo.addItem('Real Time')
  main_window.speed_combo.addItems([f'{speed}x' for speed in OPT.SPEEDS])
  main_window.speed_combo.setCurrentText('Real Time' if OPT.real_time else f'{OPT.playback_speed}x')
  main_window.speed_combo.currentTextChanged.connect(set_playback_speed)

  # playback slider
  main_window.update_frame(1)
  main_window.frame_slider = QSlider(Qt.Orientation.Horizontal)
  main_window.frame_slider.setRange(1, main_window.N_FRAMES)
  main_window.frame_slider.valueChanged.connect(main_window.update_frame)

  # step frames:
  def step_frame(is_timer, frame_increment):
    if is_timer and not OPT.autoplay:
      return
    elif is_timer and OPT.real_time:
      curr_time = time.perf_counter()
      if (curr_time - OPT.real_time_last_update) >= OPT.simulation_timestep:
        OPT.real_time_last_update = curr_time
      else:
        return
    
    current_frame = main_window.frame_slider.value()
    next_frame = current_frame + frame_increment

    if OPT.loop_playback:
      next_frame = next_frame % main_window.N_FRAMES
      if next_frame < 1:
        next_frame = main_window.N_FRAMES
    elif next_frame > main_window.N_FRAMES:
      next_frame = main_window.N_FRAMES
      main_window.play_button.toggle()

    main_window.frame_slider.setValue(next_frame)

  main_window.step_pos_btn = QPushButton('>')
  main_window.step_neg_btn = QPushButton('<')
  main_window.step_pos_btn.clicked.connect(lambda: step_frame(False, OPT.playback_speed))
  main_window.step_neg_btn.clicked.connect(lambda: step_frame(False, -OPT.playback_speed))
  main_window.step_pos_btn.setFixedWidth(30)
  main_window.step_neg_btn.setFixedWidth(30)

  # autoplay functionality
  main_window.timer = QTimer(main_window)
  main_window.timer.setSingleShot(True)
  main_window.timer.setTimerType(Qt.TimerType.PreciseTimer)

  def tick():
    t0 = time.perf_counter()

    if OPT.autoplay:
      if OPT.real_time:
        # jump ahead by however many sim steps of wall time have passed
        n = int((t0 - OPT.real_time_last_update) / OPT.simulation_timestep)
        if n >= 1:
          OPT.real_time_last_update += n * OPT.simulation_timestep
          step_frame(False, min(n, 1000))
      else:
        step_frame(True, OPT.playback_speed)

    spent_ms = (time.perf_counter() - t0) * 1000
    main_window.timer.start(max(1, int(OPT.TIMER_INT - spent_ms))) # always yield to the event loop

  main_window.timer.timeout.connect(tick)
  main_window.timer.start(OPT.TIMER_INT)

  # change simulation timestep
  def update_dt(text):
    if text:
      OPT.simulation_timestep = float(text)
      save_persistent_setting('simulation_timestep')

  main_window.dt_input = QLineEdit()
  main_window.dt_input.setValidator(QDoubleValidator(bottom=0))
  main_window.dt_input.setText(str(OPT.simulation_timestep))
  main_window.dt_input.textChanged.connect(update_dt)
  main_window.dt_input.setMaximumWidth(80)

  # camera tracking mode
  def switch_cam(label):
    OPT.tracking_camera = label
    main_window.update_frame()
    save_persistent_setting('tracking_camera')

  main_window.cam_combo = QComboBox()
  main_window.cam_combo.addItems(OPT.CAM_LABELS)
  main_window.cam_combo.setCurrentText(OPT.tracking_camera)
  main_window.cam_combo.currentTextChanged.connect(switch_cam)

  # background switching
  def switch_bg(label):
    OPT.background = label
    main_window.change_bg(OPT.background)
    save_persistent_setting('background')

  main_window.bg_combo = QComboBox()
  main_window.bg_combo.addItems(OPT.BACKGROUNDS)
  main_window.bg_combo.setCurrentText(OPT.background)
  main_window.bg_combo.currentTextChanged.connect(switch_bg)

  # time format
  def switch_time_format(label):
    OPT.time_format = label
    main_window.update_frame()
    save_persistent_setting('time_format')

  main_window.time_combo = QComboBox()
  main_window.time_combo.addItems(OPT.TIME_FORMATS)
  main_window.time_combo.setCurrentText(OPT.time_format)
  main_window.time_combo.currentTextChanged.connect(switch_time_format)

  # directory
  def open_dir_dialog():
    dir_str = QFileDialog.getExistingDirectory(dir=str(OPT.filepath))

    if dir_str:
      dir_path = Path(dir_str).resolve()
      OPT.filepath = dir_path
      main_window.dir_btn.setText(f'/{str(OPT.filepath.name)}')
      save_persistent_setting('filepath')


  main_window.dir_btn = QPushButton(f'/{str(OPT.filepath.name)}')
  main_window.dir_btn.clicked.connect(open_dir_dialog)

  def reread_dir():
    if OPT.filepath:
      main_window.plotter.close()
      QApplication.processEvents()

      main_window.setup_window(read_data=True)
  main_window.read_btn = QPushButton('Read Data')
  main_window.read_btn.clicked.connect(reread_dir)


  # earth toggle
  def toggle_earth(is_checked):
    OPT.show_earth = is_checked
    main_window.earth.toggle_visibility(OPT.show_earth)
    main_window.update_frame()
    save_persistent_setting('show_earth')

  main_window.earth_btn = QPushButton('Earth', checkable=True, checked=OPT.show_earth)
  main_window.earth_btn.toggled.connect(toggle_earth)

  # sun toggle
  def toggle_sun(is_checked):
    OPT.show_sun = is_checked
    main_window.sun.toggle_visibility(main_window.plotter, OPT.show_sun)
    main_window.update_frame()
    save_persistent_setting('show_sun')

  main_window.sun_btn = QPushButton('Sun', checkable=True, checked=OPT.show_sun)
  main_window.sun_btn.toggled.connect(toggle_sun)

  # ref eci axes toggle
  def toggle_raxes(is_checked):
    OPT.show_eci_axes = is_checked
    main_window.eci_axes.toggle_visibility(OPT.show_eci_axes, OPT.show_axes_labels)
    main_window.update_frame()
    save_persistent_setting('show_eci_axes')

  main_window.raxes_btn = QPushButton(
    'ECI Axes',
    checkable=True,
    checked=OPT.show_eci_axes
  )
  main_window.raxes_btn.toggled.connect(toggle_raxes)

  # body axes toggle
  def toggle_baxes(is_checked):
    OPT.show_body_axes = is_checked
    main_window.body_axes.toggle_visibility(OPT.show_body_axes, OPT.show_axes_labels)
    main_window.update_frame()
    save_persistent_setting('show_body_axes')

  main_window.baxes_btn = QPushButton(
    'Body Axes',
    checkable=True,
    checked=OPT.show_body_axes
  )
  main_window.baxes_btn.toggled.connect(toggle_baxes)

  # lvlh axes toggle
  def toggle_lvlh(is_checked):
    OPT.show_lvlh_axes = is_checked
    main_window.lvlh_axes.toggle_visibility(OPT.show_lvlh_axes, OPT.show_axes_labels)
    main_window.update_frame()
    save_persistent_setting('show_lvlh_axes')

  main_window.laxes_btn = QPushButton(
    'LVLH Axes',
    checkable=True,
    checked=OPT.show_lvlh_axes
  )
  main_window.laxes_btn.toggled.connect(toggle_lvlh)

  # sun vector toggle
  def toggle_sun_vector(is_checked):
    OPT.show_sun_vector = is_checked
    main_window.sun_vector.toggle_visibility(OPT.show_sun_vector, OPT.show_axes_labels)
    main_window.update_frame()
    save_persistent_setting('show_sun_vector')

  main_window.sun_vector_btn = QPushButton(
    'Sun Vector',
    checkable=True,
    checked=OPT.show_sun_vector
  )
  main_window.sun_vector_btn.toggled.connect(toggle_sun_vector)

  # axes labels
  def toggle_labels(is_checked):
    OPT.show_axes_labels = is_checked
    main_window.eci_axes.toggle_visibility(OPT.show_eci_axes, OPT.show_axes_labels)
    main_window.body_axes.toggle_visibility(OPT.show_body_axes, OPT.show_axes_labels)
    if OPT.EARTH_AVAILABLE:
      main_window.lvlh_axes.toggle_visibility(OPT.show_lvlh_axes, OPT.show_axes_labels)
    if OPT.SUN_AVAILABLE:
      main_window.sun_vector.toggle_visibility(OPT.show_sun_vector, OPT.show_axes_labels)
    main_window.update_frame()
    save_persistent_setting('show_axes_labels')

  main_window.labels_btn = QPushButton('Axes Labels', checkable=True, checked=OPT.show_axes_labels)
  main_window.labels_btn.toggled.connect(toggle_labels)


  # satellite body toggle
  def toggle_body_mesh(is_checked):
    OPT.show_body_mesh = is_checked
    main_window.body_mesh.toggle_visibility(OPT)

    main_window.norm_btn.setEnabled(OPT.show_body_mesh)
    main_window.edge_btn.setEnabled(OPT.show_body_mesh)
    main_window.transparency_btn.setEnabled(OPT.show_body_mesh)
    main_window.lighting_btn.setEnabled(OPT.show_body_mesh)
    main_window.forces_combo.setEnabled(OPT.show_body_mesh)

    main_window.update_frame()
    save_persistent_setting('show_body_mesh')

  main_window.body_mesh_btn = QPushButton(
    'Satellite',
    checkable=True
  )
  main_window.body_mesh_btn.toggled.connect(toggle_body_mesh)

  # satellite normals toggle
  def toggle_norms(is_checked):
    OPT.show_normals = is_checked

    if hasattr(main_window, 'body_mesh'):
      main_window.body_mesh.toggle_visibility(OPT)

    main_window.update_frame()
    save_persistent_setting('show_normals')

  main_window.norm_btn = QPushButton(
    'Normals',
    checkable=True,
    enabled=OPT.show_body_mesh
  )
  main_window.norm_btn.toggled.connect(toggle_norms)

  # satellite mesh edges
  def toggle_edges(is_checked):
    OPT.show_edges = is_checked

    if hasattr(main_window, 'body_mesh'):
      main_window.body_mesh.toggle_visibility(OPT)

    main_window.update_frame()
    save_persistent_setting('show_edges')
  main_window.edge_btn = QPushButton(
    'Edges',
    checkable=True,
    enabled=OPT.show_body_mesh
  )
  main_window.edge_btn.toggled.connect(toggle_edges)

  # transparency
  def toggle_transparency(is_checked):
    OPT.transparent = is_checked

    if hasattr(main_window, 'body_mesh'):
      main_window.body_mesh.toggle_visibility(OPT)

    main_window.update_frame()
    save_persistent_setting('transparent')
  main_window.transparency_btn = QPushButton(
    'Transparency',
    checkable=True,
    enabled=OPT.show_body_mesh
  )
  main_window.transparency_btn.toggled.connect(toggle_transparency)

  # lighting
  def toggle_lighting(is_checked):
    OPT.lighting = is_checked

    if hasattr(main_window, 'body_mesh'):
      main_window.body_mesh.toggle_visibility(OPT)

    main_window.update_frame()
    save_persistent_setting('lighting')
  main_window.lighting_btn = QPushButton(
    'Lighting',
    checkable=True,
    enabled=OPT.show_body_mesh
  )
  main_window.lighting_btn.toggled.connect(toggle_lighting)

  # satellite forces combo box
  def change_forces(option):
    OPT.show_aero_f = any(sub in option for sub in ['Aero', 'All'])
    OPT.show_srp_f = any(sub in option for sub in ['SRP', 'All'])

    main_window.body_mesh.toggle_visibility(OPT)

    main_window.update_frame()
    save_persistent_setting('show_aero_f')
    save_persistent_setting('show_srp_f')

  main_window.forces_combo = QComboBox()
  main_window.forces_combo.addItems(['None', 'All', 'Aero', 'SRP'])
  main_window.forces_combo.currentTextChanged.connect(change_forces)


  if OPT.GEOMETRY_AVAILABLE:
    main_window.body_mesh_btn.setChecked(OPT.show_body_mesh)
    main_window.norm_btn.setChecked(OPT.show_normals)
    main_window.edge_btn.setChecked(OPT.show_edges)
    main_window.transparency_btn.setChecked(OPT.transparent)

    if OPT.FORCES_AVAILABLE:
      if OPT.show_srp_f and OPT.show_aero_f:
        current_force = 'All'
      elif OPT.show_aero_f:
        current_force = 'Aero'
      elif OPT.show_srp_f:
        current_force = 'SRP'
      else:
        current_force = 'None'
      main_window.forces_combo.setCurrentText(current_force)

      main_window.lighting_btn.setChecked(OPT.lighting)


  # render button
  def open_render_dialog():
    dialog = RenderSettingsDialog(
      start_frame=1,
      end_frame=main_window.N_FRAMES,
      output_type="MP4",
      output_dir=str(Path.home() / "Downloads"),
      parent=main_window,
      speed=OPT.playback_speed
    )

    if dialog.exec():
      settings = dialog.get_settings()
      main_window.render_animation(settings)

  main_window.render_btn = QPushButton('Render')
  main_window.render_btn.clicked.connect(open_render_dialog)

  # screenshot button
  def take_screenshot():
    img = main_window.plotter.screenshot(return_img=True)
    img = np.ascontiguousarray(img)
    h, w, ch = img.shape
    qimg = QImage(img.data, w, h, ch * w, QImage.Format_RGB888).copy()
    QGuiApplication.clipboard().setImage(qimg)

    main_window.ss_btn.setText('Copied!')
    main_window.ss_timer.start(3000)

  main_window.ss_btn = QPushButton('Screenshot')
  main_window.ss_btn.clicked.connect(take_screenshot)
  main_window.ss_timer = QTimer(main_window)
  main_window.ss_timer.setSingleShot(True)
  main_window.ss_timer.timeout.connect(lambda: main_window.ss_btn.setText('Screenshot'))

  top_layout = QHBoxLayout()
  top_layout.addWidget(QLabel('Camera:'), 1)
  top_layout.addWidget(main_window.cam_combo, 2)
  top_layout.addWidget(QLabel('Background:'), 1)
  top_layout.addWidget(main_window.bg_combo, 2)
  top_layout.addWidget(QLabel('Time Format:'), 1)
  top_layout.addWidget(main_window.time_combo, 2)
  top_layout.addWidget(QLabel('Directory:'), 1)
  top_layout.addWidget(main_window.dir_btn, 2)
  add_divider(top_layout, orientation=QFrame.VLine)
  top_layout.addWidget(main_window.read_btn, 2)
  top_layout.addStretch(100)


  left_layout = QVBoxLayout()
  left_layout.addSpacing(5)
  add_divider(left_layout, spacing_before=0)
  left_layout.addWidget(main_window.labels_btn)
  left_layout.addSpacing(5)
  left_layout.addWidget(main_window.raxes_btn)
  if OPT.EARTH_AVAILABLE:
    left_layout.addWidget(main_window.laxes_btn)
  left_layout.addWidget(main_window.baxes_btn)
  if OPT.SUN_AVAILABLE:
    left_layout.addWidget(main_window.sun_vector_btn)
  add_divider(left_layout)
  if OPT.EARTH_AVAILABLE:
    left_layout.addWidget(main_window.earth_btn)
  if OPT.SUN_AVAILABLE:
    left_layout.addWidget(main_window.sun_btn)
  if OPT.GEOMETRY_AVAILABLE:
    add_divider(left_layout)
    left_layout.addWidget(main_window.body_mesh_btn)
    left_layout.addWidget(main_window.norm_btn)
    left_layout.addWidget(main_window.edge_btn)
    left_layout.addWidget(main_window.transparency_btn)
    if OPT.FORCES_AVAILABLE:
      left_layout.addWidget(main_window.lighting_btn)
      left_layout.addWidget(main_window.forces_combo)
  left_layout.addStretch()


  bot_top = QHBoxLayout()
  bot_top.addWidget(main_window.play_button)
  bot_top.addWidget(main_window.step_neg_btn)
  bot_top.addWidget(main_window.step_pos_btn)
  bot_top.addWidget(main_window.frame_slider)

  bot_bot = QHBoxLayout()
  bot_bot.addWidget(main_window.loop_btn)
  bot_bot.addWidget(QLabel('Playback Speed:'))
  bot_bot.addWidget(main_window.speed_combo)
  bot_bot.addWidget(QLabel('Simulation Timestep (s):'))
  bot_bot.addWidget(main_window.dt_input)
  add_divider(bot_bot, orientation=QFrame.VLine)
  bot_bot.addWidget(main_window.render_btn)
  bot_bot.addWidget(main_window.ss_btn)
  bot_bot.addStretch()

  bottom_layout = QVBoxLayout()
  bottom_layout.addLayout(bot_top)
  add_divider(bottom_layout, spacing_before=0, spacing_after=0)
  bottom_layout.addLayout(bot_bot)

  # middle layout
  middle_layout = QHBoxLayout()
  middle_layout.addLayout(left_layout)
  middle_layout.addWidget(plotter_widget, 1)

  # add everything to central layout
  central_layout.addLayout(top_layout)
  central_layout.addLayout(middle_layout)
  central_layout.addLayout(bottom_layout)

  return top_layout, bottom_layout, left_layout