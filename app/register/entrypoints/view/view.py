import aioconsole
from colorama import Fore, Back, Style

from app.register import usecases
from app.register.entrypoints.view import utils
from app.register.entrypoints.cron import Sync


async def start_view(register: usecases.Register, syncronizer: Sync = None) -> None:
    while True:
        cmd = None
        try:
            command = str(await aioconsole.ainput("Digita el valor Producto: "))
            match command:
                case _ if command.isdigit():
                    cmd = "number"
                    if 500_000 > int(command) > 0:
                        register.add_item(price=float(command))
                        utils.show_items_value(bill=register.get_current_bill())  # type: ignore
                    elif int(command) >= 500000:
                        print(
                            Style.BRIGHT
                            + Back.YELLOW
                            + Fore.BLACK
                            + "presione + y doble enter para registrar este valor mayor a $500.000, de lo contrario enter"
                        )
                        if str(await aioconsole.ainput("")) == "+":
                            register.add_item(price=float(command))
                            utils.show_items_value(bill=register.get_current_bill())  # type: ignore
                            print(Style.RESET_ALL)
                        print(Style.RESET_ALL)
                case "b":
                    cmd = "b"
                    register.remove_last_item()
                    utils.show_items_value(bill=register.get_current_bill())  # type: ignore
                case "t" | "-":
                    cmd = "t"
                    daily_shift = await register.get_daily_shift()
                    if not daily_shift:
                        raise Exception("No hay ventas")
                    utils.show_total_sales(daily_shift=daily_shift)
                case "":
                    cmd = "enter"
                    await register.save_bill()
                    utils.open_register()
                case "nt":
                    cmd = "nt"
                    value = float(
                        await aioconsole.ainput(
                            "Ingrese el valor para la nota credito: "
                        )
                    )
                    if value >= 0:
                        register.add_item(price=-value)
                        await register.save_bill()
                    else:
                        raise Exception("Valor invalido")
                case "p" | "+":
                    cmd = "p"
                    daily_shift = await register.get_daily_shift()
                    last_bill = daily_shift.bills[-1]
                    utils.print_last(bill=last_bill)

                case ".":
                    cmd = "."
                    utils.open_register()
                case "h" | "help":
                    cmd = "h"
                    utils.show_commands()
                case "sync" | "s":
                    cmd = "sync"
                    if syncronizer:
                        print("Iniciando sincronización manual...")
                        await syncronizer.sync_bills()
                        print("Sincronización completada.")
                    else:
                        print("Error: Sincronizador no disponible")
                case _:
                    print("Comando no encontrado")
        except Exception as e:
            # write log to file with the traceback and the command
            with open("error.log", "a") as file:
                file.write(f"{e} - {cmd}\n")

            print("Error: ", e)
