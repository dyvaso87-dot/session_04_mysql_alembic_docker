CREATE DATABASE escuela;

CREATE TABLE alumnos (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL
);

CREATE TABLE materias (
    id SERIAL PRIMARY KEY,
    materia VARCHAR(150) NOT NULL
);

INSERT INTO alumnos (nombre)
VALUES
    ('Ana'),
    ('Carlos'),
    ('María');


INSERT INTO materias (materia)
VALUES
    ('Introducción al Front End'),
    ('Introducción al Back End'),
    ('Arquitectura de Computadoras');