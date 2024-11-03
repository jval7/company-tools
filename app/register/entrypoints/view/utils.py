import datetime
import os
from os import system

from app.register import model
from app.register.entrypoints.view import money_format

try:
    from win32printing import Printer
except Exception as error:
    print(error)


def clear() -> None:
    if os.name == "posix":
        clear_command = "clear"
    else:
        clear_command = "cls"
    system(clear_command)


def show_items_value(bill: model.Bill) -> None:
    clear()
    print("+++++++++++++")
    print("L I S T A  D E  P R O D U C T O S")
    for i in bill.items:
        print(money_format.SetMoneda(i.price))  # type: ignore
    print("Subtotal: ", money_format.SetMoneda(bill.get_total()))  # type: ignore
    print("+++++++++++++")


def show_total_sales(daily_shift: model.DailyShift) -> None:
    clear()
    print("+++++++++++++")
    print("V E N T A  T O T A L")
    print("Id  |  Valor  |  Fecha")
    for i in daily_shift.bills:
        print(i.id, money_format.SetMoneda(i.total), i.get_date_in_isoformat())  # type: ignore
    print("Total: ", money_format.SetMoneda(daily_shift.total))  # type: ignore
    print("+++++++++++++")


def print_last(bill: model.Bill) -> None:
    font = {
        "height": 11,
    }
    fontg = {
        "height": 14,
    }
    date = datetime.datetime.today()
    string = (
        "       "
        + str(date.day)
        + "-"
        + str(date.month)
        + "-"
        + str(date.year)
        + " "
        + str(date.hour)
        + ":"
        + str(date.minute)
        + ":"
        + str(date.second)
    )
    with Printer(linegap=1) as printer:
        printer.text("       CACHARRERIA MUNOZ", align="center", font_config=fontg)
        printer.text("        Cra 12a # 2-23", align="center", font_config=fontg)
        printer.text("      Nit. 1.062.309.077", align="center", font_config=fontg)
        printer.text(string, align="center", font_config=fontg)
        printer.text("        CUENTA DE COBRO", align="center", font_config=fontg)
        printer.text(" ", align="center", font_config=font)
        printer.text(" ", align="center", font_config=font)
        printer.text("Productos: ", align="left", font_config=font)
        for i in bill.items:
            printer.text(
                money_format.SetMoneda(i.price), align="left", font_config=font  # type: ignore
            )
        printer.text("Total", align="center", font_config=font)
        printer.text(money_format.SetMoneda(bill.total), align="left", font_config=font)  # type: ignore
        printer.text("    GRACIAS POR SU COMPRA", align="center", font_config=fontg)
        printer.text("       VUELVA PRONTO!", align="center", font_config=fontg)
        printer.text(" ", align="center", font_config=font)
        printer.text(" ", align="center", font_config=font)


def open_register() -> None:
    font = {
        "height": 15,
    }
    with Printer(linegap=1) as printer:
        printer.text("", align="center", font_config=font)


def show_commands() -> None:
    clear()
    print("+++++++++++++")
    print("C O M A N D O S  D I S P O N I B L E S")
    print("1. [number] - Agregar un producto con el valor especificado")
    print("2. b - Eliminar el último producto agregado")
    print("3. t | - - Mostrar las ventas totales del día")
    print("4. [enter] - Guardar la factura actual")
    print("5. nt - Ingresar una nota de crédito")
    print("6. p | + - Imprimir la última factura")
    print("7. . - Abrir la caja registradora")
    print("8. h | help - Mostrar los comandos disponibles")
    print("+++++++++++++")
