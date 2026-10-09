from dataclasses import dataclass
from pathlib import Path
import sys

@dataclass
class OPT:
  WINDOW_SIZE: tuple[int, int] = (800, 600)

  FILEPATH: Path = Path(sys.executable).resolve().parent
  FILENAME_STATE: str = 'xdata.json'
  FILENAME_GEOMETRY: str = 'geometry.json'
  FILENAME_SURFACE_FORCES: str = 'surfdata.json'
  FILENAME_SUN_POS: str = 'rs.json'

  FILE_AVAILABLE: bool = False
  EARTH_AVAILABLE: bool = False
  GEOMETRY_AVAILABLE: bool = False
  FORCES_AVAILABLE: bool = False
  SUN_AVAILABLE: bool = False

  # simulation stepsize (dt)
  SIMULATION_TIMESTEP: int = 1
  # indices of quaternion, orbital pos, and orbital vel in state data
  I_Q: tuple[int, int] = (6, 10)
  I_R: tuple[int, int] = (0, 3)
  I_V: tuple[int, int] = (3, 6)

  # roughly longest length of satellite, used to resize axes and earth
  GEOMETRY_SCALE: float = 0.3
  # how much bigger the earth/sun is compared to the satellite
  EARTH_SIZE: float = 10
  EARTH_DISTANCE: float = 1.2
  SUN_SIZE: float = 1
  SUN_DISTANCE: float = 100
  # order of magnitude of forces
  AERO_FORCE_SCALE: float = 0.15*10**5
  SRP_FORCE_SCALE: float = 0.3*10**6
  

  autoplay: bool = False
  loop_playback: bool = True
  # how many frames to increment each playback step
  SPEEDS = [1, 2, 5, 10, 20]
  playback_speed: int = 5
  # real time playback in simulation time
  real_time: bool = False
  # keeps track of when to step frame
  real_time_last_update: float = 0
  # how often (ms) that a playback step occurs (17ms = 1/(60fps))
  TIMER_INT: int = 17

  # time hud format
  TIME_FORMATS = ['hr:min:sec', 'min', 'sec']
  time_format = 'hr:min:sec'

  # whether the camera should track the satellite over its orbit
  # the camera angle to use for tracking
  CAM_LABELS = ['Free', 'Satellite', 'Orbital', 'Inertial', 'Down', 'Forward', 'Side']
  tracking_camera: str = 'Orbital'

  # background image/skybox
  BACKGROUNDS = ['Black', 'White', 'Stars']
  background = 'Black'

  show_eci_axes: bool = False
  show_body_axes: bool = False
  show_lvlh_axes: bool = True
  show_axes_labels: bool = True

  show_body_mesh: bool = True
  show_normals: bool = False
  show_aero_f: bool = False
  show_srp_f: bool = True

  show_earth: bool = True
  show_sun: bool = True