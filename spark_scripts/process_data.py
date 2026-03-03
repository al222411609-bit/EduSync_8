from pyspark.sql import SparkSession

def init_spark():
    # Configuración para conectar Spark con MongoDB
    spark = SparkSession.builder \
        .appName("EdusyncDataProcessor") \
        .config("mongodb+srv://al222411609_db_user:Leo2505280606_edusync@cluster0.hujbcuw.mongodb.net/EdusyncDB?retryWrites=true&w=majority") \
        .getOrCreate()
    return spark

# Aquí procesarás los archivos que mencionas más adelante