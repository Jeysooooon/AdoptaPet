"""
Script de bootstrap para crear un usuario administrador en el microservicio Usuarios.

Uso:
  - Definir en el .env (o en el entorno) las variables:
      ADMIN_EMAIL - correo del administrador (requerido)
      ADMIN_PASSWORD - contraseña (requerido)
      ADMIN_NAME - nombre a mostrar (opcional, default: 'Admin')
  - Ejecutar desde la carpeta Usuarios:
      python create_admin.py

El script crea el usuario con rol='admin' si no existe y mostrará un JWT para pruebas.
No se guardan ni se muestran contraseñas reales en commits; este script usa variables de entorno locales.
"""

import os
import sys
from dotenv import load_dotenv

# Asegurarse que la carpeta actual (Usuarios) esté en sys.path para importar app.py
load_dotenv()

try:
    # Importar la app y modelos desde el paquete de Usuarios
    from app import app, db, Usuario, generar_token
except Exception as e:
    print("Error importando el microservicio Usuarios. Ejecuta este script desde la carpeta Usuarios o ajusta PYTHONPATH.")
    print("Detalle:", e)
    sys.exit(1)

ADMIN_EMAIL = os.getenv('ADMIN_EMAIL')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')
ADMIN_NAME = os.getenv('ADMIN_NAME', 'Admin')

if not ADMIN_EMAIL or not ADMIN_PASSWORD:
    print("Faltan variables de entorno. Define ADMIN_EMAIL y ADMIN_PASSWORD en tu .env o entorno y vuelve a ejecutar.")
    print("Ejemplo (PowerShell): $env:ADMIN_EMAIL='admin@ejemplo.com'; $env:ADMIN_PASSWORD='Cambiar123'; python create_admin.py")
    sys.exit(1)

with app.app_context():
    existing = Usuario.query.filter_by(correo=ADMIN_EMAIL).first()
    if existing:
        print(f"Usuario con correo {ADMIN_EMAIL} ya existe con rol '{existing.rol}'. No se creó nada.")
        print("Si deseas forzar actualización de rol, hazlo manualmente en la base de datos o modifica el script.")
        # Mostrar token útil para tests
        try:
            token = generar_token(existing)
            print("JWT para ese usuario (útil para pruebas):")
            print(token)
        except Exception:
            pass
        sys.exit(0)

    usuario = Usuario(nombre=ADMIN_NAME, correo=ADMIN_EMAIL)
    usuario.password = ADMIN_PASSWORD
    usuario.rol = 'admin'
    try:
        db.session.add(usuario)
        db.session.commit()
        print(f"Administrador creado: {ADMIN_EMAIL} (nombre: {ADMIN_NAME})")
        try:
            token = generar_token(usuario)
            print("Token JWT (válido por el tiempo configurado en Usuarios):")
            print(token)
            print("Cópialo y úsalo en la cabecera 'Authorization: Bearer <token>' para probar endpoints protegidos.")
        except Exception as e:
            print("Usuario creado pero no se pudo generar token automáticamente:", e)
    except Exception as e:
        db.session.rollback()
        print("Error al crear el usuario admin:", e)
        sys.exit(1)
