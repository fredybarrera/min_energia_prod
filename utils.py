#-------------------------------------------------------------------------------
# Name:         utils
# Purpose:      Utilidades varias
#
# Author:       Fredys Barrera Artiaga <fbarrera@esri.cl>
# Created:      12-04-2020
# Copyright:    (c) fbarrera 2020
# Licence:      <your licence>
#-------------------------------------------------------------------------------

import arcpy
import envia_email as email
from bs4 import BeautifulSoup
from datetime import datetime
import constants as const
import xml.etree.ElementTree as et
import urllib.request as ur
import requests
import traceback
import json
import os

script_dir = os.path.dirname(__file__)

# DATASET
dataset = const.DATASET
# Workspace
arcpy.env.workspace = const.WORKSPACE
# Folder local
folder_local = const.WORKSPACE_LOCAL
# Sobreescribo la misma capa de salida
arcpy.env.overwriteOutput = True
# Set the preserveGlobalIds environment to True
arcpy.env.preserveGlobalIds = True
# Buffer incendios temporal
capa_buffer_incendios = const.BUFFER_INCENDIOS
# Capa estaciones meteorológicas
capa_estaciones_meteorologicas = const.ESTACIONES_METEOROLOGICAS
# Prefijo del nombre de los datos
USER_DATOS = const.USER_DATOS

def get_data_kml(url):
    """Obtiene la data desde el servicio de Conaf (KML)."""
    try:
        data = et.ElementTree(file=ur.urlopen(url))
        return data
    except:
        print("Failed get_data_kml (%s)" %
              traceback.format_exc())
        utils.error_log("Failed get_data_kml (%s)" %
                        traceback.format_exc())


def post_request_json_raw_data(url, raw_data):
    """Realiza una peticion http de tipo POST con raw_data en formato json."""
    try:
        response = requests.post(url, json=raw_data)
        if response.status_code == 200:
            data = response.json()
            return data
        return False
    except:
        print("Failed post_request_payload (%s)" %
              traceback.format_exc())
        utils.error_log("Failed post_request_payload (%s)" %
                        traceback.format_exc())


def get_data_iframe(id_incendio):
    """Retorna el detalle de un incendio desde el iframe."""
    try:
        arcpy.AddMessage("Obteniendo data iframe de incendio_id: " + id_incendio)

        # open iframe src url
        response = ur.urlopen('http://sidco.conaf.cl/mapa/popup.php?id=' + id_incendio + '&key=mEiNnE2k18')

        iframe_soup = BeautifulSoup(response, "html.parser")

        # Busco sonbre el div dentro del iframe que contiene la información adicional del incendio.
        entradas = iframe_soup.find_all('div', {'id': 'tabla-ficha-' + id_incendio + '_div'})

        data = []

        for entrada in entradas:
            # fecha y hora de inicio del incendio
            data.append(entrada.find(
                'span', {'class': 'incendio-fecha'}).getText())
            # comuna del incendio
            data.append(entrada.find(
                'span', {'class': 'incendio-comuna'}).getText())
            # superficie afectada
            data.append(entrada.find(
                'span', {'class': 'incendio-superficie'}).getText())
            # Estado del incendio
            data.append(entrada.find('strong').getText())

        return data

    except:
        print("Failed get_data_iframe (%s)" % traceback.format_exc())
        utils.error_log("Failed get_data_iframe (%s)" %
                        traceback.format_exc())


def get_data_iframe_aux(id_incendio):
    """Método auxiliar para simular data obtenida desde un iframe, 
    se usa para cargar un kml local que tiene información desactualizada.
    """

    return ['31-may-2020 16:27', 'Valparaíso', '10 ha', 'En Combate']


def truncar_data_dataset(table):
    """Trunca la informacion de una tabla dentro del dataset."""
    try:
        arcpy.AddMessage("Limpiando capa " + table + "...")

        fc = os.path.join(arcpy.env.workspace, dataset, table)

        print('fc: ', fc)

        # Truncate a feature class if it exists
        if arcpy.Exists(fc):
            print('existe: ', table)
            arcpy.TruncateTable_management(fc)

    except:
        print("Failed truncar_data_dataset (%s)" % traceback.format_exc())
        utils.error_log("Failed truncar_data_dataset (%s)" %
                        traceback.format_exc())


def delete_temp_tables():
    """Elimina las tablas temporales creadas en el proceso."""
    try:
        tables = const.TABLES_SIGGRE

        for table in tables:
            name = table.split(USER_DATOS)
            # print('name: ', name)
            t = "cruce_" + name[1]
            # t = 'cruce_' + table
            # fc = os.path.join(arcpy.env.workspace, t)
            fc = os.path.join(folder_local, t)
            arcpy.AddMessage("Eliminando capa temporal " + t + " ...")
            # Delete a feature class if it exists
            if arcpy.Exists(fc):
                arcpy.Delete_management(fc)
        

        # fc = os.path.join(arcpy.env.workspace, capa_buffer_incendios)
        fc = os.path.join(folder_local, capa_buffer_incendios)
        arcpy.AddMessage("Eliminando capa temporal " + capa_buffer_incendios + " ...")
        # Delete a feature class if it exists
        if arcpy.Exists(fc):
            arcpy.Delete_management(fc)
                
    except:
        print("Failed delete_temp_tables (%s)" % traceback.format_exc())
        utils.error_log("Failed delete_temp_tables (%s)" %
                        traceback.format_exc())


def enviar_correo_empresa(destinatario, id_incendio, comuna_incendio, superficie, instalaciones):
    """Envía correo electrónico a la empresa afectada."""
    try:
        hora_reporte = str(datetime.now())
        texto_instalaciones = '<table><thead style="background-color:#215868;color:white"><tr>'
        texto_instalaciones += '<td>Fecha y hora</td>'
        texto_instalaciones += '<td>Número/Nombre Incendio</td>'
        texto_instalaciones += '<td>Comuna</td>'
        texto_instalaciones += '<td>Superficie (ha)</td>'
        texto_instalaciones += '<td>Tipo Infraestructura</td>'
        texto_instalaciones += '<td>Nombre Infraestructura</td>'
        texto_instalaciones += '<td>Empresa</td>'
        # texto_instalaciones += '<td>Distancia Infraestructura hacia el foco de incendio(m)</td>'
        texto_instalaciones += '<td>Hora del reporte</td>'
        texto_instalaciones += '</tr></thead>'
        texto_instalaciones += '<tbody>'
        for instalacion in instalaciones:
            texto_instalaciones += '<tr>'
            texto_instalaciones += '<td>' + instalacion['fecha_inicio_incendio'] + '</td>'
            texto_instalaciones += '<td>' + instalacion['id_incendio'] + '<br/> '+ instalacion['nombre_incendio'] +'</td>'
            texto_instalaciones += '<td>' + instalacion['comuna_incendio'] + '</td>'
            texto_instalaciones += '<td>' + instalacion['superficie_incendio'] + '</td>'
            texto_instalaciones += '<td>' + instalacion['capa'] + '</td>'
            texto_instalaciones += '<td>' + instalacion['nombre'] + '</td>'
            texto_instalaciones += '<td>' + instalacion['propietario'] + '</td>'
            # texto_instalaciones += '<td>' + str(int(instalacion['near_dist'])) + '</td>'
            texto_instalaciones += '<td>' + hora_reporte + '</td>'
            texto_instalaciones += '</tr>'
        texto_instalaciones += '</tbody>'
        texto_instalaciones += '</table>'

        subject = "[Empresa] - Incendio N° " + id_incendio + ", comuna de " + comuna_incendio

        email.enviar_email_empresa(destinatario, subject, texto_instalaciones)

    except:
        print("Failed enviar_correo_empresa (%s)" % traceback.format_exc())
        utils.error_log("Failed enviar_correo_empresa (%s)" %
                        traceback.format_exc())


def enviar_correo_admin(id_incendio, comuna_incendio, superficie, instalaciones):
    """Envía correo electrónico al ministerio de energía."""
    try:
        hora_reporte = str(datetime.now())
        texto_instalaciones = '<table><thead style="background-color:#215868;color:white"><tr>'
        texto_instalaciones += '<td>Fecha y hora</td>'
        texto_instalaciones += '<td>Número/Nombre Incendio</td>'
        texto_instalaciones += '<td>Comuna</td>'
        texto_instalaciones += '<td>Superficie (ha)</td>'
        texto_instalaciones += '<td>Tipo Infraestructura</td>'
        texto_instalaciones += '<td>Nombre Infraestructura</td>'
        texto_instalaciones += '<td>Empresa</td>'
        # texto_instalaciones += '<td>Distancia Infraestructura hacia el foco de incendio(m)</td>'
        texto_instalaciones += '<td>Hora del reporte</td>'
        texto_instalaciones += '</tr></thead>'
        texto_instalaciones += '<tbody>'
        for instalacion in instalaciones:
            texto_instalaciones += '<tr>'
            texto_instalaciones += '<td>' + instalacion['fecha_inicio_incendio'] + '</td>'
            texto_instalaciones += '<td>' + instalacion['id_incendio'] + '<br/> '+ instalacion['nombre_incendio'] +'</td>'
            texto_instalaciones += '<td>' + instalacion['comuna_incendio'] + '</td>'
            texto_instalaciones += '<td>' + instalacion['superficie_incendio'] + '</td>'
            texto_instalaciones += '<td>' + instalacion['capa'] + '</td>'
            texto_instalaciones += '<td>' + instalacion['nombre'] + '</td>'
            texto_instalaciones += '<td>' + instalacion['propietario'] + '</td>'
            # texto_instalaciones += '<td>' + str(int(instalacion['near_dist'])) + '</td>'
            texto_instalaciones += '<td>' + hora_reporte + '</td>'
            texto_instalaciones += '</tr>'
        texto_instalaciones += '</tbody>'
        texto_instalaciones += '</table>'

        subject = "[Admin] - Incendio N° " + id_incendio + ", comuna de " + comuna_incendio

        email.enviar_email_admin(
            id_incendio, 
            comuna_incendio, 
            superficie, 
            subject, 
            texto_instalaciones)

    except:
        print("Failed enviar_correo_admin (%s)" % traceback.format_exc())
        utils.error_log("Failed enviar_correo_admin (%s)" %
                        traceback.format_exc())


def enviar_correo_admin_extinguido(id_incendio, fecha_inicio_incendio, comuna_incendio):
    """Envía correo electrónico informando que el incendio se ha extinguido."""
    try:

        subject = "[Extinguido] - Incendio N° " + id_incendio + " extinguido"

        email.enviar_email_admin_extinguido(
            id_incendio,
            comuna_incendio,
            subject,
            fecha_inicio_incendio)

    except:
        print("Failed enviar_correo_admin_extinguido (%s)" % traceback.format_exc())
        utils.error_log("Failed enviar_correo_admin_extinguido (%s)" %
                        traceback.format_exc())


def convert_seconds(seconds):
    """Convert seconds into hours, minutes and seconds."""
    seconds = seconds % (24 * 3600)
    hour = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60

    return "%d:%02d:%02d" % (hour, minutes, seconds)


def actualizar_agromet():
    """Actualiza la variable de la direccion del viento de cada estacion meteorológica."""
    try:
        # Obtengo las estaciones meteorológicas
        fc = os.path.join(arcpy.env.workspace, dataset, capa_estaciones_meteorologicas)
        estaciones = []
        datos = []

        with arcpy.da.SearchCursor(fc, ['id', 'nombre']) as cursor:
            for row in cursor:
                estaciones.append(row[0])
        del cursor

        # id_direccion_viento
        # id_humedad_media
        # id_temperatura_media
        # id_velocidad_viento_max
        # id_velocidad_viento_media

        # Hago el llamado a la api por cada estacion para consultar el id de la variable de la direccion del viento
        for id_estacion in estaciones:
            url = 'http://agromet.inia.cl/api/variables?ema=' + str(id_estacion) + '&user=9532d75b835b8074ff3407fd701bd9ba1e8d292d'
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                id_direccion_viento = data['variables'][0]['idEmaVariable']
                id_humedad_media = data['variables'][1]['idEmaVariable']
                id_temperatura_media = data['variables'][2]['idEmaVariable']
                id_velocidad_viento_max = data['variables'][3]['idEmaVariable']
                id_velocidad_viento_media = data['variables'][4]['idEmaVariable']
                datos.append({
                    "id_estacion": int(id_estacion),
                    "id_direccion_viento": int(id_direccion_viento),
                    "id_humedad_media": int(id_humedad_media),
                    "id_temperatura_media": int(id_temperatura_media),
                    "id_velocidad_viento_max": int(id_velocidad_viento_max),
                    "id_velocidad_viento_media": int(id_velocidad_viento_media)
                })

        # # Por cada estacion, actualizo las variables
        for k in datos:
            with arcpy.da.UpdateCursor(fc, ['id', 'id_direccion_viento', 'id_humedad_media', 'id_temperatura_media', 'id_velocidad_viento_max', 'id_velocidad_viento_media']) as cursor:
                for row in cursor:
                    if row[0] == k['id_estacion']:
                        row[1] = k['id_direccion_viento']
                        row[2] = k['id_humedad_media']
                        row[3] = k['id_temperatura_media']
                        row[4] = k['id_velocidad_viento_max']
                        row[5] = k['id_velocidad_viento_media']
                        print('Se actualiza estacion: {0} con id_direccion_viento: {1}'.format(
                            k['id_estacion'], k['id_direccion_viento']))
                    cursor.updateRow(row)
            del cursor

    except:
        print("Failed actualizar_agromet (%s)" % traceback.format_exc())
        utils.error_log("Failed actualizar_agromet (%s)" %
                        traceback.format_exc())


def log(text):
    """Registra un log de proceso. """
    try:
        log_file = os.path.join(script_dir, 'log.txt')
        f = open(log_file, "a", encoding='utf-8')
        f.write(
            "{0} -- {1}\n".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), text))
        f.close()
    except:
        print("Failed log (%s)" %
              traceback.format_exc())
        utils.error_log("Failed send (%s)" %
                        traceback.format_exc())


def error_log(text):
    """Registra un log de error. """
    try:
        log_file = os.path.join(script_dir, 'error-log.txt')
        f = open(log_file, "a")
        f.write(
            "{0} -- {1}\n".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), text))
        f.write("---------------------------------------------------------------- \n")
        f.close()
    except:
        print("Failed error_log (%s)" %
              traceback.format_exc())
              