import time
import sys

from types import SimpleNamespace

import pyvista as pv
import numpy as np

from helpers import Frame, read_file

#TODO: add export option (and settings)
#TODO: add simulation time display option
#TODO: add background

# GENERAL SETTINGS

# simulation timestep per frame (s)
DT = 1


SETTINGS = SimpleNamespace()

SETTINGS.WINDOW_SIZE = (800, 600)
SETTINGS.AUTOPLAY = False
SETTINGS.LOOP_PLAYBACK = False


# WIDGET SETTINGS
# relative size
BUTTON_SIZE = 0.04
BUTTON_GAP = 0.01

SLIDER_POS = [(0.05 + BUTTON_SIZE, 0.08), (0.95, 0.08)]

# ms between playback frames (17 ms = 1/ 60 fps)
PLAYBACK_SPEED = 17

# EXPORT SETTINGS
# exported video fps
FPS_VID = 60
# desired number of simulation seconds in one video second (s)
T_SIM_VID  = 60*5

# number of simulation frames in one video second
N_VID_S = np.floor(T_SIM_VID / DT)
# number of simulation frames in one video frame
N_VID_F = N_VID_S / FPS_VID



def main():
  A_list = read_file()
  N_FRAMES = len(A_list)
  
  pl, body_frame = setup_plotter()

  
  def step(i):
    # update body frame 
    body_frame.rotate_mesh(A_list[i])

    pl.render()

  """
    t0 = time.perf_counter()
    t_last = t0

    # render video
    if i % N_VID_F == 0:
      # could add text here 
      pl.write_frame()

    t_curr = time.perf_counter()
    nonlocal t_last
    if i == 0 or i == n_frames-1 or (t_curr - t_last) >= 3:
      print(f'{((i+1)/n_frames)*100:.2f}%: {i+1} / {n_frames} {t_curr-t0:.2f}s elapsed')
      t_last = t_curr
  """


  # playback slider

  slider = pl.add_slider_widget(
    callback=lambda val: step(int(val)-1),
    rng=(1, N_FRAMES),
    value=1,
    fmt="%.0f",
    interaction_event='always',
    style='modern',
    pointa=SLIDER_POS[0],
    pointb=SLIDER_POS[1],
  )

  # setup play/pause button

  def toggle_play(is_checked):
    SETTINGS.AUTOPLAY = is_checked

  
  button = pl.add_checkbox_button_widget(
    callback=toggle_play,
    value=SETTINGS.AUTOPLAY,
    border_size=0,
    color_off='grey',
    color_on='green'
  )

  # reposition button relative to window size since it has absolute positioning

  def repos_button(*_):
    win_width, win_height = pl.window_size

    abs_button_size = BUTTON_SIZE * min(win_width, win_height)

    abs_button_gap = (BUTTON_GAP * win_width, BUTTON_GAP * win_height)

    x0 = SLIDER_POS[0][0]*win_width - abs_button_size - abs_button_gap[0]
    y0 = SLIDER_POS[0][1]*win_height - abs_button_size/2

    bounds = [x0, x0 + abs_button_size, y0, y0 + abs_button_size, 0, 0]

    button.GetRepresentation().PlaceWidget(bounds)

  pl.iren.add_observer('ConfigureEvent', repos_button)

  repos_button()


  # add button play/pause functionality

  def timer_callback(step):
    if not SETTINGS.AUTOPLAY:
      return
    
    current_frame = slider.GetRepresentation().GetValue()

    next_frame = current_frame + 1
    if SETTINGS.LOOP_PLAYBACK:
      next_frame = (current_frame % N_FRAMES) + 1
    elif next_frame >= N_FRAMES:
      return

    slider.GetRepresentation().SetValue(next_frame)
    slider.InvokeEvent('InteractionEvent')

  pl.iren.initialize()

  pl.add_timer_event(
    max_steps=sys.maxsize,
    duration=PLAYBACK_SPEED,
    callback=timer_callback
  )


  pl.show()

  # render loop
  #pl.open_movie('rotation.mp4', framerate=FPS_VID, quality=8)

  #for i in range(n_frames):
  #  if AUTOPLAY: step(i)
    
  #pl.close()



def setup_plotter() -> tuple[pv.Plotter, Frame]:
  # setup plotter mesh
  pl = pv.Plotter(window_size=SETTINGS.WINDOW_SIZE)

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

  return pl, body_frame


if __name__ == "__main__":
  main()