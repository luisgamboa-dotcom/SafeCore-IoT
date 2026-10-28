"""Conversion de la cuenta ADC del MQ-2 a ppm estimado de gas inflamable (LPG).

El nodo (firmware/safecoreNode.ino) envia el valor crudo de analogRead(A0),
una cuenta en escala 0-1023 a 3.3 V, sin conversion. Esta capa traduce esa
cuenta a ppm con la curva del datasheet del MQ-2 para gas LPG:

    ppm = 579.41 * ratio ^ -1.3409        con ratio = Rs / R0

donde Rs se deduce del divisor del modulo (RL = 5 kOhm, VCC = 5 V):

    VRL = ADC / 1023 * 3.3     Rs = RL * (VCC - VRL) / VRL

R0 (resistencia del sensor en aire limpio) se ESTIMA a partir del minimo de las
lecturas historicas del proyecto (ADC ~ 38, aire limpio; factor aire limpia del
datasheet Rs/R0 ~ 9.83). Limitacion documentada: sin calibracion contra gas real
(R0 preciso) el ppm es un ESTIMADO, suficiente para el panel y las reglas.

Alcance:
- La conversion corre SOLO en el servidor (ingesta); el firmware sigue
  enviando cuentas ADC (sus alarmas locales THR=200 siguen en ADC).
- Las lecturas historicas en BD (magnitud 1) se migran con la misma formula
  (ver sql/migrar_gas_adc_a_ppm.sql).
"""

ADC_MAX = 1023          # escala del ADC del ESP8266 (10 bits)
VREF = 3.3              # voltaje maximo de entrada del ADC (V)
VCC_MODULO = 5.0        # alimentacion del MQ-2 (V)
RL_OHMS = 5000.0        # resistencia de carga del modulo MQ-2
# Curva LPG del datasheet del MQ-2 (aprox log-log).
CURVA_A = 579.41
CURVA_B = 1.3409
# Estimacion de R0: lectura de referencia en aire limpio y factor del datasheet.
AIRE_LIMPIO_ADC = 38.0
FACTOR_AIRE_LIMPIO = 9.83

_VRL_AIRE = AIRE_LIMPIO_ADC / ADC_MAX * VREF
R0_OHMS = RL_OHMS * (VCC_MODULO - _VRL_AIRE) / _VRL_AIRE / FACTOR_AIRE_LIMPIO


def adc_a_ppm(adc):
    """Convierte una cuenta ADC del MQ-2 (0-1023) a ppm estimado de LPG."""
    adc = float(adc)
    if adc <= 0:
        return 0.0
    vrl = adc / ADC_MAX * VREF
    rs = RL_OHMS * (VCC_MODULO - vrl) / vrl
    return round(CURVA_A * (rs / R0_OHMS) ** -CURVA_B, 2)
