Immersive Scaler
===========
Fine tuned automated avatar scaling, for vrchat

## Purpose

VRChat uses avatar scale and proportions to get world vr world size
and virtual height. If those are off it can ruin immersion. Immersive
Scaler is a one click blender plugin to match VRChat scale to your own
world and your own proportions.

Before:
![Unscaled Avatar](https://github.com/triazo/avatar_resize/blob/master/Static/Unscaled-1.m4v?raw=true)

One click in blender later:
![Scaled Avatar](https://github.com/triazo/avatar_resize/blob/master/Static/Scaled-1.m4v?raw=true)



## Usage

First, install the CATS plugin. There is currently a hard
dependency on the pose mode operations.

Import your avatar, use the CATS fix (no arguments necessary, I've just observed weird behavior when run against armatures without this), and hit the 'rescale avatar' button.

Options are:

- Target Height: The in game height of an avatar. This includes extra
  leg length.

- Arm to Leg Ratio: If rescaling needs to be done, how much should the
  legs be changed (shortened, most of the time), and how much should
  the arms be changed (lengthened, most of the time). A value of 1
  will only affect the legs, and a value of 0 will only affect the
  arms. This works outside of the range zero to one, but will probably
  look weird.

- Limb Thickness: In many cases, fat legs or spagetti arms look weird,
  so this option will also scale the girth of the limbs along with the
  length. A value of 1 will do no scaling and a value of 0 will do the
  same amount of scaling of girth as is being applied to the
  length. This works outside of the range zero to one, but will
  probably look weird.

- Extra Leg Length: In case no configuration where the avatar's feet
  touch the floor looks any good, you can have the avatar's feet and
  virtual floor be underneath your real floor by a certian amount by
  setting this number to be nonzero. An extra leg length of 1 will put
  the virtual floor one meter below your real floor.

- Scale Hand: Sets if the hand should be lengthened and widened along
  with the arm. In many cases skinny long hands at the end of spagetti
  arms looks even weirder than regular hands on the end of spagetti
  arms, this is off by default.


## Spreading Fingers

There is another function in here for knuckles (index) controller
users to spread fingers. Most armatures have fingers in parallel with
each other when fully open (only with finger tracking), which is an
uncomfortable position for fingers, so this sets the rest pose of your
fingers in what is hopefully a more natural position