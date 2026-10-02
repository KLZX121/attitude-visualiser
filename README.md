# Attitude Visualiser
Python app for visualising and animating spacecraft attitude given the attitude state over time. Designed for use with the [ADCS simulation software](https://github.com/KLZX121/AUStronauts-ADCS) from the [UNSW AUStronauts CubeSat mission](https://unswaustronauts.vercel.app/).

Attitude and other relevant data is read from user given JSON files.

### Features
**Attitude**
* View satellite attitude as static frames at each timestep or as an animation over a simulation time period
* Includes ECI, and Body frame axes

**Orbit**
* View satellite orbital position relative to the Earth
* Includes LVLH axes and Earth object

**Satellite Geometry and Disturbances**
* View satellite geometry and panels, along with panel disturbance forces
* Includes satellite geometry and aerodynamic drag and solar radiation pressure (SRP)

**Sun**
* View satellite attitude relative to the Sun
* Includes Sun object and lighting effects


### Settings
Settings are available for switching background colour, toggling on/off the various axes and objects, and animation playback controls.

**Camera Tracking Modes**
  
  * `free` Camera is free to move.

  * `satellite` Tracks satellite and remains fixed to the body frame. Useful for viewing disturbances on satellite panels.

  * `orbital` Tracks satellite and remains fixed to the orbital frame. Useful for viewing attitude relative to the Earth.

  * `inertial` Tracks satellite and remains fixed to the inertial frame. Useful for viewing attitude relative to ECI or the Sun.

  * `down` Tracks satellite in a top-down view with satellite velocity to the top of the screen.

  * `forward` Tracks satellite from behind with satellite velocity into the screen.

  * `side` Tracks satellite from the side with satellite velocity to the right of the screen.


### Input JSON Files
Place correctly named and formatted JSON files within the same directory as the app. See below for [examples](#example-files).

*xdata.json* - Required file for attitude and optionally including orbital data. Given as a 2D array: list of state vectors, with Shuster/JPL format ECI->Body scalar first quaternions, and optional ECI orbital position and velocity. It is important to define the indices of these values in the configuration file. Each state vector represents the state at subsequent timesteps. 

For example, with the indices defined as: I_Q = (0, 4), I_R = (4, 7), I_V = (7, 10), then let X_i = [qs, qx, qy, qz, rx, ry, rz, vx, vy, vz] be the state vector at timestep i. Then, for a simulation with 3 timesteps, `xdata.json` would be: `[X_1, X_2, X_3]`

*geometry.json* - Optional file for satellite geometry visualisation. Given as an object with: `{n_surfaces: int, surfaces: {name: str, vertices: int[3][]}[] }`. The file `generate_geometry.py` will generate an example 3U CubeSat.

*surfdata.json* - Optional file for satellite panel disturbance forces. Given as a list of objects representing the forces and torques acting on each satellite panel at each timestep: `{a: {f: int[3][], t: int[3][]}, s: {f: int[3][], t: int[3][]}}[]]`. `a.f`
and `a.t` contain a list of aerodynamic forces and torques for each panel, and `s.f` and `s.t` do the same for SRP forces and torques.

*rs.json* - Optional file for Sun position. Given as a 2D array: list of position vectors (ECI) at each timestep: `int[3][]`.

#### Example Files
These are the first two timesteps of an example simulation from a 3U CubeSat.

**xdata.json**

Indices are `I_R = (0, 3), I_V = (3, 6), I_Q = (6, 10)`. Note also that there are additional states from indices 10 - 15 that are ignored.
```
[
	[
		3169.9434358372891, -3078.19580245602, 5153.7748100884019,
		6.3488150978125724, 4.0265329738166837, -1.4982762837030741,
		-0.29534713196140178, 0.90929990196077415, 0.22970313900889833,
		-0.1821544066602836, 0, 0, 0, 0, 0, 0
	],
	[
		3176.2902302138064, -3074.1673094107618, 5152.2732509745283,
		6.3447723079087472, 4.0304522608751592, -1.5048416245409377,
		-0.29534713180786804, 0.909299901839022, 0.22970313920630855,
		-0.18215440726806031, -6.1449242463864891e-22, -2.6736029352991113e-9,
		0, 6.1449242463864891e-22, 2.6736029352991113e-9, 0
	],
  ...
]
```

**geometry.json**

This is generated from `generate_geometry.py`. Note that only the `vertices` field is required within the surface objects.

```
{
	"n_surfaces": 10,
	"surfaces": [
		{
			"name": "body_z_pos",
			"vertices": [
				[0.05, 0.05, 0.17025],
				[0.05, -0.05, 0.17025],
				[-0.05, -0.05, 0.17025],
				[-0.05, 0.05, 0.17025]
			],
			"normal": [0, 0, 1],
			"area": 0.010000000000000002,
			"centroid": [0.0, 0.0, 0.17025],
			"Cd": 2,
			"Ca": 0.12,
			"Crs": 0.8,
			"Crd": 0.08
		},
		{
			"name": "body_z_neg",
			"vertices": [
				[0.05, 0.05, -0.17025],
				[0.05, -0.05, -0.17025],
				[-0.05, -0.05, -0.17025],
				[-0.05, 0.05, -0.17025]
			],
			"normal": [0, 0, -1],
			"area": 0.010000000000000002,
			"centroid": [0.0, 0.0, -0.17025],
			"Cd": 2,
			"Ca": 0.12,
			"Crs": 0.8,
			"Crd": 0.08
		},
    ...
  ]
}

```

**surfdata.json**

```
[
	{
		"a": {
			"f": [
				[0, 0, 0],
				[0, 0, 0],
				[0, 0, 0],
				[0, 0, 0],
				[0, 0, 0],
				[0, 0, 0],
				[0, 0, 0],
				[0, 0, 0],
				[0, 0, 0],
				[0, 0, 0]
			],
			"t": [
				[0, 0, 0],
				[0, 0, 0],
				[0, 0, 0],
				[0, 0, 0],
				[0, 0, 0],
				[0, 0, 0],
				[0, 0, 0],
				[0, 0, 0],
				[0, 0, 0],
				[0, 0, 0]
			]
		},
		"s": {
			"f": [
				[0, 0, 0],
				[0, 0, 0],
				[0, 0, 0],
				[0, 0, 0],
				[0, 0, 0],
				[0, 0, 0],
				[0, 0, 0],
				[0, 0, 0],
				[0, 0, 0],
				[0, 0, 0]
			],
			"t": [
				[0, 0, 0],
				[0, 0, 0],
				[0, 0, 0],
				[0, 0, 0],
				[0, 0, 0],
				[0, 0, 0],
				[0, 0, 0],
				[0, 0, 0],
				[0, 0, 0],
				[0, 0, 0]
			]
		}
	},
	{
		"a": {
			"f": [
				[0, 0, -0],
				[
					-3.9259954997046363e-10, -2.9111842347972644e-26,
					6.9023249807252567e-14
				],
				[
					-7.6036358193015e-6, -5.6382093983438409e-22,
					1.3368014676494285e-9
				],
				[0, 0, -0],
				[
					-5.6382093983438409e-22, -4.1808163850873537e-38,
					9.9125823194846829e-26
				],
				[0, 0, -0],
				[
					-7.6036358193015013e-6, -5.6382093983438418e-22,
					1.3368014676494287e-9
				],
				[0, 0, -0],
				[
					-7.6036358193015013e-6, -5.6382093983438418e-22,
					1.3368014676494287e-9
				],
				[0, 0, -0]
			],
			"t": [
				[-0, 0, 0],
				[-4.9562911597423428e-27, 6.6840073382471444e-11, 0],
				[0, -6.6840073382471431e-11, -2.8191046991719208e-23],
				[-0, 0, -0],
				[4.956291159742342e-27, -0, 2.8191046991719208e-23],
				[0, 0, 0],
				[
					1.3368014676494286e-10, -6.6840073382471431e-11,
					7.6036358193015015e-7
				],
				[-0, 0, 0],
				[
					-1.3368014676494286e-10, -6.6840073382471431e-11,
					-7.6036358193015015e-7
				],
				[0, 0, 0]
			]
		},
		"s": {
			"f": [
				[
					-6.8374764090992558e-11, 2.551567330694464e-9,
					-7.8583523616138331e-9
				],
				[0, -0, 0],
				[
					-3.8948052947376276e-10, 7.4821858872279638e-10,
					-2.3281607172982967e-10
				],
				[-0, -0, 0],
				[0, -0, 0],
				[
					-7.4821858872279648e-10, 2.5909447103568883e-7,
					-8.6880867610146511e-9
				],
				[
					-3.8948052947376281e-10, 7.4821858872279648e-10,
					-2.3281607172982972e-10
				],
				[-0, -0, 0],
				[
					-3.8948052947376281e-10, 7.4821858872279648e-10,
					-2.3281607172982972e-10
				],
				[-0, -0, 0]
			],
			"t": [
				[-4.3440433805073252e-10, -1.1640803586491485e-11, 0],
				[0, -0, -0],
				[-0, 1.1640803586491485e-11, 3.7410929436139822e-11],
				[0, 0, 0],
				[0, 0, -0],
				[4.3440433805073257e-10, 0, -3.7410929436139828e-11],
				[
					-2.3281607172982972e-11, 1.1640803586491486e-11,
					7.6358982383516115e-11
				],
				[0, -0, 0],
				[
					2.3281607172982972e-11, 1.1640803586491486e-11,
					-1.5371235112364528e-12
				],
				[0, -0, -0]
			]
		}
	},
  ...
]
```

**rs.json**

Note that the magnitude of the vectors here is ignored within the app.
```
[
	[-6.2959011651237249e7, 1.2718089444075212e8, 5.5124497443555787e7],
	[-6.2959038323933147e7, 1.2718088322894175e8, 5.5124492583394125e7],
  ...
]
```


