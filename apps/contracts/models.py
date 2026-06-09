from django.db import models


class PublicContract(models.Model):
    cedula_institucion = models.BigIntegerField(db_column="CEDULA_INSTITUCION", null=True, blank=True)
    institucion = models.CharField(db_column="INSTITUCION", max_length=255, null=True, blank=True)
    nro_procedimiento = models.CharField(db_column="NRO_PROCEDIMIENTO", max_length=120, null=True, blank=True)
    descripcion = models.TextField(db_column="DESCRIPCION", null=True, blank=True)
    tipo_procedimiento = models.CharField(db_column="TIPO_PROCEDIMIENTO", max_length=120, null=True, blank=True)
    modalidad_procedimiento = models.CharField(db_column="MODALIDAD_PROCEDIMIENTO", max_length=120, null=True, blank=True)
    excepcion_cd = models.CharField(db_column="EXCEPCION_CD", max_length=60, null=True, blank=True)
    cod_unidad_compra = models.BigIntegerField(db_column="COD_UNIDAD_COMPRA", null=True, blank=True)
    nombre_unidad_compra = models.CharField(db_column="NOMBRE_UNIDAD_COMPRA", max_length=255, null=True, blank=True)
    pago_adelantado_pymes = models.CharField(db_column="PAGO_ADELANTADO_PYMES", max_length=8, null=True, blank=True)
    fecha_invitacion = models.CharField(db_column="FECHA_INVITACION", max_length=40, null=True, blank=True)
    fecha_inicio_recepcion = models.CharField(db_column="FECHA_INICIO_RECEPCION", max_length=40, null=True, blank=True)
    fecha_cierre_recepcion = models.CharField(db_column="FECHA_CIERRE_RECEPCION", max_length=40, null=True, blank=True)
    fecha_apertura = models.CharField(db_column="FECHA_APERTURA", max_length=40, null=True, blank=True)
    numero_partida = models.BigIntegerField(db_column="NUMERO_PARTIDA", null=True, blank=True)
    numero_linea = models.BigIntegerField(db_column="NUMERO_LINEA", null=True, blank=True)
    cantidad_solicitada = models.FloatField(db_column="CANTIDAD_SOLICITADA", null=True, blank=True)
    precio_unitario_estimado = models.FloatField(db_column="PRECIO_UNITARIO_ESTIMADO", null=True, blank=True)
    tipo_moneda = models.CharField(db_column="TIPO_MONEDA", max_length=10, null=True, blank=True)
    tipo_cambio_usd = models.FloatField(db_column="TIPO_CAMBIO_USD", null=True, blank=True)
    codigo_identificacion = models.BigIntegerField(db_column="CODIGO_IDENTIFICACION", null=True, blank=True)
    descrip_identificacion = models.TextField(db_column="DESCRIP_IDENTIFICACION", null=True, blank=True)

    class Meta:
        managed = False
        db_table = "public_contracts"
