import os
import re
import time

import mujoco
import mujoco.viewer

# ---------------------------------------------------------
# AJUSTES QUE PUEDES CAMBIAR
# ---------------------------------------------------------
COLOR_ROBOT = "0.08 0.08 0.08 1"     # negro (rojo verde azul opacidad, de 0 a 1)
COLOR_BLANCO = "0.97 0.97 0.97"      # blanco del cielo y el suelo
COLOR_LINEAS = "0.85 0.85 0.85"      # gris muy claro de las marcas del suelo

CAMARA_DISTANCIA = 1.8               # lo lejos que esta la camara
CAMARA_AZIMUT = 135                  # angulo alrededor del robot
CAMARA_ELEVACION = -20               # altura desde la que mira

VER_FUERZAS_CONTACTO = False         # flechas con la fuerza de cada contacto

# ---------------------------------------------------------
# 1. BUSCAR LA CARPETA DEL GO1
# ---------------------------------------------------------
raiz = os.path.dirname(os.path.abspath(__file__))
carpeta = None
for ruta, carpetas, archivos in os.walk(raiz):
    if "venv" in ruta.split(os.sep):
        continue
    if os.path.basename(ruta) == "unitree_go1" and "scene.xml" in archivos:
        carpeta = ruta
        break

if carpeta is None:
    raise SystemExit("No encuentro la carpeta unitree_go1 dentro de PLASMA-IA.")

print("Carpeta del Go1:", carpeta)

# ---------------------------------------------------------
# 2. LEER LOS ARCHIVOS ORIGINALES
# ---------------------------------------------------------
with open(os.path.join(carpeta, "go1.xml"), "r", encoding="utf-8") as f:
    robot = f.read()

with open(os.path.join(carpeta, "scene.xml"), "r", encoding="utf-8") as f:
    escena = f.read()

# ---------------------------------------------------------
# 3. PINTAR EL ROBOT DE NEGRO
# ---------------------------------------------------------
def pintar_material(m):
    etiqueta = m.group(0)
    if "rgba=" in etiqueta:
        return re.sub(r'rgba="[^"]*"', 'rgba="' + COLOR_ROBOT + '"', etiqueta)
    return etiqueta

robot = re.sub(r"<material[^>]*>", pintar_material, robot)

# ---------------------------------------------------------
# 4. ESCENA BLANCA (cielo y suelo)
# ---------------------------------------------------------
escena = re.sub(r'rgb1="[^"]*"', 'rgb1="' + COLOR_BLANCO + '"', escena)
escena = re.sub(r'rgb2="[^"]*"', 'rgb2="' + COLOR_BLANCO + '"', escena)
escena = re.sub(r'markrgb="[^"]*"', 'markrgb="' + COLOR_LINEAS + '"', escena)
escena = re.sub(r'<rgba haze="[^"]*"', '<rgba haze="1 1 1 1"', escena)

# la escena ahora usa el robot negro
escena = escena.replace('file="go1.xml"', 'file="go1_negro.xml"')

# ---------------------------------------------------------
# 5. RENDIMIENTO: sin reflejos, sin sombras, sin bruma
# ---------------------------------------------------------
def aligerar(texto):
    # quita los reflejos del suelo
    texto = re.sub(r'reflectance="[^"]*"', 'reflectance="0"', texto)

    # las luces dejan de proyectar sombra
    def luz_sin_sombra(m):
        etiqueta = m.group(0)
        if "castshadow" in etiqueta:
            return etiqueta
        return etiqueta.replace("<light", '<light castshadow="false"', 1)

    return re.sub(r"<light[^>]*>", luz_sin_sombra, texto)

escena = aligerar(escena)
robot = aligerar(robot)

# apaga las sombras y la bruma en la parte visual de la escena
if "<visual>" in escena and "<quality" not in escena:
    escena = escena.replace(
        "<visual>",
        '<visual>\n    <quality shadowsize="0"/>\n    <map haze="0"/>',
        1,
    )

# ---------------------------------------------------------
# 6. GUARDAR LOS ARCHIVOS NUEVOS
# ---------------------------------------------------------
with open(os.path.join(carpeta, "go1_negro.xml"), "w", encoding="utf-8") as f:
    f.write(robot)

destino = os.path.join(carpeta, "scene_plasma.xml")
with open(destino, "w", encoding="utf-8") as f:
    f.write(escena)

print("Archivos creados: go1_negro.xml y scene_plasma.xml")

# ---------------------------------------------------------
# 7. ABRIR EL VISOR
# ---------------------------------------------------------
modelo = mujoco.MjModel.from_xml_path(destino)
datos = mujoco.MjData(modelo)
mujoco.mj_resetDataKeyframe(modelo, datos, 0)   # postura inicial de pie

with mujoco.viewer.launch_passive(modelo, datos) as visor:
    visor.cam.distance = CAMARA_DISTANCIA
    visor.cam.azimuth = CAMARA_AZIMUT
    visor.cam.elevation = CAMARA_ELEVACION

    visor.opt.flags[mujoco.mjtVisFlag.mjVIS_CONTACTFORCE] = VER_FUERZAS_CONTACTO

    while visor.is_running():
        mujoco.mj_step(modelo, datos)
        visor.sync()
        time.sleep(modelo.opt.timestep)