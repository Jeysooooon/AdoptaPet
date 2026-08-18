AdoptaPet - Frontend (Flask static server)

Instrucciones rápidas:

1. Construir la imagen (desde la raíz del repo):
   docker build -t adoptapet_frontend:latest ./frontend

2. Levantar con docker-compose (añade el bloque 'frontend' en tu docker-compose.yml o ejecutar directamente):
   docker-compose up -d frontend

3. Acceder en: http://localhost:8000

Notas:
- El frontend hace peticiones a los servicios backend que se asumen corriendo en los puertos 48910-48915 en el host.
- En desarrollo puedes montar el volumen ./frontend:/app y ejecutar "flask run" para recarga en caliente.
