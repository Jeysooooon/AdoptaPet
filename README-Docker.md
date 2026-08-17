Instrucciones para levantar la arquitectura "Database per Service" con docker-compose

Resumen:
- Cada microservicio se ejecuta en su propia carpeta (db_mascotas, db_adopciones, db_donaciones, db_eventos, db_notificaciones, Usuarios).
- Cada microservicio tiene su propio archivo de variables para Docker: `.env.docker` (ya creado en cada carpeta).
- Cada microservicio usa su propia base de datos MySQL contenida en un contenedor distinto (mysql_mascotas, mysql_adopciones, ...).

Requisitos:
- Docker y docker-compose instalados en la máquina de desarrollo.
- Puerto 48910-48915 y 33060-33065 libres en el host (o ajustar en docker-compose.yml).

Comandos:
1) En la raíz del proyecto (donde está docker-compose.yml) ejecutar:

   docker-compose up

   Esto descargará las imágenes de MySQL y Python y levantará los contenedores. Cada contenedor Python ejecutará `pip install -r requirements.txt` desde su carpeta y posteriormente `python app.py`.

2) Verificar los endpoints (ejemplos):
- Usuarios:  http://localhost:48910/
- Adopciones: http://localhost:48911/
- Donaciones: http://localhost:48912/
- Eventos: http://localhost:48913/
- Mascotas: http://localhost:48914/
- Notificaciones: http://localhost:48915/

Notas importantes:
- Los archivos `.env.docker` creados contienen valores de ejemplo para facilitar el arranque local. Reemplazar SECRET_KEY y JWT_SECRET_KEY por valores seguros si se va a exponer el entorno.
- Los servicios siguen manteniendo sus archivos `.env` originales (usados al ejecutar localmente sin Docker). El cambio para Docker no sobreescribe esos `.env`; Docker usa los `.env.docker` a través de la clave `env_file`.
- Si se desea usar credenciales/puertos distintos, editar `docker-compose.yml` y los `.env.docker` correspondientes.

Qué cambios se hicieron para cumplir "Database per Service":
- Se crearon bases de datos MySQL independientes (contenedores) para cada microservicio.
- Se proporcionaron `.env.docker` con DATABASE_URL apuntando al respectivo contenedor MySQL.
- Se añadió `docker-compose.yml` para orquestar todos los servicios y sus bases de datos con un solo comando.

Siguientes pasos (recomendado):
- Revisar cada servicio para confirmar que no existan joins SQL que mezclen datos entre dominios; en este proyecto las comunicaciones inter-dominio ya se implementaron mediante llamadas HTTP en los servicios que lo requieren (por ejemplo, Adopciones -> Mascotas).
- Añadir Dockerfiles si se desea optimizar la imagen y evitar volver a instalar dependencias en cada inicio.

Autor: Copilot CLI runtime in VS Code (acción automática para reorganizar la arquitectura)