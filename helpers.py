import pyvista as pv

class Frame:
  def __init__(self, frame_name, cols=('red', 'green', 'blue'), labels=('x', 'y', 'z'), opacity=1):
    self.frame_name = frame_name
    self.cols = cols
    self.labels = labels
    self.opacity = opacity

    self.arrow_actor = [None, None, None]
   
  def setup(self, basis_vecs, plotter) -> None:
    for i in range(3):
      arrow = pv.Arrow(direction=basis_vecs[i], shaft_radius=0.04, tip_length=0.2)
      self.arrow_actor[i] = plotter.add_mesh(arrow, color=self.cols[i], label=self.labels[i], opacity=self.opacity, name=f'{self.frame_name}_{i}')

  def rotate_mesh(self, A):  
    # rotate using transpose of attitude (body -> ref)
    for i in range(3):
      self.arrow_actor[i].rotation_from(A.T)