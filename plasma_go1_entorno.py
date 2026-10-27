import os
import time

import mujoco
import numpy as np
import gymnasium as gym
from gymnasium import spaces


def buscar_escena():
    """Busca scene_plasma.xml (el que creaste con modelo_plasma_go1.py)."""
    raiz = os.path.dirname(os.path.abspath(__file__))
    for ruta, carpetas, archivos in os.walk(raiz):
        carpetas[:] = [c for c in carpetas if c != "venv"]
        if os.path.basename(ruta) == "unitree_go1" and "scene_plasma.xml" in archivos:
            return os.path.join(ruta, "scene_plasma.xml")
    raise SystemExit("No encuentro scene_plasma.xml. Ejecuta antes modelo_plasma_go1.py una vez.")


class Go1Entorno(gym.Env):
    """El Go1 aprende a mantenerse de pie y despues a avanzar."""

    def __init__(self):
        super().__init__()
        self.model = mujoco.MjModel.from_xml_path(buscar_escena())
        self.data = mujoco.MjData(self.model)

        # El robot decide 50 veces por segundo (cada 0.02 s)
        self.salto = max(1, round(0.02 / self.model.opt.timestep))
        self.dt = self.salto * self.model.opt.timestep

        # Postura de pie (viene en el modelo, "keyframe" numero 0)
        if self.model.nkey > 0:
            self.pos_inicial = self.model.key_qpos[0].copy()
            self.ctrl_inicial = self.model.key_ctrl[0].copy()
        else:
            self.pos_inicial = self.model.qpos0.copy()
            self.ctrl_inicial = np.zeros(self.model.nu)

        self.rango = self.model.actuator_ctrlrange.copy()
        self.escala_accion = 0.3     # cuanto se puede alejar de la postura de pie (radianes)
        self.max_pasos = 500         # 500 pasos x 0.02 s = 10 segundos por intento
        self.pasos = 0

        # ACCIONES: un numero entre -1 y 1 para cada motor
        self.action_space = spaces.Box(-1.0, 1.0, shape=(self.model.nu,), dtype=np.float32)

        # OBSERVACION: altura, inclinacion, angulos de patas y todas las velocidades
        tamano_obs = (self.model.nq - 2) + self.model.nv
        self.observation_space = spaces.Box(-np.inf, np.inf, shape=(tamano_obs,), dtype=np.float32)

    def _observacion(self):
        return np.concatenate([self.data.qpos[2:], self.data.qvel]).astype(np.float32)

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        mujoco.mj_resetData(self.model, self.data)
        self.data.qpos[:] = self.pos_inicial
        self.data.ctrl[:] = self.ctrl_inicial
        # pequeno ruido en las patas para que cada intento sea un poco distinto
        ruido = self.np_random.uniform(-0.02, 0.02, size=self.data.qpos[7:].shape)
        self.data.qpos[7:] += ruido
        mujoco.mj_forward(self.model, self.data)
        self.pasos = 0
        return self._observacion(), {}

    def step(self, accion):
        accion = np.clip(np.asarray(accion, dtype=np.float64), -1.0, 1.0)

        # la accion es un ajuste sobre la postura de pie
        ctrl = self.ctrl_inicial + accion * self.escala_accion
        ctrl = np.clip(ctrl, self.rango[:, 0], self.rango[:, 1])
        self.data.ctrl[:] = ctrl

        x_antes = self.data.qpos[0]
        for _ in range(self.salto):
            mujoco.mj_step(self.model, self.data)
        velocidad = (self.data.qpos[0] - x_antes) / self.dt   # metros por segundo hacia delante

        altura = self.data.qpos[2]
        cuat = self.data.qpos[3:7]
        vertical = 1.0 - 2.0 * (cuat[1] ** 2 + cuat[2] ** 2)  # 1 = derecho, 0 = tumbado

        caido = altura < 0.15 or vertical < 0.5

        # RECOMPENSA
        recompensa = 1.0                              # premio por seguir de pie en cada paso
        recompensa += 2.0 * velocidad                 # premio por avanzar
        recompensa -= 0.02 * float(np.sum(accion**2)) # pequeno castigo por mover los motores a lo loco

        self.pasos += 1
        terminado = bool(caido)
        cortado = self.pasos >= self.max_pasos
        return self._observacion(), float(recompensa), terminado, cortado, {}


# Prueba rapida: python plasma_go1_entorno.py
if __name__ == "__main__":
    env = Go1Entorno()
    print("Motores (acciones):", env.action_space.shape[0])
    print("Numeros que ve el robot (observacion):", env.observation_space.shape[0])
    print("Pasos de fisica por decision:", env.salto)

    env.reset(seed=0)
    inicio = time.time()
    n = 2000
    for _ in range(n):
        _, _, terminado, cortado, _ = env.step(env.action_space.sample())
        if terminado or cortado:
            env.reset()
    segundos = time.time() - inicio
    print("Velocidad:", round(n / segundos), "pasos por segundo")
    print("Todo correcto")