import code, sys, threading, importlib, time
sys.path.append('../fbt-resize')
import fbt_resize

def reload_thread(golist):
    while golist[0] == 1:
        time.sleep(1)
        importlib.reload(fbt_resize)

def console_thread():
    golist=[1] # ok I know it isn't threadsafe but there's no real way
               # this can break
    t = threading.Thread(target=reload_thread, args=(golist,))
    t.start()
    code.interact(local=locals())
    golist[0]=0
    t.join()

threading.Thread(target = console_thread).start()

sys.exit()


# Docs on what to add to the blender console to reload this
import sys
import importlib
sys.path.add("/home/triazo/projects/blender-vrcavatars/fbt-resize")
import fbt_resize
