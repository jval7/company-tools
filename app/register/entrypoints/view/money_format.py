# type: ignore


def SetMoneda(num: int | float, simbolo: str = "$", n_decimales: int = 0) -> str:
    """Convierte el numero en un string en formato moneda
    SetMoneda(45924.457, 'RD$', 2) --> 'RD$ 45,924.46'
    """
    # con abs, nos aseguramos que los dec. sea un positivo.
    n_decimales = abs(n_decimales)

    # se redondea a los decimales idicados.
    num = round(num, n_decimales)

    # se divide el entero del decimal y obtenemos los string
    try:
        num, dec = str(num).split(".")
        dec += "0" * (n_decimales - len(dec))
    except ValueError:
        num = str(num)
    # si el num tiene menos decimales que los que se quieren mostrar,
    # se completan los faltantes con ceros.

    # se invierte el num, para facilitar la adicion de comas.
    num = num[::-1]

    # se crea una lista con las cifras de miles como elementos.
    list_of_thousands = [
        num[pos : pos + 3][::-1] for pos in range(0, 50, 3) if (num[pos : pos + 3])
    ]
    list_of_thousands.reverse()

    # se pasa la lista a string, uniendo sus elementos con comas.
    num = str.join(",", list_of_thousands)

    # si el numero es negativo, se quita una coma sobrante.
    try:
        if num[0:2] == "-,":
            num = "-%s" % num[2:]
    except IndexError:
        pass

    # si no se especifican decimales, se retorna un numero entero.
    if not n_decimales:
        return "%s %s" % (simbolo, num)

    return "%s %s.%s" % (simbolo, num)  # noqa: F507
