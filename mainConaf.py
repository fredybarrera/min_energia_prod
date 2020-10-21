#-------------------------------------------------------------------------------
# Name:         mainConaf
# Purpose:      Script que lee información de incendios forestales de conaf, a través de un 
#               servicio web en formato kml.
#               Se obtiene el listado de incendios forestales activos, los cuales se cruzan 
#               espacialmente con capas de infraestructuras proporcionadas por el Ministerio de energía.
#               Al encontrar una coincidencia, se almacena el registro en una capa de resultados.
#               Tambien se envia una alerta por email al responsable de la entidad utilizando 
#               el campo "EMAIL" del registro.
#
# Author:       Fredys Barrera Artiaga <fbarrera@esri.cl>
# Created:      12-04-2020
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

# Workspace
arcpy.env.workspace = const.WORKSPACE
# Sobreescribo la misma capa de salida
arcpy.env.overwriteOutput = True
# Set the preserveGlobalIds environment to True
arcpy.env.preserveGlobalIds = False
# Ruta absoluta del script
script_dir = os.path.dirname(__file__)
# DATASET
dataset = const.DATASET
# DATASET Ministerio
dataset_ministerio = const.DATASET_MINISTERIO
# Folder local
folder_local = const.WORKSPACE_LOCAL
#-------------------------------------------------------------------------------
# Configuracion CONAF
#-------------------------------------------------------------------------------
# Información de incendios forestales
# La información devuelta por el servicio es en formato KML
# Valido si uso un kml local o llamo a la api de conaf
usar_kml_local = const.USE_FILE_KML
# xml conaf
url_conaf_file = os.path.join(script_dir, const.URL_FILE_CONAF)
# URL API
url_conaf_api = const.URL_API_CONAF
# Namespace
nmsp_conaf = '{http://www.opengis.net/kml/2.2}'
# Capa de conaf en donde se guardan los incendios
capa_incendios = const.INCENDIOS
# Capa con puntos afectados
capa_puntos_afectados = const.PUNTOS_AFECTADOS
# Capa con lineas afectadas
capa_lineas_afectadas = const.LINEAS_AFECTADAS
# Capa de salida del buffer por cada incendio
capa_buffer_incendios = const.BUFFER_INCENDIOS
# Capa de lectura de incendios de AGOL
capa_buffer_incendios_visor = const.BUFFER_VISOR

user_datos = const.USER_DATOS

def main():
    """Main function Conaf."""

    timeStart = time.time()
    arcpy.AddMessage("Proceso Conaf iniciado... " + str(datetime.now()))
    utils.log("Proceso Conaf iniciado")

    #-------------------------------------------------------------------------------
    # Proceso CONAF
    #-------------------------------------------------------------------------------
    # Obtengo la data de Conaf
    incendios = []
    if usar_kml_local == 'true':
        # Elimino los incendios anteriores 
        utils.truncar_data_dataset(capa_incendios)
        # Elimino los buffers anteriores del visor
        utils.truncar_data_dataset(capa_buffer_incendios_visor)
        # Obtengo los indendios desde archivo local
        data_conaf = et.parse(url_conaf_file)
        # Proceso la data de Conaf y la almaceno en la GDB 'capa_incendios' y en el servicio REST de conaf
        incendios = procesar_data_conaf_local(data_conaf)
    else:
        # Obtengo los indendios desde servicio web
        data_conaf = utils.get_data_kml(url_conaf_api)
        # Proceso la data de Conaf y la almaceno en la GDB 'capa_incendios' y en el servicio REST de conaf
        incendios = procesar_data_conaf_rest(data_conaf)
    

    # Si no existen incendios activos en el servicio de conaf, limpio todas las capas
    if (incendios['incendios_activos'] == 0):
    # if (incendios['actualizados'] == 0 and incendios['nuevos'] == 0 and incendios['extinguidos'] == 0):
        informar_incendios_extinguidos()
        utils.truncar_data_dataset(capa_incendios)
        utils.truncar_data_dataset(capa_puntos_afectados)
        utils.truncar_data_dataset(capa_lineas_afectadas)
        utils.truncar_data_dataset(capa_buffer_incendios_visor)


    # Si existen incendios nuevos, creo los buffer a cada uno de ellos, ejecuto el análisis y actualizo las capas
    # Si hay actualizacion de algun incendio, actualizo el estado del servicio de incendios, buffer y capas de resultados
    if (incendios['actualizados'] > 0 or incendios['nuevos'] > 0):

       # Creo el buffer a los incendios (sobreescribe el existente)
        crear_buffer(capa_incendios)

        # Borro los buffers creados con anterioridad
        utils.truncar_data_dataset(capa_buffer_incendios_visor)
        # Una vez creado el buffer, copio los datos en capa_buffer_incendios_visor
        copiar_datos_buffer(capa_buffer_incendios, capa_buffer_incendios_visor)

        # Ejecuto el cruce espacial del buffer creado versus las capas del min. energía (crea y sobreescribe las capas de cruces)
        ejecutar_analisis(capa_buffer_incendios_visor)
        
        # Limpio las capas de resultados local
        utils.truncar_data_dataset(capa_puntos_afectados)
        utils.truncar_data_dataset(capa_lineas_afectadas)

        # Actualizo las capas locales con los resultados (puntos y lineas afectadas)
        actualizar_resultados_local_lineas()
        actualizar_resultados_local_puntos()

        # Ejecuto funcion de cercania para obtener la distancia entre los resultados y los incendios.
        # Se quita funcionalidad de cercanía debido a que ocupa licencia advanced
        # ejecutar_cercania(capa_puntos_afectados)
        # ejecutar_cercania(capa_lineas_afectadas)

        # Obtengo las entidades afectadas por el incendio, 
        # si hay incendios nuevos, envio la alerta
        entidades = obtener_resultados()
        
        # Cuando existen incendios nuevos se informa
        if incendios['nuevos'] > 0:
            # Envío las alertas a las entidades afectadas
            generar_alertas(entidades)
    
    
    # Elimino las tablas auxiliares
    utils.delete_temp_tables()

    timeEnd = time.time()
    timeElapsed = timeEnd - timeStart
    arcpy.AddMessage("Proceso Conaf finalizado... " + str(datetime.now()))
    arcpy.AddMessage("Se procesaron " + str(incendios) + ' incendios')
    arcpy.AddMessage("Tiempo de ejecución: " + str(utils.convert_seconds(timeElapsed)))
    utils.log("Se procesaron " + str(incendios) + ' incendios')
    utils.log("Tiempo de ejecución: " +
              str(utils.convert_seconds(timeElapsed)))
    utils.log("Proceso Conaf finalizado \n")


def informar_incendios_extinguidos():
    """Informa al admin que el incendio se ha extinguido, cuando no existe ningún incendio registrado por conaf."""
    try:
        arcpy.AddMessage("Enviando alerta de incendio extinguido...")
        fc = os.path.join(arcpy.env.workspace, dataset, capa_incendios)
        with arcpy.da.SearchCursor(fc, ["id_incendio", "fecha_inicio_incendio", "comuna_incendio"]) as cursor:
            for row in cursor:
                # Envío la alerta
                utils.log("Informando incendio extingido id: {0}, comuna de {1}, fecha: {3}".format(row[0], row[2], row[1]))
                utils.enviar_correo_admin_extinguido(row[0], row[1], row[2])
        del cursor

    except:
        print("Failed informar_incendios_extinguidos (%s)" % traceback.format_exc())
        utils.error_log("Failed informar_incendios_extinguidos (%s)" %
                        traceback.format_exc())


def procesar_data_conaf_rest(data):
    """
    Procesa la data obtenida desde el servicio de conaf y actualiza la capa de incendios de conaf
    1.- Se leen los icendios desde el servicio de conaf
    2.- Se registran los nuevos incendios
    3.- Se actualiza el estado de los incendios registrados
    """
    try:
        arcpy.AddMessage("Procesando data de conaf...")
        utils.log("Procesando data de conaf")
        incendios_nuevos = 0
        incendios_actualizados = 0
        incendios_extinguidos = 0
        incendios_activos = 0
        indendios_servicio = []

        fields = [
            'id_incendio', 
            'nombre_incendio', 
            'fecha_actualizacion', 
            'fecha_inicio_incendio', 
            'comuna_incendio', 
            'superficie_incendio', 
            'estado_incendio', 
            'SHAPE@'
        ]

        fc = os.path.join(arcpy.env.workspace, dataset, capa_incendios)

        for pm in data.iterfind('.//{0}Placemark'.format(nmsp_conaf)):

            incendio = pm.find('{0}name'.format(nmsp_conaf)).text  # Nombre del incendio
            
            id_incendio = pm.find('{0}ExtendedData/{0}SchemaData/{0}SimpleData'.format(nmsp_conaf)).text  # Id del incendio
            indendios_servicio.append(id_incendio)

            for ls in pm.iterfind('{0}Point/{0}coordinates'.format(nmsp_conaf)):

                # print('hay incendios activos en el servicio de conaf -------------------------------------')

                incendios_activos += 1

                coordinates = ls.text.strip().replace(',0', '')
                res = coordinates.split(',')
                longitud, latitud = res

                # Obtengo la informacion adicional del incendio, que no viene dentro de los atributos del Placemark, esta informacion está contenida dentro de un iframe
                fecha_inicio_incendio, comuna, superficie, estado_incendio_servicio = utils.get_data_iframe(id_incendio)
                utils.log("Incendio: {0}, comuna: {1}, superficie: {2}, estado: {3}".format(id_incendio, comuna, superficie, estado_incendio_servicio))

                # Valido si ya existe el indencio en la GDB
                existe = False
                expression = """{0} = '{1}'""".format(arcpy.AddFieldDelimiters(fc, 'id_incendio'), id_incendio)
                with arcpy.da.SearchCursor(fc, ['id_incendio', 'nombre_incendio', 'estado_incendio'], where_clause=expression) as cursor:
                    # Si existe el incendio, valido el estado
                    for row in cursor:
                        existe = True
                        estado_incendio = row[2]
                        # Si cambia el estado del incencio, lo actualizo
                        if estado_incendio != estado_incendio_servicio:
                            incendios_actualizados += 1
                            # Si el incendio se encuentra extinguido, genero la alerta informando
                            if estado_incendio_servicio == 'Extinguido':
                                incendios_extinguidos += 1
                                utils.enviar_correo_admin_extinguido(id_incendio, fecha_inicio_incendio, comuna)

                                # Elimino el registro del incendio en la base de datos
                                with arcpy.da.UpdateCursor(fc, ['id_incendio']) as cursor_update:
                                    for row_u in cursor_update:
                                        if row_u[0] == id_incendio:
                                            cursor_update.deleteRow()
                                del cursor_update

                                # Elimino el buffer del incendio
                                fcb = os.path.join(arcpy.env.workspace, dataset, capa_buffer_incendios_visor)
                                with arcpy.da.UpdateCursor(fcb, ['id_incendio']) as cursor_update:
                                    for row_u in cursor_update:
                                        if row_u[0] == id_incendio:
                                            cursor_update.deleteRow()    
                                del cursor_update

                                # Elimino las lineas afectadas el incendio
                                fcl = os.path.join(arcpy.env.workspace, dataset, capa_lineas_afectadas)
                                with arcpy.da.UpdateCursor(fcl, ['id_incendio']) as cursor_update:
                                    for row_u in cursor_update:
                                        if row_u[0] == id_incendio:
                                            cursor_update.deleteRow()
                                del cursor_update

                                # Elimino los puntos afectadas el incendio
                                fcp = os.path.join(arcpy.env.workspace, dataset, capa_puntos_afectados)
                                with arcpy.da.UpdateCursor(fcp, ['id_incendio']) as cursor_update:
                                    for row_u in cursor_update:
                                        if row_u[0] == id_incendio:
                                            cursor_update.deleteRow()
                                del cursor_update
                            # with arcpy.da.UpdateCursor(fc, ['id_incendio', 'estado_incendio', 'informado']) as cursor_update:
                            #     for row_u in cursor_update:
                            #         if row_u[0] == id_incendio:
                            #             row_u[1] = estado_incendio_servicio
                            #             row_u[2] = True
                            #             print('Id incendio: {0}, estado : {1}, nuevo estado: {2}'.format(id_incendio, estado_incendio, estado_incendio_servicio))
                            #         cursor_update.updateRow(row_u)
                            # del cursor_update
                    # Si no existe, lo guardo
                    if existe == False:
                        incendios_nuevos += 1
                        # Creo la geometría de punto
                        point = arcpy.Point(float(longitud), float(latitud))
                        out_sr = arcpy.SpatialReference("WGS 1984")
                        ptGeometry = arcpy.PointGeometry(point, out_sr)
                        cursor_insert = arcpy.da.InsertCursor(fc, fields)
                        # Creo el incendio en GDB
                        cursor_insert.insertRow((
                            id_incendio,
                            incendio,
                            datetime.now(),
                            fecha_inicio_incendio,
                            comuna,
                            superficie,
                            estado_incendio_servicio,
                            ptGeometry))

                        del cursor_insert
                del cursor

        total = {
            'actualizados': incendios_actualizados,
            'nuevos': incendios_nuevos,
            'extinguidos': incendios_extinguidos,
            'incendios_activos': incendios_activos
        }

        notifica_incencios_borrados(indendios_servicio)

        print('Incendios: ', total)

        return total

    except:
        print("Failed procesar_data_conaf_rest (%s)" % traceback.format_exc())
        utils.error_log("Failed procesar_data_conaf_rest (%s)" %
                        traceback.format_exc())

def notifica_incencios_borrados(incendios):
    """Permite notificar un incendio como extinguido 
    cuando conaf lo borra del servicio sin cambiar el estado a extinguido"""
    try:
        str_incendios = '\'' + '\', \''.join(incendios) + '\''
        fc = os.path.join(arcpy.env.workspace, dataset, capa_incendios)
        expression = """{0} NOT IN ({1})""".format(arcpy.AddFieldDelimiters(fc, 'id_incendio'), str_incendios)
        print('incendios notifica_incencios_borrados expression: ', expression)
        incendios_notificados = []
        with arcpy.da.SearchCursor(fc, ["id_incendio", "fecha_inicio_incendio", "comuna_incendio"], where_clause=expression) as cursor:
            for row in cursor:
                print('incendio registrado y borrado de conaf:: ', row[0])
                incendios_notificados.append(row[0])
                utils.log("Informando incendio extingido id: {0}, comuna de {1}, fecha: {2}".format(row[0], row[2], row[1]))
                utils.enviar_correo_admin_extinguido(row[0], row[1], row[2])
        del cursor

        # Elimino el registro del incendio en la base de datos
        with arcpy.da.UpdateCursor(fc, ['id_incendio']) as cursor_update:
            for row_u in cursor_update:
                if row_u[0] in incendios_notificados:
                    cursor_update.deleteRow()    
        del cursor_update


        # Elimino el buffer del incendio
        fc = os.path.join(arcpy.env.workspace, dataset, capa_buffer_incendios_visor)
        with arcpy.da.UpdateCursor(fc, ['id_incendio']) as cursor_update:
            for row_u in cursor_update:
                if row_u[0] in incendios_notificados:
                    cursor_update.deleteRow()    
        del cursor_update

        # Elimino las lineas afectadas el incendio
        fc = os.path.join(arcpy.env.workspace, dataset, capa_lineas_afectadas)
        with arcpy.da.UpdateCursor(fc, ['id_incendio']) as cursor_update:
            for row_u in cursor_update:
                if row_u[0] in incendios_notificados:
                    cursor_update.deleteRow()    
        del cursor_update

        # Elimino los puntos afectadas el incendio
        fc = os.path.join(arcpy.env.workspace, dataset, capa_puntos_afectados)
        with arcpy.da.UpdateCursor(fc, ['id_incendio']) as cursor_update:
            for row_u in cursor_update:
                if row_u[0] in incendios_notificados:
                    cursor_update.deleteRow()    
        del cursor_update
        

    except:
        print("Failed notifica_incencios_borrados (%s)" % traceback.format_exc())
        utils.error_log("Failed notifica_incencios_borrados (%s)" %
                        traceback.format_exc())

def procesar_data_conaf_local(data):
    """
    Procesa la data obtenida desde un kml local y actualiza la capa de incendios de conaf
    1.- Se leen los icendios desde el servicio de conaf
    2.- Se registran los nuevos incendios
    3.- Se actualiza el estado de los incendios registrados
    """
    try:
        arcpy.AddMessage("Procesando data de conaf...")
        utils.log("Procesando data de conaf local")
        incendios_nuevos = 0
        incendios_actualizados = 0
        incendios_extinguidos = 0
        incendios_activos = 0
        indendios_servicio = []

        fields = [
            'id_incendio',
            'nombre_incendio',
            'fecha_actualizacion',
            'fecha_inicio_incendio',
            'comuna_incendio',
            'superficie_incendio',
            'estado_incendio',
            'SHAPE@'
        ]

        fc = os.path.join(arcpy.env.workspace, dataset, capa_incendios)

        for pm in data.iterfind('.//{0}Placemark'.format(nmsp_conaf)):

            incendio = pm.find('{0}name'.format(nmsp_conaf)).text  # Nombre del incendio

            id_incendio = pm.find('{0}ExtendedData/{0}SchemaData/{0}SimpleData'.format(nmsp_conaf)).text  # Id del incendio
            indendios_servicio.append(id_incendio)

            for ls in pm.iterfind('{0}Point/{0}coordinates'.format(nmsp_conaf)):

                # print('hay incendios activos en el kml de prueba -------------------------------------')

                incendios_activos += 1

                coordinates = ls.text.strip().replace(',0', '')
                res = coordinates.split(',')
                longitud, latitud = res

                # Obtengo la informacion adicional del incendio, que no viene dentro de los atributos del Placemark, esta informacion está contenida dentro de un iframe
                fecha_inicio_incendio, comuna, superficie, estado_incendio_servicio = utils.get_data_iframe_aux(id_incendio)

                # Valido si ya existe el indencio en la GDB
                existe = False
                expression = """{0} = '{1}'""".format(arcpy.AddFieldDelimiters(fc, 'id_incendio'), id_incendio)
                with arcpy.da.SearchCursor(fc, ['id_incendio', 'nombre_incendio', 'estado_incendio'], where_clause=expression) as cursor:
                    # Si existe el incendio, valido el estado
                    for row in cursor:
                        existe = True
                        estado_incendio = row[2]
                        # Si cambia el estado del incencio, lo actualizo
                        if estado_incendio != estado_incendio_servicio:
                            incendios_actualizados += 1
                            # Si el incendio se encuentra extinguido, genero la alerta informando
                            if estado_incendio_servicio == 'Extinguido':
                                incendios_extinguidos += 1
                                utils.enviar_correo_admin_extinguido(id_incendio, fecha_inicio_incendio, comuna)
                                # Elimino el registro del incendio en la base de datos
                                with arcpy.da.UpdateCursor(fc, ['id_incendio']) as cursor_update:
                                    for row_u in cursor_update:
                                        if row_u[0] == id_incendio:
                                            cursor_update.deleteRow()
                                del cursor_update

                                # Elimino el buffer del incendio
                                fcb = os.path.join(arcpy.env.workspace, dataset, capa_buffer_incendios_visor)
                                with arcpy.da.UpdateCursor(fcb, ['id_incendio']) as cursor_update:
                                    for row_u in cursor_update:
                                        if row_u[0] == id_incendio:
                                            cursor_update.deleteRow()    
                                del cursor_update

                                # Elimino las lineas afectadas el incendio
                                fcl = os.path.join(arcpy.env.workspace, dataset, capa_lineas_afectadas)
                                with arcpy.da.UpdateCursor(fcl, ['id_incendio']) as cursor_update:
                                    for row_u in cursor_update:
                                        if row_u[0] == id_incendio:
                                            cursor_update.deleteRow()
                                del cursor_update

                                # Elimino los puntos afectadas el incendio
                                fcp = os.path.join(arcpy.env.workspace, dataset, capa_puntos_afectados)
                                with arcpy.da.UpdateCursor(fcp, ['id_incendio']) as cursor_update:
                                    for row_u in cursor_update:
                                        if row_u[0] == id_incendio:
                                            cursor_update.deleteRow()
                                del cursor_update
                            # with arcpy.da.UpdateCursor(fc, ['id_incendio', 'estado_incendio', 'informado']) as cursor_update:
                            #     for row_u in cursor_update:
                            #         if row_u[0] == id_incendio:
                            #             # aca deberia eliminar el incendio, sus puntos y lineas afectadas.
                            #             row_u[1] = estado_incendio_servicio
                            #             row_u[2] = True
                            #             print('Id incendio: {0}, estado : {1}, nuevo estado: {2}'.format(
                            #                 id_incendio, estado_incendio, estado_incendio_servicio))
                            #         cursor_update.updateRow(row_u)
                            # del cursor_update
                    # Si no existe, lo guardo
                    if existe == False:
                        incendios_nuevos += 1
                        # Creo la geometría de punto
                        point = arcpy.Point(float(longitud), float(latitud))
                        out_sr = arcpy.SpatialReference("WGS 1984")
                        ptGeometry = arcpy.PointGeometry(point, out_sr)
                        cursor_insert = arcpy.da.InsertCursor(fc, fields)
                        # Creo el incendio en GDB
                        cursor_insert.insertRow((
                            id_incendio,
                            incendio,
                            datetime.now(),
                            fecha_inicio_incendio,
                            comuna,
                            superficie,
                            estado_incendio_servicio,
                            ptGeometry))

                        del cursor_insert
                del cursor

        total = {
            'actualizados': incendios_actualizados,
            'nuevos': incendios_nuevos,
            'extinguidos': incendios_extinguidos,
            'incendios_activos': incendios_activos
        }

        notifica_incencios_borrados(indendios_servicio)

        print('Incendios: ', total)

        return total

    except:
        print("Failed procesar_data_conaf_local (%s)" % traceback.format_exc())
        utils.error_log("Failed procesar_data_conaf_local (%s)" %
                        traceback.format_exc())


def crear_buffer(capa_incendios):
    """Crea un buffer por cada uno de los incendios."""
    try:
        arcpy.AddMessage("Creando buffer...")
        utils.log("Creando buffer")
        # roads = capa_incendios
        buffer_output = capa_buffer_incendios
        # roadsBuffer = os.path.join(arcpy.env.workspace, buffer_output)
        roadsBuffer = os.path.join(folder_local, buffer_output)
        roads = os.path.join(arcpy.env.workspace, dataset, capa_incendios)
        # print('roadsBuffer: ', roadsBuffer)
        # print('roads: ', roads)
        distanceField = "5 Kilometers"
        arcpy.Buffer_analysis(roads, roadsBuffer, distanceField)
    
    except:
        print("Failed crear_buffer (%s)" %
            traceback.format_exc())
        utils.error_log("Failed crear_buffer (%s)" %
                        traceback.format_exc())


def copiar_datos_buffer(buffer_incendios, buffer_visor):
    """Copia los resultados del buffer temporal al buffer visor."""
    try:
        arcpy.AddMessage("Actualizando capa de buffers...")
        utils.log("Actualizando capa de buffers")
        fc_origen = os.path.join(folder_local, buffer_incendios)
        fc_destino = os.path.join(arcpy.env.workspace, dataset, buffer_visor)
        fields = [
            'id_incendio',
            'nombre_incendio',
            'comuna_incendio',
            'superficie_incendio',
            'estado_incendio',
            'fecha_inicio_incendio',
            'fecha_actualizacion',
            'informado',
            'BUFF_DIST',
            'ORIG_FID',
            'SHAPE@'
        ]
        insert_cursor = arcpy.da.InsertCursor(fc_destino, fields)
        with arcpy.da.SearchCursor(fc_origen, fields) as cursor:
            for row in cursor:
                insert_cursor.insertRow((
                    row[0],
                    row[1],
                    row[2],
                    row[3],
                    row[4],
                    row[5],
                    row[6],
                    row[7],
                    row[8],
                    row[9],
                    row[10]
                   ))

        # Delete cursor object
        del cursor
        del insert_cursor

    except:
        print("Failed copiar_datos_buffer (%s)" %
            traceback.format_exc())
        utils.error_log("Failed copiar_datos_buffer (%s)" %
                        traceback.format_exc())


def ejecutar_analisis(buffer):
    """Ejecuta el análisis de intersección entre los buffers de los incendios 
    versus las capas de infraestructuras definidas por el cliente."""
    try:
        arcpy.AddMessage("Ejecutando análisis...")
        utils.log("Ejecutando análisis")
        
        incluir = const.TABLES_SIGGRE
        features = arcpy.ListFeatureClasses(feature_dataset=dataset_ministerio)

        for feature in incluir:
            f = feature
            if f in features:
                #Ejecuto el cruce espacial por cada capa
                in_buffer = os.path.join(arcpy.env.workspace, dataset, buffer)
                in_feature = os.path.join(arcpy.env.workspace, dataset_ministerio, f)
                inFeatures = [in_buffer, in_feature]
                name = f.split(user_datos)
                capa_cruce = "cruce_" + name[1]
                arcpy.AddMessage("Intersectando buffer contra " + f + " ...")
                arcpy.AddMessage("nombre capa_cruce: " + capa_cruce + " ...")
                intersectOutput = os.path.join(folder_local, capa_cruce)
                arcpy.Intersect_analysis(inFeatures, intersectOutput, "", "" , 'input')
    
    except:
        print("Failed ejecutar_analisis (%s)" %
              traceback.format_exc())
        utils.error_log("Failed ejecutar_analisis (%s)" %
                        traceback.format_exc())


def actualizar_resultados_local_lineas():
    """
    Obtiene las lineas afectadas por el incendio.
    Guarda las lineas en la capa "LINEAS_AFECTADAS"
    """
    try: 

        posiblesColumnas = [
            'LEYENDA',
            'NOMBRE',
            'PROPIEDAD',
            'PROPIETARIO',
            'DIRECCION',
            'TIPO',
            'COMBUSTIBL',
            'CRITICIDAD',
            'ESTADO_INF',
            'E_MAIL',
            'NOM_EMP_AN',
            'NOMBRE_ALI',
            'SHAPE@',
            'id_incendio',
            'nombre_incendio',
            'comuna_incendio',
            'superficie_incendio',
            'estado_incendio',
            'fecha_inicio_incendio'
        ]
        
        incluir = const.LINE_TABLES
        features = const.TABLES_SIGGRE

        # print('incluir: ', incluir)
        # print('features: ', features)

        data = []
        for f in features:
            name = f.split(user_datos)
            feature = "cruce_" + name[1]
            # print('feature: ', feature)
            if feature in incluir:
                # fc = os.path.join(arcpy.env.workspace, feature)
                fc = os.path.join(folder_local, feature)
                if arcpy.Exists(fc):
                    # print('fccccccc: ', fc)
                    print('actualizar_resultados_local_lineas fc: ', fc)
                    field_names = [f.name for f in arcpy.ListFields(fc)]
                    field_names.append('SHAPE@')
                    with arcpy.da.SearchCursor(fc, field_names) as cursor:
                        for row in cursor:
                            union = list(zip(field_names, row))
                            attributes = {}
                            for val in union:
                                if val[0] in posiblesColumnas:
                                    if val[0] == 'SHAPE@':
                                        attributes['shape'] = val[1]
                                        continue
                                    if (val[0] == 'NOMBRE_ALI'):
                                        attributes['nombre'] = val[1]
                                        continue
                                    if (val[0] == 'NOM_EMP_AN' or val[0] == 'PROPIEDAD'):
                                        attributes['propietario'] = val[1]
                                        continue
                                    attributes[val[0].lower()] = (val[1] != None and val[1] or '')
                                    attributes['capa'] = feature.replace('cruce_', '')
                        
                            data.append(attributes)
                    # Delete cursor object
                    del cursor

        insert_data_local(capa_lineas_afectadas, data)

    except:
        print("Failed actualizar_resultados_local_lineas (%s)" %
            traceback.format_exc())
        utils.error_log("Failed actualizar_resultados_local_lineas (%s)" %
                        traceback.format_exc())


def actualizar_resultados_local_puntos():
    """
    Obtiene los puntos afectados por el incendio.
    Guarda los puntos en la capa "PUNTOS_AFECTADOS"
    """
    try:

        posiblesColumnas = [
            'LEYENDA', 
            'NOMBRE', 
            'DIRECCION',
            'PROPIEDAD', 
            'PROPIETARI', 
            'PROPIETARIO',
            'CRITICIDAD', 
            'ESTADO', 
            'ESTADO_INF', 
            'E_MAIL', 
            'id_incendio',
            'nombre_incendio',
            'comuna_incendio',
            'superficie_incendio',
            'estado_incendio',
            'fecha_inicio_incendio',
            'Shape'
        ]

        # features = arcpy.ListFeatureClasses()
        features = const.TABLES_SIGGRE
        incluir = const.POINT_TABLES

        data = []
        for f in features:
            name = f.split(user_datos)
            feature = "cruce_" + name[1]
            # print('feature: ', feature)
            if feature in incluir:
                # fc = os.path.join(arcpy.env.workspace, feature)
                fc = os.path.join(folder_local, feature)
                if arcpy.Exists(fc):
                    print('actualizar_resultados_local_puntos fc: ', fc)
                    field_names = [f.name for f in arcpy.ListFields(fc)]
                    with arcpy.da.SearchCursor(fc, field_names) as cursor:
                        for row in cursor:
                            union = list(zip(field_names, row))
                            attributes = {}
                            for val in union:
                                if val[0] in posiblesColumnas:
                                    if val[0] == 'Shape':
                                        shape = val[1]
                                        attributes['latitud'] = shape[1]
                                        attributes['longitud'] = shape[0]
                                        continue
                                    if (val[0] == 'PROPIETARI' or val[0] == 'PROPIEDAD'):
                                        attributes['propietario'] = val[1]
                                        continue
                                    attributes[val[0].lower()] = (val[1] != None and val[1] or '')
                                    attributes['capa'] = feature.replace('cruce_', '')
                            
                            data.append(attributes)

                    # Delete cursor object
                    del cursor
        
        insert_data_local(capa_puntos_afectados, data, True)

    except:
        print("Failed actualizar_resultados_local_puntos (%s)" %
              traceback.format_exc())
        utils.error_log("Failed actualizar_resultados_local_puntos (%s)" %
                        traceback.format_exc())


def insert_data_local(capa_local, datos, es_punto=None):
    """Guarda en las capas de resultados las entidades afectadas."""
    try:
        fields = [
            'leyenda',
            'nombre',
            'propietario',
            'direccion',
            'criticidad',
            'estado',
            'estado_inf',
            'e_mail',
            'capa',
            'id_incendio',
            'nombre_incendio',
            'comuna_incendio',
            'superficie_incendio',
            'estado_incendio',
            'fecha_inicio_incendio',
            'SHAPE@'
        ]
        fc = os.path.join(arcpy.env.workspace, dataset, capa_local)
        cursor = arcpy.da.InsertCursor(fc, fields)
        out_sr = arcpy.SpatialReference("WGS 1984")
        for dato in datos:
            if es_punto != None:
                point = arcpy.Point(float(dato['longitud']), float(dato['latitud']))
                geometry = arcpy.PointGeometry(point, out_sr)
            else:

                # for feature in dato['shape']['paths']:
                # #     # Create a Polyline object based on the array of points
                # #     # Append to the list of Polyline objects
                #     # geometry = arcpy.Polyline(arcpy.Array([arcpy.Point(*coords) for coords in feature]))

                #     array = arcpy.Array([arcpy.Point(*coords) for coords in feature])
                
                geometry = dato['shape']

            cursor.insertRow((
                dato['leyenda'],
                dato['nombre'],
                dato['propietario'],
                ('direccion' in dato and dato['direccion'] or ''),
                ('criticidad' in dato and dato['criticidad'] or ''),
                ('estado' in dato and dato['estado'] or ''),
                ('estado_inf' in dato and dato['estado_inf'] or ''),
                dato['e_mail'],
                dato['capa'],
                dato['id_incendio'],
                dato['nombre_incendio'],
                dato['comuna_incendio'],
                dato['superficie_incendio'],
                dato['estado_incendio'],
                dato['fecha_inicio_incendio'],
                geometry))

        del cursor

    except:
        print("Failed insert_data_local (%s)" %
              traceback.format_exc())
        utils.error_log("Failed insert_data_local (%s)" %
                        traceback.format_exc())


def obtener_resultados():
    """Obtiene los resultados de los puntos y lineas afectadas"""
    try:
        arcpy.AddMessage("Obteniendo resultados de entidades afectadas...")
        utils.log("Obteniendo resultados de entidades afectadas")
        # Puntos 
        puntosAfectados = obtener_puntos_afectados()
        # Lineas 
        lineasAfectadas = obtener_lineas_afectadas()
        # Correos de alertas a enviar
        entidades = puntosAfectados + lineasAfectadas

        return entidades

    except:
        print("Failed obtener_resultados (%s)" %
              traceback.format_exc())
        utils.error_log("Failed obtener_resultados (%s)" %
                        traceback.format_exc())


def obtener_puntos_afectados():
    """Permite obtener los puntos afectador por el incendio."""
    try:
        fields = [
            'id_incendio',
            'leyenda',
            'nombre',
            'propietario',
            'direccion',
            'criticidad',
            'estado',
            'estado_inf',
            'e_mail',
            'capa',
            'nombre_incendio',
            'comuna_incendio',
            'superficie_incendio',
            'estado_incendio',
            'fecha_inicio_incendio',
            # 'near_fid',
            # 'near_dist',
            'SHAPE@X', 
            'SHAPE@Y'
        ]
        fc = os.path.join(arcpy.env.workspace, dataset, capa_puntos_afectados)
        features = []
        datos = []
        with arcpy.da.SearchCursor(fc, fields) as cursor:
            for row in cursor:
                attributes = {}
                attributes['id_incendio'] = row[0]
                attributes['leyenda'] = row[1]
                attributes['nombre'] = row[2]
                attributes['propietario'] = row[3]
                attributes['direccion'] = row[4]
                attributes['criticidad'] = row[5]
                attributes['estado'] = row[6]
                attributes['estado_inf'] = row[7]
                attributes['e_mail'] = row[8]
                attributes['capa'] = row[9]
                attributes['nombre_incendio'] = row[10]
                attributes['comuna_incendio'] = row[11]
                attributes['superficie_incendio'] = row[12]
                attributes['estado_incendio'] = row[13]
                attributes['fecha_inicio_incendio'] = str(row[14])
                # attributes['near_fid'] = row[15]
                # attributes['near_dist'] = row[16]
                features.append({
                    "geometry": {
                        "x": row[15], "y": row[16]
                    },
                    "attributes": attributes
                })
                datos.append(attributes)

        # Delete cursor object
        del cursor
        print('Puntos afectados: ', len(features))
        return datos

    except:
        print("Failed obtener_puntos_afectados (%s)" %
              traceback.format_exc())
        utils.error_log("Failed obtener_puntos_afectados (%s)" %
                        traceback.format_exc())


def obtener_lineas_afectadas():
    """Permite obtener las lineas afectadas por el incendio."""
    try: 
        fields = [
            'id_incendio',
            'leyenda',
            'nombre',
            'propietario',
            'direccion',
            'criticidad',
            'estado',
            'estado_inf',
            'e_mail',
            'capa',
            'nombre_incendio',
            'comuna_incendio',
            'superficie_incendio',
            'estado_incendio',
            'fecha_inicio_incendio',
            # 'near_fid',
            # 'near_dist',
            'SHAPE@JSON'
        ]
        fc = os.path.join(arcpy.env.workspace, dataset, capa_lineas_afectadas)
        features = []
        datos = []
        with arcpy.da.SearchCursor(fc, fields) as cursor:
            for row in cursor:
                attributes = {}
                attributes['id_incendio'] = row[0]
                attributes['leyenda'] = row[1]
                attributes['nombre'] = row[2]
                attributes['propietario'] = row[3]
                attributes['direccion'] = row[4]
                attributes['criticidad'] = row[5]
                attributes['estado'] = row[6]
                attributes['estado_inf'] = row[7]
                attributes['e_mail'] = row[8]
                attributes['capa'] = row[9]
                attributes['nombre_incendio'] = row[10]
                attributes['comuna_incendio'] = row[11]
                attributes['superficie_incendio'] = row[12]
                attributes['estado_incendio'] = row[13]
                attributes['fecha_inicio_incendio'] = str(row[14])
                # attributes['near_fid'] = row[15]
                # attributes['near_dist'] = row[16]
                features.append({
                    "geometry": json.loads(row[15]),
                    "attributes": attributes
                })
                datos.append(attributes)

        # Delete cursor object
        del cursor
        print('Lineas afectadas: ', len(features))
        return datos

    except:
        print("Failed obtener_lineas_afectadas (%s)" %
            traceback.format_exc())
        utils.error_log("Failed obtener_lineas_afectadas (%s)" %
                        traceback.format_exc())


def generar_alertas(entidades):
    """
    Se envia solo un correo por incendio.
    Envío una alerta a cada correo afectada por un incendio.
    Se envia el listado completo de las infraestructuras afectadas de la empresa.
    Se utiliza el correo electrónico registrado por cada infraestructura para agrupar.
    Se envia un resumen de los incendios e infraestructuras afectadas al ministerio de energia.
    """
    try:
        arcpy.AddMessage("Generando alertas...")
        utils.log("Generando alertas")
        
        print('cantidad entidades: ', len(entidades))

        if len(entidades) > 0:
            # Agrupo la data por id_incendio
            data_por_incendio = agrupar_data_por_incendio(entidades)

            # Recorro la data agrupada por incendio y la vuelvo a agrupar por correo
            for incendio in data_por_incendio:

                id_incendio = incendio
                comuna_incendio = data_por_incendio[incendio]['comuna']
                superficie = data_por_incendio[incendio]['superficie']

                fc = os.path.join(arcpy.env.workspace, dataset, capa_incendios)
                with arcpy.da.SearchCursor(fc, ["id_incendio", "informado"]) as cursor:
                    for row in cursor:
                        # Envío alertas a los incendios que no se han informado.
                        if row[0] == id_incendio and row[1] != True:
                            # Envío por cada incendio, una alerta al ministerio de energía con el resumen de todas las instalaciones afectadas.
                            # aca no debo considerar los incendios ya informados.
                            utils.enviar_correo_admin(
                                    id_incendio,
                                    comuna_incendio,
                                    superficie,
                                    data_por_incendio[incendio]['instalaciones']
                                )

                            # Para el caso de las empresas, agrupo la data por email
                            data_por_correo = agrupar_por_correo(data_por_incendio[incendio]['instalaciones'])
                            if bool(data_por_correo):
                                for correo in data_por_correo:

                                    # Por cada correo registrado, envío una alerta con todas las instalaciones afectadas.
                                    utils.enviar_correo_empresa(
                                        correo,
                                        id_incendio,
                                        comuna_incendio,
                                        superficie,
                                        data_por_correo[correo]['instalaciones']
                                    )
                            
                            # Actualizo el incendio a informado.
                            with arcpy.da.UpdateCursor(fc, ['id_incendio', 'informado']) as cursor_update:
                                for row_u in cursor_update:
                                    if row_u[0] == id_incendio:
                                        row_u[1] = True
                                    cursor_update.updateRow(row_u)
                            del cursor_update
                del cursor


    except:
        print("Failed generar_alertas (%s)" %
            traceback.format_exc())
        utils.error_log("Failed generar_alertas (%s)" %
                        traceback.format_exc())


def agrupar_data_por_incendio(instalaciones):
    """Agrupo por incendio (id_incendio) la data de las instalaciones afectadas."""
    try:
        data = {}
        incendios = []
        
        # Obtengo un listado único de incendios
        for instalacion in instalaciones:
            if ((instalacion['id_incendio'] not in incendios) and (instalacion['id_incendio'] != '')):
                incendios.append(instalacion['id_incendio'])
                data[instalacion['id_incendio']] = {
                    'comuna': instalacion['comuna_incendio'],
                    'superficie': instalacion['superficie_incendio'],
                    # 'near_dist': instalacion['near_dist'],
                    'instalaciones': [],
                }

        print('incendios unicos: ', incendios)

        # Recorro las instalaciones afectadas y las agrupo por correo
        for instalacion in instalaciones:
            if instalacion['id_incendio'] in incendios:
                data[instalacion['id_incendio']]['instalaciones'].append(instalacion)

        return data

    except:
        print("Failed agrupar_data_por_incendio (%s)" %
            traceback.format_exc())
        utils.error_log("Failed agrupar_data_por_incendio (%s)" %
                        traceback.format_exc())


def agrupar_por_correo(instalaciones):
    """Agrupo por mail (E_MAIL) la data de las instalaciones afectadas."""
    try:
        data = {}
        correos = []

        # Obtengo un listado único de correos
        for instalacion in instalaciones:
            if ((instalacion['e_mail'] not in correos) and (instalacion['e_mail'] != '')):
                correos.append(instalacion['e_mail'])
                data[instalacion['e_mail']] = {
                    'instalaciones': [],
                }

        print('correos unicos: ', correos)

        # Recorro las instalaciones afectadas y las agrupo por correo
        for instalacion in instalaciones:
            if instalacion['e_mail'] in correos:
                data[instalacion['e_mail']]['instalaciones'].append(instalacion)

        return data

    except:
        print("Failed agrupar_por_correo (%s)" %
            traceback.format_exc())
        utils.error_log("Failed agrupar_por_correo (%s)" %
                        traceback.format_exc())


def ejecutar_cercania(in_features):
    """Ejecuta la cercania de las instalaciones afectadas (puntos y lineas) respecto del incendio."""
    try:
        arcpy.AddMessage("Ejecutando cercanía..." + in_features)
        utils.log("Ejecutando cercanía " + in_features)
        # set local variables
        near_features = [capa_incendios]
        # find features only within search radius
        search_radius = "5,5 Kilometers"
        # find location nearest features
        location = "NO_LOCATION"
        # avoid getting angle of neares features
        angle = "NO_ANGLE"
        method = "GEODESIC"
        # execute the function
        arcpy.Near_analysis(in_features, near_features, search_radius, location, angle, method)

    except:
        print("Failed ejecutar_cercania (%s)" %
              traceback.format_exc())
        utils.error_log("Failed ejecutar_cercania (%s)" %
                        traceback.format_exc())


if __name__ == '__main__':
    main()
