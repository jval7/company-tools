from datetime import timezone, timedelta, datetime


def get_posix_time_until_day() -> int:
    # Define the Colombian time zone offset (UTC-5)
    colombia_tz = timezone(timedelta(hours=-5))

    # Get the current time in the Colombian time zone
    current_time = datetime.now(colombia_tz)

    # Create a new datetime with hours, minutes, and seconds set to zero
    day_time = current_time.replace(hour=0, minute=0, second=0, microsecond=0)

    # Convert the datetime back to a POSIX timestamp
    return int(day_time.timestamp())


def convert_to_posix(date_str: str) -> int:
    # Define the date format
    date_format = "%d-%m-%Y"

    # Define the Colombian time zone offset (UTC-5)
    colombia_tz = timezone(timedelta(hours=-5))

    # Parse the date string into a datetime object
    date_obj = datetime.strptime(date_str, date_format)

    # Apply Colombian timezone to the datetime object
    date_obj = date_obj.replace(tzinfo=colombia_tz)

    # Convert the datetime object to a POSIX timestamp
    posix_timestamp = int(date_obj.timestamp())

    return posix_timestamp


def get_first_and_last_day_posix() -> tuple[int, int]:
    # Define Colombia timezone offset (UTC-5)
    colombia_offset = timedelta(hours=-5)
    colombia_tz = timezone(colombia_offset)

    # Get current time in Colombia timezone
    now = datetime.now(colombia_tz)

    # Get the first day of the current month
    first_day = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Get the last day of the current month
    if first_day.month == 12:
        next_month = first_day.replace(year=first_day.year + 1, month=1, day=1)
    else:
        next_month = first_day.replace(month=first_day.month + 1, day=1)
    last_day = next_month - timedelta(days=1)
    last_day = last_day.replace(hour=23, minute=59, second=59, microsecond=999999)

    # Convert to POSIX timestamps
    first_day_posix = int(first_day.timestamp())
    last_day_posix = int(last_day.timestamp())

    return first_day_posix, last_day_posix


def SetMoneda(num, simbolo="$", n_decimales=0) -> str:  # type: ignore
    """Convierte el numero en un string en formato moneda
    SetMoneda(45924.457, 'RD$', 2) --> 'RD$ 45,924.46'
    """
    # con abs, nos aseguramos que los dec. sea un positivo.
    n_decimales = abs(n_decimales)

    # se redondea a los decimales idicados.
    num = round(num, n_decimales)

    # se divide el entero del decimal y obtenemos los string
    try:
        num, dec = str(num).split(".")  # type: ignore
        dec += "0" * (n_decimales - len(dec))
    except ValueError:
        num = str(num)
    # si el num tiene menos decimales que los que se quieren mostrar,
    # se completan los faltantes con ceros.

    # se invierte el num, para facilitar la adicion de comas.
    num = num[::-1]

    # se crea una lista con las cifras de miles como elementos.
    l = [num[pos : pos + 3][::-1] for pos in range(0, 50, 3) if (num[pos : pos + 3])]
    l.reverse()

    # se pasa la lista a string, uniendo sus elementos con comas.
    num = str.join(",", l)

    # si el numero es negativo, se quita una coma sobrante.
    try:
        if num[0:2] == "-,":
            num = "-%s" % num[2:]
    except IndexError:
        pass

    # si no se especifican decimales, se retorna un numero entero.
    if not n_decimales:
        return "%s %s" % (simbolo, num)
    return "%s %s.%s" % (simbolo, num)  # type: ignore
