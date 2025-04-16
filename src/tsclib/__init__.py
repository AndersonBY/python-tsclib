import os
import sys
import time
import types
import logging
from pathlib import Path
from typing import TypedDict

# Setup basic logging
log_level = os.getenv("TSCLIB_LOG_LEVEL", "INFO")
logging.basicConfig(level=log_level, format="%(asctime)s - %(levelname)s - %(message)s")

# --- Configuration ---
# Attempt to load pythonnet
try:
    # 首先导入pythonnet并显式加载
    from pythonnet import load

    # 加载.NET运行时
    load()

    # 导入clr模块
    import clr

    logging.debug("pythonnet loaded successfully.")
except ImportError as e:
    logging.error(f"ERROR: pythonnet library not found: {e}")
    logging.error("Please install it: pip install pythonnet")
    sys.exit(1)
except Exception as e:
    logging.error(f"ERROR: Failed to initialize pythonnet or CLR: {e}")
    logging.error("Ensure .NET Framework or .NET Core/5+ is installed and compatible.")
    sys.exit(1)


# --- Custom Exception ---
class TSCError(Exception):
    """Custom exception for TSC printer related errors."""

    pass


# --- Constants (based on documentation and common usage) ---
class SensorType:
    GAP = "0"
    BLACK_MARK = "1"


class BarcodeReadable:
    NO = "0"
    YES = "1"


class Rotation:
    DEG_0 = "0"
    DEG_90 = "90"
    DEG_180 = "180"
    DEG_270 = "270"


class PrinterDeviceInfo(TypedDict):
    device_path: str
    friendly_name: str
    description: str
    manufacturer: str
    vid: str
    pid: str
    index: str
    hardware_id: str
    compatible_ids: str
    device_class: str
    class_guid: str
    driver: str
    service: str
    location: str
    physical_device_name: str
    bus_number: str
    enumerator_name: str


# --- TSC Printer Class ---
class TSCPrinter:
    """
    A Python wrapper for the TSCSDK.node_usb class in tsclibnet.dll.

    Provides methods to control a TSC printer connected via USB.
    """

    _tsc_instance = None
    _TSCSDK = None
    _dll_path = None

    def __init__(self, dll_path: str | Path | None = None):
        """
        Initializes the TSCPrinter wrapper.

        Loads the tsclibnet.dll and prepares the TSCSDK.node_usb instance.

        Args:
            dll_path: Path to the tsclibnet.dll file. If None, it assumes
                      the DLL is in the same directory as this script.

        Raises:
            FileNotFoundError: If the DLL file cannot be found.
            ImportError: If the TSCSDK namespace cannot be imported from the DLL.
            RuntimeError: If the TSCSDK.node_usb instance cannot be created.
            TSCError: For other initialization errors.
        """
        if TSCPrinter._tsc_instance:
            logging.warning("TSCPrinter instance already exists. Reusing existing instance.")
            self._tsc_instance = TSCPrinter._tsc_instance  # Reuse existing instance
            self._TSCSDK = TSCPrinter._TSCSDK
            self._dll_path = TSCPrinter._dll_path
            return

        if dll_path is None:
            # Default to DLL in the same directory as this module
            self._dll_path = Path(__file__).parent / "tsclibnet.dll"
        else:
            self._dll_path = Path(dll_path)

        if not self._dll_path.exists():
            raise FileNotFoundError(f"TSC DLL not found at: {self._dll_path}")

        logging.debug(f"Loading TSC DLL from: {self._dll_path}")
        try:
            # Add reference to the DLL (use name without extension)
            logging.debug(f"Adding reference to: {str(self._dll_path.resolve().with_suffix(''))}")
            clr.AddReference(str(self._dll_path.resolve().with_suffix("")))  # type: ignore

            # Import the namespace
            import TSCSDK  # type: ignore

            TSCPrinter._TSCSDK = TSCSDK  # Store namespace at class level

            # Create the usb instance (must be instance, not static class)
            TSCPrinter._tsc_instance = self._TSCSDK.node_usb()  # type: ignore
            self._tsc_instance = TSCPrinter._tsc_instance  # Assign to instance variable too
            TSCPrinter._dll_path = self._dll_path  # Store path at class level

            logging.debug("tsclibnet.dll loaded and TSCSDK.node_usb instance created successfully.")

            # Optional: List available methods for debugging
            logging.debug("Available methods in tsc_instance:")
            for method_name in dir(self._tsc_instance):
                if not method_name.startswith("_"):
                    logging.debug(f"- {method_name}")
        except ImportError:
            logging.error(f"Failed to import TSCSDK namespace from '{self._dll_path.name}'.")
            logging.error("Ensure the DLL is a valid .NET assembly and pythonnet is working.")
            TSCPrinter._tsc_instance = None
            raise
        except AttributeError:
            logging.error("Could not find 'usb' class within the TSCSDK namespace.")
            logging.error("The DLL structure might be different than expected.")
            TSCPrinter._tsc_instance = None
            raise RuntimeError("Failed to find usb class in TSCSDK.")
        except Exception as e:
            logging.error(f"An unexpected error occurred during DLL loading: {e}")
            logging.error("Check .NET installation, DLL compatibility (32/64 bit), and pythonnet setup.")
            TSCPrinter._tsc_instance = None
            raise TSCError(f"Failed to initialize TSC printer interface: {e}")

    def _execute_command(self, method_name: str, *args):
        """Helper method to execute a command on the TSC instance and handle Task results."""
        if not self._tsc_instance:
            raise ConnectionError("TSC USB interface is not initialized.")

        try:
            method = getattr(self._tsc_instance, method_name)
            logging.debug(f"Executing: {method_name} with args: {args}")

            # Most methods seem to return Task<System.Object>
            task = method(*args)

            # Check if it returned a Task (as expected for async .NET methods)
            # Check type name string to avoid direct dependency if possible, or use isinstance cautiously
            if task is not None and "Task" in str(type(task)):
                # Wait for the task to complete and get the result
                result = task.Result  # This blocks until the async operation completes
                logging.debug(f"{method_name} task completed. Result: {result}")
                # Often, the result might be null or a status code string/object.
                # Success is often indicated by lack of exceptions.
                # We might want to check specific results if the API is better documented.
                return result
            else:
                # Handle methods that might not return a Task (e.g., sendcommand_byte returns void)
                logging.debug(f"{method_name} executed (non-Task or None return). Return value: {task}")
                return task  # Return the direct result if not a Task

        except AttributeError:
            logging.error(f"Method '{method_name}' not found in TSCSDK.node_usb instance.")
            raise
        except Exception as e:
            logging.error(f"Error executing TSC command '{method_name}': {e}")
            # Attempt to get more details if it's a .NET exception
            if hasattr(e, "ToString"):  # Common for .NET exceptions proxied by pythonnet
                logging.error(f"Detailed .NET Error: {e.ToString()}")  # type: ignore
            import traceback

            logging.error(f"Traceback: {traceback.format_exc()}")
            raise TSCError(f"Failed during printer operation '{method_name}': {e}")

    # --- Core Printer Operations ---

    def list_printers(self) -> list[PrinterDeviceInfo]:
        """
        Enumerates connected TSC USB printers (VID 0x1203).

        Returns:
            A list of printer model names found. The index in this list
            can be used with open_port_by_index. Returns empty list on failure.
        """
        printer_list_net = self._execute_command("listprinters")
        available_printers = []
        if printer_list_net and printer_list_net.Count > 0:
            for i in range(printer_list_net.Count):
                net_device_info = printer_list_net[i]
                py_device_info = {
                    "device_path": net_device_info["DevicePath"],
                    "friendly_name": net_device_info["FriendlyName"],
                    "description": net_device_info["DeviceDesc"],
                    "manufacturer": net_device_info["Manufacturer"],
                    "vid": net_device_info["VID"],
                    "pid": net_device_info["PID"],
                    "index": net_device_info["Index"],
                    "hardware_id": net_device_info["HardwareID"],
                    "compatible_ids": net_device_info["CompatibleIDs"],
                    "device_class": net_device_info["Class"],
                    "class_guid": net_device_info["ClassGuid"],
                    "driver": net_device_info["Driver"],
                    "service": net_device_info["Service"],
                    "location": net_device_info["Location"],
                    "physical_device_name": net_device_info["PhysicalDeviceName"],
                    "bus_number": net_device_info["BusNumber"],
                    "enumerator_name": net_device_info["EnumeratorName"],
                }
                available_printers.append(py_device_info)

        return available_printers

    def open_port(self, port_index: int = 0) -> bool:
        """
        Opens the communication port to the printer.

        Args:
            port_index: The index of the port.
                       - For USB, typically 0 (default) lets the driver find it.
                       - Can also be driver name (e.g., "TSC TTP-247") or LPT port ("LPT1").
                       Refer to tsclib documentation for specifics.

        Returns:
            The result from the DLL's openport method. Success often indicated by
            lack of exceptions rather than a specific return value.
        """
        logging.debug(f"Opening printer port '{port_index if port_index else 'USB (default)'}'...")
        result = self._execute_command("openport", port_index)
        logging.debug(f"openport result: {result}")
        # Add a small delay after opening port, sometimes helpful
        time.sleep(0.1)
        return result

    def close_port(self) -> object:
        """
        Closes the communication port to the printer.

        Returns:
            The result from the DLL's closeport method.
        """
        logging.debug("Closing printer port...")
        # Pass object (empty string works based on user code)
        result = self._execute_command("closeport", "")
        logging.debug(f"closeport result: {result}")
        return result

    def get_status(self, delay_ms: int = 100) -> str:
        """
        Retrieves the printer status as a string code.

        Args:
            delay_ms: Delay in milliseconds to wait for status.

        Returns:
            A string representing the printer status (e.g., "00" for ready).
            Refer to TSPL manual for status code meanings.
        """
        logging.debug("Querying printer status...")
        result = self._execute_command("printerstatus_string", delay_ms)
        status = str(result)  # Ensure it's a string
        logging.debug(f"Printer status code: {status}")
        return status

    def get_about_info(self) -> str:
        """
        Retrieves 'about' information from the DLL (e.g., version).

        Returns:
            A string containing the about information.
        """
        logging.debug("Querying DLL about info...")
        # Pass object (empty string works based on user code)
        result = self._execute_command("about", "")
        about_info = str(result)
        logging.debug(f"DLL About info: {about_info}")
        return about_info

    def setup_label(
        self, width_mm: str, height_mm: str, speed: str, density: str, sensor_type: str, gap_mm: str, offset_mm: str
    ) -> object:
        """
        Configures the label dimensions, print speed, density, and sensor settings.

        Args:
            width_mm: Label width in mm (string).
            height_mm: Label height in mm (string).
            speed: Print speed (string, e.g., "4.0"). See TSPL manual for options.
            density: Print density (string, "0"-"15").
            sensor_type: Sensor type (string, use SensorType constants, e.g., SensorType.GAP).
            gap_mm: Vertical gap/black mark height in mm (string).
            offset_mm: Vertical gap/black mark offset in mm (string, usually "0").

        Returns:
            The result from the DLL's setup method.
        """
        logging.debug(
            f"Setting up label: {width_mm}x{height_mm}mm, Speed:{speed}, Density:{density}, Sensor:{sensor_type}"
        )
        setup_params = types.SimpleNamespace(
            width=width_mm,  # Parameter names likely inferred by the DLL
            height=height_mm,  # based on order or internal mapping. Let's try
            speed=speed,  # names that seem logical, falling back to order.
            density=density,  # NOTE: The C API takes positional args. The .NET API
            sensor=sensor_type,  #       might take an object OR positional. Using
            vertical=gap_mm,  #       SimpleNamespace is a good bet for object input.
            offset=offset_mm,  #       ***If this fails, we might need positional args***
            #       like: self._execute_command("setup", width_mm, height_mm, ...)
        )
        # The reversed API shows `setup(object input)`. Passing a namespace worked for others.
        result = self._execute_command("setup", setup_params)
        logging.debug(f"setup result: {result}")
        return result

    def clear_buffer(self) -> object:
        """
        Clears the printer's command buffer. Should be called before sending new label data.

        Returns:
            The result from the DLL's clearbuffer method.
        """
        logging.debug("Clearing printer buffer...")
        # Pass object (empty string works based on user code)
        result = self._execute_command("clearbuffer", "")
        logging.debug(f"clearbuffer result: {result}")
        return result

    def print_label(self, quantity: str = "1", copies: str = "1") -> object:
        """
        Executes the print command for the data currently in the buffer.

        Args:
            quantity: Number of sets/labels to print (string).
            copies: Number of identical copies per set/label (string).

        Returns:
            The result from the DLL's printlabel method.
        """
        logging.debug(f"Sending print command: Quantity={quantity}, Copies={copies}")
        print_params = types.SimpleNamespace(
            quantity=quantity,
            copy=copies,  # Matches user's working code parameter name
        )
        result = self._execute_command("printlabel", print_params)
        logging.debug(f"printlabel result: {result}")
        return result

    # --- Sending Raw Commands ---

    def send_command(self, command: str) -> object:
        """
        Sends a raw TSPL/TSPL2 command string to the printer. Assumes default encoding.

        Args:
            command: The TSPL/TSPL2 command string.

        Returns:
            The result from the DLL's sendcommand method.
        """
        logging.debug(f"Sending command: {command}")
        result = self._execute_command("sendcommand", command)
        logging.debug(f"sendcommand result: {result}")
        return result

    def send_command_utf8(self, command: str) -> object:
        """
        Sends a raw TSPL/TSPL2 command string to the printer, encoded as UTF-8.
        Useful for commands containing international characters.

        Args:
            command: The TSPL/TSPL2 command string.

        Returns:
            The result from the DLL's sendcommand_utf8 method.
        """
        logging.debug(f"Sending UTF-8 command: {command}")
        result = self._execute_command("sendcommand_utf8", command)
        logging.debug(f"sendcommand_utf8 result: {result}")
        return result

    # --- Printing Elements ---

    def print_text_internal_font(
        self, x: str, y: str, font_type: str, rotation: str, x_mul: str, y_mul: str, text: str
    ) -> object:
        """
        Prints text using the printer's built-in fonts.

        Args:
            x: X coordinate (dots).
            y: Y coordinate (dots).
            font_type: Internal font identifier (string, e.g., "3"). See TSPL manual.
            rotation: Rotation angle (string, use Rotation constants).
            x_mul: Horizontal magnification (string, "1"-"8").
            y_mul: Vertical magnification (string, "1"-"8").
            text: The text content to print.

        Returns:
            The result from the DLL's printerfont method.
        """
        logging.debug(f"Printing internal font text at ({x},{y}): {text}")
        font_params = types.SimpleNamespace(
            x=x,
            y=y,
            fonttype=font_type,  # Matches user's working code
            rotation=rotation,
            xmul=x_mul,
            ymul=y_mul,
            text=text,
        )
        result = self._execute_command("printerfont", font_params)
        logging.debug(f"printerfont result: {result}")
        return result

    def print_barcode(
        self,
        x: str,
        y: str,
        barcode_type: str,
        height: str,
        readable: str,
        rotation: str,
        narrow_bar_mul: str,
        wide_bar_mul: str,
        code: str,
    ) -> object:
        """
        Prints a barcode using the printer's built-in barcode engine.

        Args:
            x: X coordinate (dots).
            y: Y coordinate (dots).
            barcode_type: Barcode type identifier (string, e.g., "128", "39"). See TSPL manual.
            height: Barcode height (dots).
            readable: Whether to print human-readable text (string, use BarcodeReadable constants).
            rotation: Rotation angle (string, use Rotation constants).
            narrow_bar_mul: Narrow bar width multiplier/ratio (string). See TSPL manual.
            wide_bar_mul: Wide bar width multiplier/ratio (string). See TSPL manual.
            code: The barcode data content.

        Returns:
            The result from the DLL's barcode method.
        """
        logging.debug(f"Printing barcode at ({x},{y}): Type={barcode_type}, Code={code}")
        barcode_params = types.SimpleNamespace(
            x=x,
            y=y,
            type=barcode_type,
            height=height,
            readable=readable,
            rotation=rotation,
            narrow=narrow_bar_mul,  # Matches user's working code
            wide=wide_bar_mul,  # Matches user's working code
            code=code,
        )
        result = self._execute_command("barcode", barcode_params)
        logging.debug(f"barcode result: {result}")
        return result

    def print_text_windows_font(
        self,
        x: int,
        y: int,
        font_height: int,
        rotation: int,
        font_style: int,
        font_underline: int,
        font_face_name: str,
        text: str,
    ) -> object:
        """
        Prints text using a TrueType font installed on the Windows system
        where this script is running.

        Args:
            x: X coordinate (dots).
            y: Y coordinate (dots).
            font_height: Font height (dots).
            rotation: Rotation angle (int: 0, 90, 180, 270).
            font_style: Font style (int: 0=Normal, 1=Italic, 2=Bold, 3=Bold Italic).
            font_underline: Underline (int: 0=No, 1=Yes).
            font_face_name: Name of the installed TTF font (e.g., "Arial", "Verdana").
            text: The text content to print.

        Returns:
            The result from the DLL's windowsfont method.
        """
        logging.debug(f"Printing Windows font '{font_face_name}' at ({x},{y}): {text}")
        windowsfont_params = types.SimpleNamespace(
            x=x,
            y=y,
            fontheight=font_height,  # Matches user's working code
            rotation=rotation,
            fontstyle=font_style,
            fontunderline=font_underline,
            szFaceName=font_face_name,  # Matches user's working code
            content=text,  # Matches user's working code
        )
        result = self._execute_command("windowsfont", windowsfont_params)
        logging.debug(f"windowsfont result: {result}")
        return result

    # --- Context Manager Support ---

    def __enter__(self):
        """Enters the runtime context related to this object."""
        self.open_port()  # Or specific port if needed: self.open_port("USB") etc.
        # Check status after opening? Optional.
        # status = self.get_status()
        # if status != "00": # Assuming "00" is ready
        #     logging.warning(f"Printer status after opening port is not ready: {status}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exits the runtime context, ensuring the port is closed."""
        try:
            self.close_port()
        except Exception as e:
            # Log error during close but don't suppress the original exception (if any)
            logging.error(f"Error closing printer port during exit: {e}")
        # Return False to propagate exceptions that occurred within the 'with' block
        return False


# --- Example Usage ---
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)  # More verbose logging for testing
    logging.debug("--- TSC Printer Module Test ---")

    # Assumes tsclibnet.dll is in the same directory as this script
    # If it's elsewhere, provide the full path:
    # DLL_LOCATION = r"C:\path\to\your\tsclibnet.dll"
    # printer = TSCPrinter(dll_path=DLL_LOCATION)

    try:
        printer = TSCPrinter()  # Uses default path finding

        # logging.debug("--- Getting DLL Info ---")
        # print(f"DLL About Info: {printer.get_about_info()}")

        logging.debug("\n--- Running Print Job via Context Manager ---")
        with printer:  # Automatically opens and closes the port
            logging.debug("Port opened via context manager.")

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

            logging.debug("Print job sent to the printer.")

        # The 'with' block automatically calls printer.close_port() here,
        # even if errors occurred inside the block.
        logging.debug("Port closed via context manager.")

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

    logging.debug("\n--- TSC Printer Module Test Finished ---")

# Note: This script assumes the 'tsclibnet.dll' is present in the same directory
# or provided via the `dll_path` argument.
# Ensure the printer is connected via USB and powered on before running.
