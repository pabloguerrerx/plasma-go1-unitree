import time

import mujoco
import mujoco.viewer
from stable_baselines3 import PPO

from plasma_go1_entorno import Go1Entorno

entorno = Go1Entorno()
modelo = PPO.load("go1_ppo", device="cpu")
obs, _ = entorno.reset()

with mujoco.viewer.launch_passive(entorno.model, entorno.data) as visor:
    visor.cam.type = mujoco.mjtCamera.mjCAMERA_TRACKING   # la camara sigue al robot
    visor.cam.trackbodyid = 1
    visor.cam.distance = 2.0
    visor.cam.azimuth = 135
    visor.cam.elevation = -20
    visor.opt.flags[mujoco.mjtVisFlag.mjVIS_CONTACTPOINT] = False

    while visor.is_running():
        accion, _ = modelo.predict(obs, deterministic=True)
        obs, recompensa, terminado, cortado, _ = entorno.step(accion)
        visor.sync()
        time.sleep(entorno.dt)
        if terminado or cortado:
            obs, _ = entorno.reset()