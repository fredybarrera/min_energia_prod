
#-------------------------------------------------------------------------------
# Name:         mainAgromet
# Purpose:      Script que cunsulta la dirección del viento desde el servicio de Agromet, 
#               (estaciones meteorológicas), este dato se actualiza en la capa de agromet
#               (direccion_viento) para representar con una simbología, 
#               en que dirección apunta el viento al momento de la consulta.
#
# Author:       Fredys Barrera Artiaga <fbarrera@esri.cl>
# Created:      08-06-2020
# Copyright:    (c) fbarrera 2020
# Licence:      <your licence>
#-------------------------------------------------------------------------------

import arcpy
import utils
import constants as const
import requests
import traceback
import os
import time
import json
from datetime import datetime, timedelta

#-------------------------------------------------------------------------------
# Workspace
#-------------------------------------------------------------------------------
arcpy.env.workspace = const.WORKSPACE
# Sobreescribo la misma capa de salida
arcpy.env.overwriteOutput = True
# Set the preserveGlobalIds environment to True
arcpy.env.preserveGlobalIds = True
# DATASET
dataset = const.DATASET

#-------------------------------------------------------------------------------
# Configuracion AGROMET
#-------------------------------------------------------------------------------
# Capa estaciones meteorológicas
capa_estaciones_meteorologicas = const.ESTACIONES_METEOROLOGICAS
# API Agromet (ministerio de energía)
# Información de las estaciones meteorológicas disponibles en la red de INIA
# La informacion devuelta por la API es en formato JSON
url_agromet = const.URL_API_AGROMET
userkey_agromet = const.USERKEY_AGROMET


def main():
    """Main function Agromet."""

    timeStart = time.time()
    arcpy.AddMessage("Proceso Agromet iniciado... " + str(datetime.now()))
    utils.log("Proceso Agromet iniciado")

    #-------------------------------------------------------------------------------
    # Proceso AGROMET
    #-------------------------------------------------------------------------------
    # Proceso que permite actualizar la direccion del viento de las estaciones meteorológicas
    arcpy.AddMessage("Obteniendo direccion del viento... ")
    utils.log("Obteniendo direccion del viento")
    obtener_variables_agromet(url_agromet, userkey_agromet)
    arcpy.AddMessage("Actualizando direccion del viento... ")
    utils.log("Actualizando direccion del viento")

    timeEnd = time.time()
    timeElapsed = timeEnd - timeStart
    arcpy.AddMessage("Proceso Agromet finalizado... " + str(datetime.now()))
    arcpy.AddMessage("Tiempo de ejecución: " +str(utils.convert_seconds(timeElapsed)))
    utils.log("Tiempo de ejecución: " + str(utils.convert_seconds(timeElapsed)))
    utils.log("Proceso Agromet finalizado \n")


def obtener_variables_agromet(url_agromet, userkey_agromet):
    """Obtiene las variable direccion del viento, temperatura, humedad de cada una de las estaciones meteorológicas."""
    try:
        # Obtengo las estaciones meteorológicas
        fc = os.path.join(arcpy.env.workspace, dataset, capa_estaciones_meteorologicas)
        estaciones = []
        muestras = []
        ahora = datetime.now()
        fecha_hoy = str(ahora.strftime('%Y-%m-%d'))
        # A la hora actual, le resto 20 minutos ya que es el tiempo de actualizacion del servicio de agromet
        hace_20_min = ahora - timedelta(minutes=20)
        hhmm = hace_20_min.strftime('%H%M')

        print('Fecha y hora consultada: {0} - {1} '.format(fecha_hoy, hhmm))
        utils.log("Fecha y hora consultada: {0} - {1} ".format(fecha_hoy, hhmm))

        with arcpy.da.SearchCursor(fc, ['id', 'id_direccion_viento', 'id_humedad_media', 'id_temperatura_media', 'id_velocidad_viento_max', 'id_velocidad_viento_media', 'nombre', 'comuna']) as cursor:
            for row in cursor:
                estaciones.append({
                    "id_estacion": row[0],
                    "id_direccion_viento": row[1],
                    "id_humedad_media": row[2],
                    "id_temperatura_media": row[3],
                    "id_velocidad_viento_max": row[4],
                    "id_velocidad_viento_media": row[5],
                    "nombre": row[6],
                    "comuna": row[7],
                })
        del cursor

        # Obtengo las muestras por cada variable
        muestras = get_muestras(estaciones, fecha_hoy, hhmm)
        
        # Por cada estacion, actualizo el valor de la direccion del viento 'direccion_viento' y la fecha de actualizacion 'fecha_actualizacion'
        with arcpy.da.UpdateCursor(fc, ['id', 'direccion_viento', 'humedad_media', 'temperatura_media', 'velocidad_viento_max', 'velocidad_viento_media', 'fecha_actualizacion']) as cursor:
            for row in cursor:
                for k in muestras:
                    if row[0] == k['id_estacion']:
                        row[1] = k['direccion_viento']
                        row[2] = k['humedad_media']
                        row[3] = k['temperatura_media']
                        row[4] = k['velocidad_viento_max']
                        row[5] = k['velocidad_viento_media']
                        row[6] = ahora
                        print('Estacion: {0}, direccion viento: {1}'.format(
                            k['id_estacion'], k['direccion_viento']))
                        cursor.updateRow(row)
        del cursor

    except:
        print("Failed obtener_variables_agromet (%s)" %
              traceback.format_exc())
        utils.error_log("Failed obtener_variables_agromet (%s)" %
                        traceback.format_exc())


def get_muestras(estaciones, fecha_hoy, hhmm):
    """Retorna la muestra por cada una de las vaiables consultadas."""
    try:
        muestras = []

        # Hago el llamado a la api por cada estacion para consultar la direccion del viento
        for estacion in estaciones:
            print('Consultando estacion: {0}, {1}'.format(estacion['nombre'], estacion['comuna']))
            direccion_viento = get_data_variable(estacion['id_direccion_viento'], fecha_hoy, hhmm)
            humedad_media = get_data_variable(estacion['id_humedad_media'], fecha_hoy, hhmm)
            temperatura_media = get_data_variable(estacion['id_temperatura_media'], fecha_hoy, hhmm)
            velocidad_viento_max = get_data_variable(estacion['id_velocidad_viento_max'], fecha_hoy, hhmm)
            velocidad_viento_media = get_data_variable(estacion['id_velocidad_viento_media'], fecha_hoy, hhmm)

            muestras.append({
                "id_estacion": int(estacion['id_estacion']),
                "direccion_viento": float(direccion_viento),
                "humedad_media": float(humedad_media),
                "temperatura_media": float(temperatura_media),
                "velocidad_viento_max": float(velocidad_viento_max),
                "velocidad_viento_media": float(velocidad_viento_media)
            })

        return muestras

    except:
        print("Failed get_muestras (%s)" %
              traceback.format_exc())
        utils.error_log("Failed get_muestras (%s)" %
                        traceback.format_exc())


def get_data_variable(idEmaVariable, fecha_hoy, hhmm):
    """Retorna el valor de una variable."""
    try:
        value = 0
        url = url_agromet + 'muestras/?idEmaVariable=' + str(idEmaVariable) + '&desde=' + \
            fecha_hoy + '&hasta=' + fecha_hoy + \
            '&desde_hora=' + str(hhmm) + '&hasta_hora=' + \
            str(hhmm) + '&user=' + userkey_agromet

        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data['muestras'] != None:
                value = data['muestras'][0]['valor']
            
        return value

    except:
        print("Failed get_data_variable (%s)" %
              traceback.format_exc())
        utils.error_log("Failed get_data_variable (%s)" %
                        traceback.format_exc())


if __name__ == '__main__':
    main()
