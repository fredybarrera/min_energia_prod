#-------------------------------------------------------------------------------
# Name:         mainSec
# Purpose:      Script que lee información de cortes de suministro eléctrico proveniente de la SEC.
#               La información entregada por el servicio muestra la cantidad de clientes afectados por comuna.
#               Esta informacion es actualizada en la capa de comunas.
#
# Author:       Fredys Barrera Artiaga <fbarrera@esri.cl>
# Created:      23-07-2020
# Copyright:    (c) fbarrera 2020
# Licence:      <your licence>
#-------------------------------------------------------------------------------

# Set the ArcGIS Desktop Basic product by importing the arcview module.
import arcinfo
import arcpy
import utils
import constants as const
import requests
import xml.etree.ElementTree as et
import urllib.request as ur
import traceback
import os
import time
import json
from datetime import datetime, timedelta


# CLI_SAIDI -> numero de clientes
# NOM_SEC -> nombre comuna servicio
# Nuevos
# CLI_AFECTADOS -> clientes afectados
# PORC_AFECTADOS  -> porcentaje de clientes afectados respecto al total comunal
# FECHA_ACTUALIZACION -> fecha de actualizacion de los datos

# Workspace
arcpy.env.workspace = const.WORKSPACE
# Sobreescribo la misma capa de salida
arcpy.env.overwriteOutput = True
# Set the preserveGlobalIds environment to True
arcpy.env.preserveGlobalIds = True
# DATASET
dataset = const.DATASET

#-------------------------------------------------------------------------------
# Configuracion SEC
#-------------------------------------------------------------------------------
# Url api SEC
url_api_sec = const.URL_API_SEC
# Capa comunas
capa_comunas = const.COMUNAS_SEC


def main():
    """Main function Sec."""

    timeStart = time.time()
    arcpy.AddMessage("Proceso SEC iniciado... " + str(datetime.now()))
    utils.log("Proceso SEC iniciado")

    #-------------------------------------------------------------------------------
    # Proceso SEC
    #-------------------------------------------------------------------------------
    # Proceso que permite actualizar el número de clientes afectados por cortes de 
    # suministro eléctrico a nivel nacional
    clientes_afectados = 0

    # Obtengo los clientes afectados desde el servicio de la SEC
    arcpy.AddMessage("Obteniendo clientes afectados... ")
    data = obtener_clientes_afectados(url_api_sec)
    utils.log("Obteniendo clientes afectados")

    if len(data) > 0:
        # Limpio la data de la tabla local y del servicio
        arcpy.AddMessage("Limpiando resultados anteriores... ")
        limpiar_data_local()
        utils.log("Limpiando resultados anteriores")

        # Actualizo los clientes afectados
        arcpy.AddMessage("Actualizando clientes afectados... ")
        clientes_afectados = actualizar_clientes_afectados_local(data)
        arcpy.AddMessage("clientes_afectados " + str(clientes_afectados))
        utils.log("Actualizando clientes afectados")

    else:
        arcpy.AddMessage("No se pudo obtener los clientes afectados... ")
        utils.log("No se pudo obtener los clientes afectados")


    timeEnd = time.time()
    timeElapsed = timeEnd - timeStart
    arcpy.AddMessage("Proceso SEC finalizado... " + str(datetime.now()))
    arcpy.AddMessage("Tiempo de ejecución: " +
                    str(utils.convert_seconds(timeElapsed)))
    arcpy.AddMessage("Se registraron " + str(clientes_afectados) + ' afectados')
    utils.log("Se registraron " + str(clientes_afectados) + " afectados")
    utils.log("Tiempo de ejecución: " +
            str(utils.convert_seconds(timeElapsed)))
    utils.log("Proceso SEC finalizado \n")



def obtener_clientes_afectados(url):
    """Retorna los clientes afectados por cortes electricos por comunas."""
    try:
        ahora = datetime.now()
        hace_20_min = ahora - timedelta(minutes=20)
        
        anio = hace_20_min.strftime('%Y')
        mes = hace_20_min.strftime('%m')
        dia = hace_20_min.strftime('%d')
        hora = hace_20_min.strftime('%H')

        raw_data = {"anho": anio, "mes": mes, "dia": dia, "hora": hora}

        print('url: ', url)
        print('raw_data: ', raw_data)

        response = utils.post_request_json_raw_data(url, raw_data)

        return response

    except:
        print("Failed obtener_clientes_afectados (%s)" %
              traceback.format_exc())
        utils.error_log("Failed obtener_clientes_afectados (%s)" %
                        traceback.format_exc())
        utils.log("No se pudo obtener el listado de clientes afectados, respuesta del servicio: " + str(response))


def actualizar_clientes_afectados_local(clientes_afectados):
    """Actualiza los clientes afectados por comuna en la capa local, además calcula el porcentaje."""
    try:
        fc = os.path.join(arcpy.env.workspace, dataset, capa_comunas)
        ahora = datetime.now()
        total_clientes = 0
        comunas = []
        comunas_encontradas = []
        with arcpy.da.UpdateCursor(fc, ['NOM_SEC', 'CLI_SAIDI', 'CLI_AFECTADOS', 'PORC_AFECTADOS', 'FECHA_ACTUALIZACION']) as cursor:
            for row in cursor:
                for k in clientes_afectados:
                    comunas.append(k['NOMBRE_COMUNA'])
                    if row[0] == k['NOMBRE_COMUNA']:
                        comunas_encontradas.append(k['NOMBRE_COMUNA'])
                        # Actualizo los clientes afectados
                        row[2] = row[2] + k['CLIENTES_AFECTADOS']
                        total_clientes += row[2]
                        # Calculo el porcentaje que representa los afectados versus el total de clientes
                        porcentaje = row[2] / row[1] * 100
                        row[3] = porcentaje
                        row[4] = ahora

                        cursor.updateRow(row)

                        print('Comuna: {0}, clientes afectados: {1} ({2}%)'.format(
                            k['NOMBRE_COMUNA'], row[2], porcentaje))
        del cursor

        # Nombres de comunas que entrega la sec que no están registradas en la capa de comunas
        comunas_nuevas = list(set(comunas)-set(comunas_encontradas))
        print('comunas nuevas: ', comunas_nuevas)

        # Actualizo el nombre de la comuna en la tabla
        if(len(comunas_nuevas) > 0):
            actualizar_comunas(comunas_nuevas)

        return total_clientes
    except:
        print("Failed actualizar_clientes_afectados_local (%s)" %
              traceback.format_exc())
        utils.error_log("Failed actualizar_clientes_afectados_local (%s)" %
                        traceback.format_exc())


def limpiar_data_local():
    """Limpia los regultados anteriores, deja en cero la cantidad de afectados, porcentaje y fecha de actualización."""
    try:
        fc = os.path.join(arcpy.env.workspace, dataset, capa_comunas)
        with arcpy.da.UpdateCursor(fc, ['CLI_AFECTADOS', 'PORC_AFECTADOS', 'FECHA_ACTUALIZACION']) as cursor:
            for row in cursor:
                row[0] = 0
                row[1] = 0
                row[2] = None
                cursor.updateRow(row)
        del cursor
    except:
        print("Failed limpiar_data_local (%s)" %
              traceback.format_exc())
        utils.error_log("Failed limpiar_data_local (%s)" %
                        traceback.format_exc())


def actualizar_comunas(comunas):
    """Actualiza el nombre de la comuna en la capa."""
    try:
        fc = os.path.join(arcpy.env.workspace, dataset, capa_comunas)
        features = []
        with arcpy.da.UpdateCursor(fc, ['OID@', 'NOM_SAIDI', 'NOM_SEC']) as cursor:
            for row in cursor:
                for comuna in comunas:
                    if comuna == row[1]:
                        row[2] = comuna
                        features.append({
                            "attributes": {
                                "objectId": row[0],
                                "NOM_SEC": comuna,
                            }
                        })
                        print('Comuna de {0} actualizada'.format(comuna))
                        cursor.updateRow(row)
        del cursor
        print('features: ', features)

    except:
        print("Failed actualizar_comunas (%s)" %
              traceback.format_exc())
        utils.error_log("Failed actualizar_comunas (%s)" %
                        traceback.format_exc())
        

if __name__ == '__main__':
    main()
