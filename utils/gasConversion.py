
ADC_MAX = 1023
VREF = 3.3
VCC_MODULO = 5.0
RL_OHMS = 5000.0

CURVA_A = 579.41
CURVA_B = 1.3409

AIRE_LIMPIO_ADC = 38.0
FACTOR_AIRE_LIMPIO = 9.83

_VRL_AIRE = AIRE_LIMPIO_ADC / ADC_MAX * VREF
R0_OHMS = RL_OHMS * (VCC_MODULO - _VRL_AIRE) / _VRL_AIRE / FACTOR_AIRE_LIMPIO


def adc_a_ppm(adc):
    adc = float(adc)
    if adc <= 0:
        return 0.0
    vrl = adc / ADC_MAX * VREF
    rs = RL_OHMS * (VCC_MODULO - vrl) / vrl
    return round(CURVA_A * (rs / R0_OHMS) ** -CURVA_B, 2)
