import sys
import time
import threading
import traceback
from datetime import datetime
from bacpypes.consolelogging import ConfigArgumentParser
from bacpypes.core import run, stop, deferred, enable_sleeping
from bacpypes.local.device import LocalDeviceObject

from bacnet_client import BACnetClient
from gui import BACnetGUI

def main():
    try:
        # -------------------------
        # BACnet setup
        # -------------------------
        args = ConfigArgumentParser(description=__doc__).parse_args()

        gui = BACnetGUI()

        this_device = LocalDeviceObject(
            objectName=args.ini.objectname,
            objectIdentifier=int(args.ini.objectidentifier),
            maxApduLengthAccepted=int(args.ini.maxapdulengthaccepted),
            segmentationSupported=args.ini.segmentationsupported,
            vendorIdentifier=int(args.ini.vendoridentifier),
        )
        print(f"Workstation info: {args}")

        # this_address = Address("192.168.1.5/24")  # Replace with your IP
        bacnet_client = BACnetClient(gui.gui_update_callback, this_device, args.ini.address)
        gui.set_bacnet_client(bacnet_client)

        def run_bacnet():
            enable_sleeping()
            run()

        bacnet_thread = threading.Thread(target=run_bacnet)
        bacnet_thread.daemon = True
        bacnet_thread.start()

        gui.run()
    
    except KeyboardInterrupt:
        print(f"\nShutting down...")
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
    finally:
        try:
            stop()
        except:
            pass

if __name__ == "__main__":
    main()