#-------------------------------------------------------------------------------
# Name:         template_html
# Purpose:      Retorna el html para el envío de correos
#
# Author:       Fredys Barrera Artiaga <fbarrera@esri.cl>
# Created:      01-06-2020
# Copyright:    (c) fbarrera 2020
# Licence:      <your licence>
#-------------------------------------------------------------------------------


def get_template_empresa(instalaciones, nombre_incendio):
    return """\
        <html>
        <body>
            <p>Estimados(as):</p>
            <p>Se informa incendio forestal próximo a infraestructura energética, que podría afectar a sus siguientes instalaciones:</p>
            <p>{instalaciones}</p>
            <p><a href="#" target="_blank"></a></p>
            <p style="font-style: italic; font-size: 8px;"></p>
        </body>
        </html>
    """.format(instalaciones=instalaciones)


def get_template_admin(id_incendio, comuna_incendio, superficie, instalaciones, nombre_incendio):
    return """\
        <html>
        <body>
            <p>Estimados(as): </p>
            <p>Se informa que el incendio <b>{nombre_incendio}</b>, ubicado en la comuna de <b>{comuna_incendio}</b>, ha consumido hasta el momento una superficie de <b>{superficie}</b>.</p>
            <p>Instalaciones próximas al incendio:</p>
            <p>{instalaciones}</p>
            <p><a href="#" target="_blank"></a></p>
            <p style="font-style: italic; font-size: 8px;"></p>
        </body>
        </html>
    """.format(nombre_incendio=nombre_incendio, comuna_incendio=comuna_incendio, superficie=superficie, instalaciones=instalaciones)


def get_template_admin_extinguido(id_incendio, comuna_incendio, fecha_inicio_incendio, nombre_incendio):
    return """\
        <html>
        <body>
            <p>Estimados(as): </p>
            <p>Se informa que el incendio <b>{nombre_incendio}</b>, iniciado el dia <b>{fecha_inicio_incendio}</b>, ubicado en la comuna de <b>{comuna_incendio}</b>, ha sido actualizado a <b>Controlado/Extinguido</b>.</p>
            <p><a href="#" target="_blank"></a></p>
            <p style="font-style: italic; font-size: 8px;"></p>
        </body>
        </html>
    """.format(nombre_incendio=nombre_incendio, fecha_inicio_incendio=fecha_inicio_incendio, comuna_incendio=comuna_incendio)
