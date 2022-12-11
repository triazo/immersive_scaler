Immersive Scaler
===========
Fine tuned automated avatar scaling, for vrchat

**Scaling has changed with VRChat's IK 2.0**

Immersive Scaler supports the new scaling, but must be run again on
old avatars. Play with the 'Custom Arm Ratio' option in options to
make the most of the new scaling options.

## Purpose

VRChat uses avatar scale and proportions to get world vr world size
and virtual height. If those are off it can ruin immersion. Immersive
Scaler is a one click blender plugin to match VRChat scale to your own
world and your own proportions.


Before:

https://user-images.githubusercontent.com/6687043/134242576-035c0031-f532-40ca-a704-7bb4efc69829.mp4



One click in blender later:

https://user-images.githubusercontent.com/6687043/134242292-bbbb7803-377b-440f-8d76-ade58c2176ac.mp4


## Installation

Installation is the same as most other blender plugins. Supports
Blender >=2.81, including 3.0.

Go to the
[releases](https://github.com/triazo/immersive_scaler/releases) page,
and download the latest `.zip` file. Then, in Blender, go to
Edit->Preferences, and select 'Add-ons'. On the top, hit 'Install',
navigate to the downloaded `.zip` file, select, and install it.

On the 'Add-ons' page in preferences, scroll down to '3D View:
Immersive scaler' and select the check box. A tab named 'IMScale'
should now appear on the 3d view toolbar, on the right hand side of
the view.

To test out the development version, see instructions at the bottom.

## Upgrading

While sometims an upgrade will work simply by repeating the
installation process with the newer version, often a full blender
restart is required. Disable the plugin in the Add-ons tab in the
preferences window, install the new version, restart blender, then
re-enable it.

## Usage

First, it's recommended to install the CATS plugin.

Import your avatar, use the CATS fix (no arguments necessary,
I've just observed weird behavior when run against armatures without
this), and hit the 'Rescale Armature' button. Tweak options as necessary.


![UI](https://triazo.net/files/blender_2021-10-05_17-08-04.png)

Options are:

- **Target Height**: The in game height of an avatar. This includes
  extra leg length. The button on the right retrieves the current
  height and sets the target height parameter to match.

- **Leg/Arm Scaling**: If rescaling needs to be done, how much should the
  legs be changed (shortened, most of the time), and how much should
  the arms be changed (lengthened, most of the time). A value of 1
  will only affect the legs, and a value of 0 will only affect the
  arms. This works outside of the range zero to one, but will probably
  look weird.

  This is the first option to tweak if you don't like how your avatar
  looks.

- **Arm Thickness**: When making the arms longer (or shorter), this
  determines how much the other axis should be scaled to match the
  length increase. A value of 1 will keep arm proportions exactly,
  while a value of 0 will give you spagetti arms.

- **Leg Thickness**: When making the legs shorter (or longer), this
  determines how much the other axis should be scaled to match the
  length increase. A value of 1 will keep leg proportions exactly,
  giving you spagetti legs, while a value of 0 will give you fat pancake
  legs.

- **Upper Leg Percentage**: Out of the space between the top of the leg
  and the foot, what percentage should be used by the thigh, vs the
  calf. This helps get the knee in the right place when using full
  body.
  
- **Custom Arm Ratio**: This option corresponds to vrchat's
  `--custom-arm-ratio` launch option. When the number provided here
  matches the number passed as an argument (or the default, 0.4537),
  scale by arm mode should be identical to scale by height mode. This
  option is useful to quickly get an avatar with arms that are the
  right length. The default is vrchat's default but it's reccomended
  to lower it a tiny bit to match your own preference. I personally go
  around 0.43, and 0.415 was used in a previous vrchat beta.

- **Extra Leg Length**: In case no configuration where the avatar's
  feet touch the floor looks any good, you can have the avatar's feet
  and virtual floor be underneath your real floor by a certian amount
  by setting this number to be nonzero. An extra leg length of 1 will
  put the virtual floor one meter below your real floor. This is
  calculated before height scaling so results may be different from
  run to run.

- **Scale to Eyes**: This toggle affects the 'Target Height'
  behaivor. Normally it will scale the model based on the height of
  the highest vertex, but when this toggle is set, it will scale it
  based on the eye height instead. When this is checked, the button to
  get the current height will also respond based on eye height.

- **Bone Overrides**: Immersive scaler has a list of bone names
  preprogrammed, and if your bone isn't detected will throw an
  error. When checked, a list will appear at the bottom of the UI
  letting you manually select the bone to use.

- **Center Model**: When set to true, the model will be centered at
  x,y = 0,0 in blender, as well as moved to the floor. When off,
  the avatar is still moved to the floor z=0.

- **Skip Main Rescale**: Skips the main portion of the rescale, keeping
  avatar proportions as they started. The plugin will remove any space
  between the bottom of the avatar and blender's z=0 plane, and scale
  the height to match.

- **Skip move to floor**: Skips the step where the avatar is moved to the
  floor. It still attempts to do the main rescale and scale the height.

- **Skip Height Scaling**: The avatar will not be scaled to height, and
  will keep the height it had after resizing the legs and moving the
  avatar to the floor.



## Spreading Fingers

There is another function in here for knuckles (index) controller
users to spread fingers. Many armatures have fingers in parallel with
each other when fully open (only with finger tracking), which is an
uncomfortable position for fingers, so this sets the rest pose of your
fingers in what is hopefully a more natural position

- **Spread Factor**: This determines how much the fingers will be
  spread by. A spread factor of 1 is the default behavior and will
  point the finger bones directly away from the head of the wrist
  bone. Higher values will spread the fingers more, and lower values
  will spread the fingers less. A factor of 0 will not move the
  fingers at all.

- **Ignore thumb**: This option prevents the thumb bone from also being moved.

## Hip fix

In some models it helps to shrink the hip bone. This is just a shortcut
to move the hip bone almost all the way to the spine.

## Development version Install

Either clone or download this repository, then create a zip of the
`immersive_scaler` directory. This zip is the same as what's
downloaded from the releases page.

## Contact

If you have any questions, encounter an error, or just want to say hi,
send me a ping on discord at triazo#9607.

If you like this plugin and think it's useful, spread the word!
