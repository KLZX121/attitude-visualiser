# attitude-visualiser
Simple PyVista app for visualising and animating spacecraft attitude given the attitude state over time

### Conventions

- Shuster/JPL quaternions
- Passive reference-to-body attitude

### Settings
**Camera Tracking Modes**
  
  `free` Camera is free to move.

  `orbital` Tracks satellite and rotates relative to Earth. Useful for viewing attitude relative to the Earth and tracking disturbances.

  `inertial` Tracks satellite and remains fixed in inertial space. Useful for viewing attitude relative to ECI or the Sun.

  `down` Tracks satellite in a top-down view with satellite velocity to the top of the screen.

  `forward` Tracks satellite from behind with satellite velocity into the screen.

  `side` Tracks satellite from the side with satellite velocity to the right of the screen.


