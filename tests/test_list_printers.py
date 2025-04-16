import logging

from tsclib import TSCPrinter


logging.basicConfig(level=logging.DEBUG)
logging.info("--- TSC Printer Module Test ---")

printer = TSCPrinter()

logging.info("--- Getting DLL Info ---")
print(f"DLL About Info: {printer.list_printers()}")

print(printer.open_port(0))
print(printer.close_port())
