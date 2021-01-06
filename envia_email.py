#-------------------------------------------------------------------------------
# Name:         envia_email
# Purpose:      Envía correo electrónico
#
# Author:       Fredys Barrera Artiaga <fbarrera@esri.cl>
# Created:      27-05-2020
# Copyright:    (c) fbarrera 2020
# Licence:      <your licence>
#-------------------------------------------------------------------------------

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from decouple import config
import template_html as template
import traceback
import utils

#-------------------------------------------------------------------------------
# Configuracion correo
#-------------------------------------------------------------------------------
host = config('EMAIL_HOST')
port = config('EMAIL_PORT')
smtp_server = host + ':' + port
username = config('EMAIL_USERNAME')
password = config('EMAIL_PASSWORD')
destinatario_admin = config('EMAIL_TO_ADMIN')
email_from = config('EMAIL_FROM')

# Flag para enviar o no el mail
enviar_mail = config('EMAIL_SEND')


# Envio alerta de email a la empresa responsable de la instalación
def enviar_email_empresa(destinatario, subject, texto_instalaciones, nombre_incendio):
    try:
        # Construyo los encabezados
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = email_from
        message["To"] = destinatario

        # Construyo el cuerpo del correo en HTML
        # Obtengo el template para el envío de correo a una empresa
        html = template.get_template_empresa(texto_instalaciones, nombre_incendio)
        part = MIMEText(html, "html")
        message.attach(part)

        # Envío el correo
        send(destinatario, message)
    except:
        print("Failed enviar_email_empresa (%s)" %
              traceback.format_exc())
        utils.error_log("Failed enviar_email_empresa (%s)" %
                        traceback.format_exc())


# Envío alerta de correo con el resumen del incendio al administrador del sistema
def enviar_email_admin(id_incendio, comuna_incendio, superficie, subject, texto_instalaciones, nombre_incendio):
    try:
        # Construyo los encabezados
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = email_from
        message["To"] = destinatario_admin

        # Construyo el cuerpo del correo en HTML
        # Obtengo el template para el envío de correo a una empresa
        html = template.get_template_admin(id_incendio, comuna_incendio, superficie, texto_instalaciones, nombre_incendio)
        part = MIMEText(html, "html")
        message.attach(part)

        # Envío el correo
        send(destinatario_admin, message)
    except:
        print("Failed enviar_email_admin (%s)" %
              traceback.format_exc())
        utils.error_log("Failed enviar_email_admin (%s)" %
                        traceback.format_exc())


# Envío alerta de correo al administrador del sistema informado que el incendio está extinguido.
def enviar_email_admin_extinguido(id_incendio, comuna_incendio, subject, fecha_inicio_incendio, nombre_incendio):
    try:
        # Construyo los encabezados
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = email_from
        message["To"] = destinatario_admin

        # Construyo el cuerpo del correo en HTML
        # Obtengo el template para el envío de correo a una empresa
        html = template.get_template_admin_extinguido(id_incendio, comuna_incendio, fecha_inicio_incendio, nombre_incendio)
        part = MIMEText(html, "html")
        message.attach(part)

        # Envío el correo
        send(destinatario_admin, message)
    except:
        print("Failed enviar_email_admin_extinguido (%s)" %
              traceback.format_exc())
        utils.error_log("Failed enviar_email_admin_extinguido (%s)" %
                        traceback.format_exc())


# Envio el correo
def send(to, message):
    try:
        if enviar_mail == 'true':
            # Creo el objeto para el envío del correo
            server = smtplib.SMTP(smtp_server)
            server.starttls()
            server.login(username, password)
            server.sendmail(username, to, message.as_string())
            server.quit()
    except:
        print("Failed send (%s)" % traceback.format_exc())
        utils.error_log("Failed send (%s)" %
                        traceback.format_exc())
