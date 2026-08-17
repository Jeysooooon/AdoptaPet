import subprocess
import sys
import time
import os

# Lista de los microservicios, sus carpetas y sus puertos correspondientes
MICROSERVICES = [
    {"name": "Usuarios", "dir": "Usuarios", "port": 48910},
    {"name": "Adopciones", "dir": "db_adopciones", "port": 48911},
    {"name": "Donaciones", "dir": "db_donaciones", "port": 48912},
    {"name": "Eventos", "dir": "db_eventos", "port": 48913},
    {"name": "Mascotas", "dir": "db_mascotas", "port": 48914},
    {"name": "Notificaciones", "dir": "db_notificaciones", "port": 48915},
]

processes = []

print("==================================================")
print(" Iniciando Sistema de Microservicios - AdoptsPet")
print("==================================================")

for service in MICROSERVICES:
    app_path = os.path.join(service["dir"], "app.py")
    if not os.path.exists(app_path):
        print(f" Error: No se encontró el archivo {app_path}")
        continue

    print(f" Encendiendo {service['name']} en puerto {service['port']}...")
    
    # Ejecuta cada app.py en un proceso independiente de Python
    proc = subprocess.Popen(
        [sys.executable, "app.py"],
        cwd=service["dir"]
    )
    processes.append(proc)
    time.sleep(1.5)  # Espera un momento antes de lanzar el siguiente

print("\n ¡Todos los microservicios se han iniciado con éxito!")
print("Presiona CTRL + C en esta terminal para apagarlos todos a la vez.\n")

try:
    # Mantiene el script corriendo para capturar el apagado manual
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\n Apagando todos los microservicios...")
    for proc in processes:
        proc.terminate()
    print(" ¡Sistema apagado de manera segura!")