Immersive Scaler
===========
Fine tuned automated avatar scaling, for vrchat

## Purpose

VRChat uses avatar scale and proportions to get world vr world size
and virtual height. If those are off it can ruin immersion. Immersive
Scaler is a one click blender plugin to match VRChat scale to your own
world and your own proportions.


Before:

https://user-images.githubusercontent.com/6687043/134242576-035c0031-f532-40ca-a704-7bb4efc69829.mp4



One click in blender later:

https://user-images.githubusercontent.com/6687043/134242292-bbbb7803-377b-440f-8d76-ade58c2176ac.mp4




## Usage

First, install the CATS plugin. There is currently a hard
dependency on the pose mode operations.

Import your avatar, use the CATS fix (no arguments necessary,
I've just observed weird behavior when run against armatures without
this), and hit the 'Rescale Armature' button. Tweak options as necessary.


![UI](https://triazo.net/files/blender_2021-09-21_16-42-01.png)

Options are:

- **Target Height**: The in game height of an avatar. This includes extra
  leg length.

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

- **Thigh Percentage**: Out of the space between the top of the leg
  and the foot, what percentage should be used by the thigh, vs the
  calf. This helps get the knee in the right place when using full
  body.

- **Extra Leg Length**: In case no configuration where the avatar's feet
  touch the floor looks any good, you can have the avatar's feet and
  virtual floor be underneath your real floor by a certian amount by
  setting this number to be nonzero. An extra leg length of 1 will put
  the virtual floor one meter below your real floor.

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

## Hip fix

In some models it helps to shrink the hip bone. This is just a shortcut
to move the hip bone almost all the way to the spine.
