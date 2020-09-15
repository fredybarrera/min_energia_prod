
#-------------------------------------------------------------------------------
# Name:         constants
# Purpose:      Constantes del script
#
# Author:       Fredys Barrera Artiaga <fbarrera@esri.cl>
# Created:      12-04-2020
# Copyright:    (c) fbarrera 2020
# Licence:      <your licence>
#-------------------------------------------------------------------------------

from decouple import config

# **********************************************************************************************
# Workspace
WORKSPACE = config('FOLDER_WORKSPACE')
WORKSPACE_LOCAL = config('FOLDER_WORKSPACE_LOCAL')
DATASET = config('WORKSPACE_DATASET')
DATASET_MINISTERIO = config('WORKSPACE_DATASET_CAPAS_MINISTERIO')
# **********************************************************************************************

# **********************************************************************************************
# Conaf
URL_FILE_CONAF = config('FILE_CONAF_KML')
URL_API_CONAF = "http://sidco.conaf.cl/mapa/data-minagri.php?key=mEiNnE2k18"

# Condición que indica si se va a urilizar un archivo kml local o la api de conaf
# para obtener los incendios
USE_FILE_KML = config('USE_FILE_KML')
# **********************************************************************************************

# **********************************************************************************************
# Agromet
URL_API_AGROMET = "http://agromet.inia.cl/api/"
USERKEY_AGROMET = "9532d75b835b8074ff3407fd701bd9ba1e8d292d"
# **********************************************************************************************

# **********************************************************************************************
# SEC
URL_API_SEC = "https://apps.sec.cl/IntEnLineaBetaV50/ClientesAfectados/GetPorFecha"
# **********************************************************************************************
# **********************************************************************************************

INCENDIOS = "Geodatos.USR_SCRIPT.INCENDIOS_CONAF"
# Capa con puntos afectados
PUNTOS_AFECTADOS = "Geodatos.USR_SCRIPT.PUNTOS_AFECTADOS"
# Capa con lineas afectadas
LINEAS_AFECTADAS = "Geodatos.USR_SCRIPT.LINEAS_AFECTADAS"
# Capa de salida del buffer por cada incendio
BUFFER_INCENDIOS = 'output_buffer'
# Capa de lectura de incendios de AGOL
BUFFER_VISOR = 'Geodatos.USR_SCRIPT.output_buffer_visor'
# Estaciones meteorológicas
ESTACIONES_METEOROLOGICAS = "Geodatos.USR_SCRIPT.ESTACIONES_METEOROLOGICAS"
# Capa comunas
COMUNAS_SEC = "Geodatos.USR_SCRIPT.BASE_COMUNA_SEC"


# Tables siggre
TABLES_SIGGRE = [
    'Geodatos.LGONZALEZL.IE_GENERACION', 
    'Geodatos.LGONZALEZL.IE_TAP_OFF', 
    'Geodatos.LGONZALEZL.IE_CONCESION_ELECTRICA', 
    'Geodatos.LGONZALEZL.IE_LINEA_DE_TRANSMISION', 
    'Geodatos.LGONZALEZL.IE_SUBESTACION', 
    'Geodatos.LGONZALEZL.IE_ALIMENTADOR'
    'Geodatos.LGONZALEZL.IHC_OLEODUCTO', 
    'Geodatos.LGONZALEZL.IHC_GASODUCTO', 
    'Geodatos.LGONZALEZL.IHC_TERMINAL_MARITIMO', 
    'Geodatos.LGONZALEZL.IHC_ALMACENAMIENTO_DE_COMBUSTIBLE', 
    'Geodatos.LGONZALEZL.IHC_PLANTA_SATELITE_DE_REGASIFICACION', 
    'Geodatos.LGONZALEZL.IHC_ESTACION_DE_SERVICIO'
]

LINE_TABLES = [
    'cruce_IE_LINEA_DE_TRANSMISION',
    'cruce_IE_ALIMENTADOR',
    'cruce_IHC_GASODUCTO',
    'cruce_IHC_OLEODUCTO'
]

POINT_TABLES = [
    'cruce_IHC_PLANTA_SATELITE_DE_REGASIFICACION',
    'cruce_IHC_ALMACENAMIENTO_DE_COMBUSTIBLE',
    'cruce_IE_GENERACION',
    'cruce_IE_SUBESTACION',
    'cruce_IE_TAP_OFF',
]
# **********************************************************************************************
