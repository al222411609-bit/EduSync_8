#!/usr/bin/env bash
# Salir inmediatamente si un comando falla
set -o errexit

# Instalar Java (Necesario para PySpark)
apt-get update && apt-get install -y openjdk-11-jdk

# Instalar las dependencias de Python de tu requirements.txt
pip install -r requirements.txt
