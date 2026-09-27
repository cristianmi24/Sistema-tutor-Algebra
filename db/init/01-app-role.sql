-- Ejecutado automáticamente por docker compose al crear el contenedor de PostgreSQL local.
-- Crea el rol de aplicación con el mínimo privilegio necesario (nunca usar 'postgres' desde la app).
CREATE ROLE sti_app LOGIN PASSWORD 'sti_app_dev_password';
CREATE DATABASE sti_dev OWNER sti_app;
CREATE DATABASE sti_test OWNER sti_app;
