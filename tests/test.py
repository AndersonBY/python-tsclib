import logging

from tsclib import TSCPrinter, SensorType, BarcodeReadable, Rotation, TSCError


logging.basicConfig(level=logging.DEBUG)  # More verbose logging for testing
logging.info("--- TSC Printer Module Test ---")

# Assumes tsclibnet.dll is in the same directory as this script
# If it's elsewhere, provide the full path:
# DLL_LOCATION = r"C:\path\to\your\tsclibnet.dll"
# printer = TSCPrinter(dll_path=DLL_LOCATION)

try:
    printer = TSCPrinter()  # Uses default path finding

    logging.info("--- Getting DLL Info ---")
    print(f"DLL About Info: {printer.get_about_info()}")

    logging.info("\n--- Running Print Job via Context Manager ---")
    with printer:  # Automatically opens and closes the port
        logging.info("Port opened via context manager.")

        status = printer.get_status()
        print(f"Initial Printer Status: {status}")
        if status != "00":
            # Example: Check if status code indicates common issues
            if status == "01":
                print("WARN: Head Open")
            elif status == "02":
                print("WARN: Paper Jam")
            elif status == "04":
                print("WARN: No Paper")
            elif status == "08":
                print("WARN: Ribbon Empty")
            elif status == "10":
                print("WARN: Paused")
            elif status == "20":
                print("WARN: Printing")
            else:
                print(f"WARN: Printer not ready (Status code: {status}). Check printer.")
            # Decide if to continue or raise error based on status

        # 1. Setup label (Example: 4x3 inch label = ~101mm x 76mm)
        #    Adjust dimensions, speed, density as needed for your printer/labels
        printer.setup_label(
            width_mm="70",  # Adjust
            height_mm="40",  # Adjust
            speed="4.0",  # Adjust
            density="10",  # Adjust
            sensor_type=SensorType.GAP,  # Or SensorType.BLACK_MARK
            gap_mm="3",  # Adjust gap/black mark height
            offset_mm="0",  # Usually 0
        )

        # 2. Clear buffer before adding new elements
        printer.clear_buffer()

        # 3. Add elements to the buffer
        # Internal Font Text
        printer.print_text_internal_font(
            x="50", y="50", font_type="3", rotation=Rotation.DEG_0, x_mul="1", y_mul="1", text="Internal Font Test"
        )

        # Barcode
        printer.print_barcode(
            x="50",
            y="100",
            barcode_type="128",
            height="70",
            readable=BarcodeReadable.YES,
            rotation=Rotation.DEG_0,
            narrow_bar_mul="2",
            wide_bar_mul="1",
            code="TEST12345",
        )

        # Windows Font Text (Ensure Arial is installed)
        printer.print_text_windows_font(
            x=50,
            y=250,
            font_height=48,
            rotation=0,
            font_style=0,
            font_underline=0,
            font_face_name="Arial",
            text="Windows Arial Test",
        )

        # Send a raw command (Example: Draw a box)
        printer.send_command("BOX 50,350,600,450,3")  # x1,y1,x2,y2,thickness

        # Send a command with UTF-8 (if printer supports it and CODEPAGE is set)
        # First set CODEPAGE via send_command if necessary
        # printer.send_command("CODEPAGE UTF-8")
        # Then use send_command_utf8 for the text command
        # Note: The TEXT command structure might vary. Consult TSPL manual.
        # Example using KAIU.TTF (assuming it's available or printer maps it)
        printer.send_command_utf8('TEXT 50,500,"KAIU.TTF",0,12,12,"測試中文 UTF-8 Text"')

        # 4. Execute the print command
        printer.print_label(quantity="1", copies="1")

        logging.info("Print job sent to the printer.")

    # The 'with' block automatically calls printer.close_port() here,
    # even if errors occurred inside the block.
    logging.info("Port closed via context manager.")

except FileNotFoundError as e:
    logging.error(f"Initialization failed: {e}")
    print(f"Error: {e}. Please ensure tsclibnet.dll is in the correct location.")
except ConnectionError as e:
    logging.error(f"Connection Error: {e}")
    print("Error: Could not connect to or communicate with the printer. Check connection and power.")
except TSCError as e:
    logging.error(f"A TSC Printer specific error occurred: {e}")
    print(f"Printer Error: {e}. Check printer status (paper, ribbon, etc.) and commands.")
except Exception as e:
    # Catch any other unexpected errors during the process
    logging.error(f"An unexpected error occurred: {e}", exc_info=True)  # Log traceback
    print(f"An unexpected error happened: {e}")

logging.info("\n--- TSC Printer Module Test Finished ---")

# Note: This script assumes the 'tsclibnet.dll' is present in the same directory
# or provided via the `dll_path` argument.
# Ensure the printer is connected via USB and powered on before running.
