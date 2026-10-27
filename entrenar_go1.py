import os
import time

from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.monitor import Monitor

from plasma_go1_entorno import Go1Entorno

# ---------------------------------------------------------
# AJUSTES QUE PUEDES CAMBIAR
# ---------------------------------------------------------
MINUTOS_MAXIMOS = 30            # se para solo al pasar este tiempo (480 = una noche de 8 horas)
PASOS_OBJETIVO = 5_000_000      # tope de pasos (casi siempre parara antes por el tiempo)
GUARDAR_CADA = 20_000           # guarda el progreso cada tantos pasos


class LimiteYGuardado(BaseCallback):
    """Vigila el reloj y guarda el progreso cada cierto tiempo."""

    def __init__(self, minutos, cada):
        super().__init__()
        self.limite = minutos * 60
        self.cada = cada
        self.inicio = None

    def _on_training_start(self):
        self.inicio = time.time()

    def _on_step(self):
        if self.n_calls % self.cada == 0:
            self.model.save("go1_ppo")
        # si devuelve False, el entrenamiento se para
        return (time.time() - self.inicio) < self.limite


entorno = Monitor(Go1Entorno())

if os.path.exists("go1_ppo.zip"):
    print("Encuentro un Go1 ya entrenado: sigo desde donde lo dejamos.")
    modelo = PPO.load("go1_ppo", env=entorno, device="cpu")
else:
    print("Empiezo un Go1 nuevo.")
    modelo = PPO("MlpPolicy", entorno, verbose=1, device="cpu")

print(f"Entrenando como maximo {MINUTOS_MAXIMOS} minutos. Para pararlo antes: Ctrl+C")
inicio = time.time()

try:
    modelo.learn(
        total_timesteps=PASOS_OBJETIVO,
        callback=LimiteYGuardado(MINUTOS_MAXIMOS, GUARDAR_CADA),
        reset_num_timesteps=False,
    )
except KeyboardInterrupt:
    print("Parado a mano con Ctrl+C.")

# ---------------------------------------------------------
# GUARDAR EL CONOCIMIENTO DE LA SESION
# ---------------------------------------------------------
# 1) La ultima version (la que sigue entrenando y la que ve el visor)
modelo.save("go1_ppo")

# 2) Una copia de esta sesion, con los pasos acumulados en el nombre
copia = f"go1_ppo_{modelo.num_timesteps}_pasos"
modelo.save(copia)

minutos = (time.time() - inicio) / 60
print(f"=== Terminado: {minutos:.1f} minutos. Pasos totales acumulados: {modelo.num_timesteps} ===")
print("Guardado en: go1_ppo.zip  (ultima version)")
print(f"Copia de esta sesion: {copia}.zip")