import os

DEFAULT_PLATFORM_FEE_PCT = 30.0


def platform_fee_pct() -> float:
    """Comisión de la plataforma sobre cada venta (%). Env: PLATFORM_FEE_PCT.

    Se lee en cada llamada para poder ajustarla sin redeploy; acotada 0-100.
    """
    try:
        value = float(os.getenv("PLATFORM_FEE_PCT", DEFAULT_PLATFORM_FEE_PCT))
    except ValueError:
        value = DEFAULT_PLATFORM_FEE_PCT
    return max(0.0, min(100.0, value))
