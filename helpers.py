import numpy as np
import pyvista as pv

# returns dcm list
def read_file(filepath=r'qdata.txt') -> np.ndarray:
  # formatted as a n x 4 csv
  q_list = np.loadtxt(filepath, delimiter=',')

  # dt = 1 s

  # compute dcms
  A_list = []
  
  for q in q_list:
    # input quaternion (scalar first, shuster/JPL convention)
    q = q / np.linalg.norm(q)

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

      A = (qs**2 - np.linalg.norm(qv)**2)*np.eye(3) - 2*qs*skew(qv) + 2*np.outer(qv, qv)
      return A

    A = q_to_dcm(q)
    A_list.append(A)

  return A_list

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