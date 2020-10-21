
#-------------------------------------------------------------------------------
# Name:         testMail
# Purpose:      Envía correo electrónico de prueba.
#
# Author:       Fredys Barrera Artiaga <fbarrera@esri.cl>
# Created:      30-09-2020
# Copyright:    (c) fbarrera 2020
# Licence:      <your licence>
#-------------------------------------------------------------------------------

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from decouple import config
import template_html as template
import traceback
import utils
import envia_email as email

#-------------------------------------------------------------------------------
# Configuracion correo
#-------------------------------------------------------------------------------
destinatario_admin = config('EMAIL_TO_ADMIN')
email_from = config('EMAIL_FROM')


def test_mail():
    """Permite probar envío de email."""
    try:
        utils.log("Inicio test mail")
        print("Inicio test mail")
        utils.log("Enviando mail desde {} a {}".format(email_from, destinatario_admin))
        print("Enviando mail desde {} a {}".format(email_from, destinatario_admin))

        # Construyo los encabezados
        message = MIMEMultipart("alternative")
        message["Subject"] = "Test mail"
        message["From"] = email_from
        message["To"] = destinatario_admin

        # Construyo el cuerpo del correo en HTML
        # Obtengo el template para el envío de correo a una empresa
        html = template.get_template_empresa('<b>Texto de prueba...</b>')
        part = MIMEText(html, "html")
        message.attach(part)

        # Envío el correo
        email.send(destinatario_admin, message)
        utils.log("Fin test mail\n")
        print("Fin test mail\n")
    except:
        print("Failed test_mail (%s)" %
              traceback.format_exc())
        utils.error_log("Failed test_mail (%s)" %
                        traceback.format_exc())


if __name__ == '__main__':
    test_mail()