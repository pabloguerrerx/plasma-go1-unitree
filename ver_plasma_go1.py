import time

import mujoco
import mujoco.viewer
from stable_baselines3 import PPO

from plasma_go1_entorno import Go1Entorno

# Tecla para pausar / reanudar (barra espaciadora)
TECLA_PAUSA = 32
pausado = False


def al_pulsar_tecla(tecla):
    """Se ejecuta cada vez que pulsas una tecla dentro del visor."""
    global pausado
    if tecla == TECLA_PAUSA:
        pausado = not pausado
        print("⏸  PAUSADO" if pausado else "▶  REANUDADO")


entorno = Go1Entorno()
modelo = PPO.load("go1_ppo", device="cpu")
obs, _ = entorno.reset()

with mujoco.viewer.launch_passive(
    entorno.model, entorno.data, key_callback=al_pulsar_tecla
) as visor:
    visor.cam.type = mujoco.mjtCamera.mjCAMERA_TRACKING   # la camara sigue al robot
    visor.cam.trackbodyid = 1
    visor.cam.distance = 2.0
    visor.cam.azimuth = 135
    visor.cam.elevation = -20

    # Ocultar las ayudas visuales de contacto (discos amarillos y flechas)
    visor.opt.flags[mujoco.mjtVisFlag.mjVIS_CONTACTPOINT] = False
    visor.opt.flags[mujoco.mjtVisFlag.mjVIS_CONTACTFORCE] = False

    print("Pulsa ESPACIO dentro del visor para pausar o reanudar.")

    while visor.is_running():
        if pausado:
            # El robot queda congelado, pero puedes seguir girando la camara
            visor.sync()
            time.sleep(0.02)
            continue

        accion, _ = modelo.predict(obs, deterministic=True)
        obs, recompensa, terminado, cortado, _ = entorno.step(accion)
        visor.sync()
        time.sleep(entorno.dt)
        if terminado or cortado:
            obs, _ = entorno.reset()