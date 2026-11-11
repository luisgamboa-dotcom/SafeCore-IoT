def dispositivosOrganizacion_sql(campo):
    return f"""{campo} IN (
                    SELECT d2.id_dispositivo FROM dispositivos d2
                    JOIN zonas z2 ON z2.id_zona = d2.id_zona
                    JOIN instalaciones i2 ON i2.id_instalacion = z2.id_instalacion
                    WHERE i2.id_organizacion = %s)"""


def id_organizacion_filter(campo, id_organizacion):
    return "" if id_organizacion is None else f"AND {dispositivosOrganizacion_sql(campo)}"