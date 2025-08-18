import sys
import time
import threading
import traceback
from datetime import datetime
from bacpypes.core import run, stop, deferred, enable_sleeping
from bacpypes.pdu import Address, GlobalBroadcast
from bacpypes.app import BIPSimpleApplication
from bacpypes.local.device import LocalDeviceObject
from bacpypes.apdu import WhoIsRequest, IAmRequest, ReadPropertyRequest
from bacpypes.consolelogging import ConfigArgumentParser
from bacpypes.debugging import bacpypes_debugging, ModuleLogger
from bacpypes.iocb import IOCB
from bacpypes.constructeddata import Array

import tkinter as tk
from tkinter import ttk, scrolledtext

_debug = 0
_log = ModuleLogger(globals())
discovered_devices = {}
device_points = {}

class BACnetGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("BACnet Device Discovery")
        self.root.geometry("900x600")

        self.bacnet_app = None

        # self.style = ttk.Style()
        # self.style.theme_use('clam')

        self.setup_gui()
        # self.update_gui_periodically()

    def setup_gui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        title_label = ttk.Label(main_frame, text="BACnet Device Discovery",
                                font=('Ariel', 14, 'bold'))
        title_label.pack(pady=(0, 20))

        # Discovery button
        self.discover_btn = ttk.Button(main_frame, text="Discover Devices",
                                        command=self.discover_devices)
        self.discover_btn.pack(pady=(0, 20))

        # Results area
        results_label = ttk.Label(main_frame, text="Discovered Devices:")
        results_label.pack(anchor=tk.W)

        self.results_text = tk.Text(main_frame, height=15, width=60)
        self.results_text.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

        self.results_text.insert(tk.END, "Click 'Discover Devices' to start scanning...\n")


        #Device list frame
        # list_frame = ttk.LabelFrame(main_frame, text="Discovered Devices", padding="5")
        # list_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S),
        #                 padx=(0, 10))
        # list_frame.columnconfigure(0, weight=1)
        # list_frame.rowconfigure(0, weight=1)
    
    def set_bacnet_app(self, bacnet_app):
        self.bacnet_app = bacnet_app

    def discover_devices(self):
        if self.bacnet_app:
            self.results_text.insert(tk.END, f"\n[{time.strftime('%H:%M:%S')}] Sending WhoIS broadcast...\n")
            self.results_text.see(tk.END)
            self.bacnet_app.send_whois()

            self.root.after(3000, self.update_results)

    def update_results(self):
        devices = self.bacnet_app.get_discovered_devices() if self.bacnet_app else {}

        self.results_text.insert(tk.END, f"\n--- Found {len(devices)} device(s) ---\n")

        if devices:
            for device_id, info in devices.items():
                last_seen = time.strftime('%H:%M:%S', time.localtime(info['last_seen']))
                self.results_text.insert(tk.END, f"Device {device_id}: {info['address']} (Vendor: {info['vendor_id']}) last seen: {last_seen}\n")
                # print(f"Device {device_id}: {info['address']} (last seen: {last_seen})")
        else:
            self.results_text.insert(tk.END, "No devices found.\n")

        self.results_text.insert(tk.END, "---\n")
        self.results_text.see(tk.END)

    def gui_update_callback(self):
        devices = self.bacnet_app.get_discovered_devices() if self.bacnet_app else {}
        print(f"GUI callback: {len(devices)} devices found")

    def run(self):
        self.root.mainloop()

@bacpypes_debugging
class WhoIsIAmApplication(BIPSimpleApplication):
    def __init__(self, gui_update_callback, *args):
        if _debug: WhoIsIAmApplication._debug("__init__%r", args)
        BIPSimpleApplication.__init__(self, *args)
        self.gui_update_callback = gui_update_callback

    def do_IAmRequest(self, apdu):
        if _debug: WhoIsIAmApplication._debug("do_IAmRequest %r", apdu)

        try:
            if not self.request:
                if _debug: WhoIsIAmApplication._debug("no pending request")

            elif isinstance(apdu, IAmRequest):
                print(f"device discovered: {apdu.iAmDeviceIdentifier}")

                device_id = apdu.iAmDeviceIdentifier
                max_apdu_length = apdu.maxAPDULengthAccepted
                segmentation_supported = apdu.segmentationSupported
                vendor_id = apdu.vendorID

                device_info = {
                    'device_id': device_id[1],
                    'address': str(apdu.pduSource),
                    'max_apdu_length': max_apdu_length,
                    'segmentation_supported': segmentation_supported,
                    'vendor_id': vendor_id,
                    'last_seen': time.time()
                }

                discovered_devices[device_id[1]] = device_info
                print(f"Discovered device: ID={device_id[1]}, "
                        f"Address={apdu.pduSource}, VendorID={vendor_id})")
                self.read_device_objects(device_id[1])
                
            if self.gui_update_callback: self.gui_update_callback()
        
        except Exception as e:
            print(f"Error in do_IamRequest: {e}")

    def read_device_objects(self, device_id):
        if _debug: WhoIsIAmApplication._debug("read_device_objeccts %r", device_id)

        try:
            if device_id not in discovered_devices:
                print(f"Device {device_id} not found")
                return
            
            device_info = discovered_devices[device_id]
            device_address = Address(device_info["address"])

            request = ReadPropertyRequest(
                objectIdentifier=('device', device_id),
                propertyIdentifier='objectList'
            )
            request.pduDestination = device_address

            iocb = IOCB(request)

            self.request_io(iocb)
            iocb.add_callback(self.do_ReadPropertyACK)
            print(f"Reading object list from device {device_id}")

        except Exception as e:
            print(f"Error reading device objects: {e}")
            traceback.print_exc()

    def do_ReadPropertyACK(self, iocb):
        if _debug: WhoIsIAmApplication._debug("do_ReadPropertyACK %r", apdu)

        try:
            if iocb.ioResponse:
                apdu = iocb.ioResponse
                device_address = str(apdu.pduSource)
                device_id = None

                for dev_id, dev_info in discovered_devices.items():
                    if dev_info['address'] == device_address:
                        device_id = dev_id
                        break

                if device_id is None:
                    print(f"ReadProperty response from unknown device: {device_address}")
                    return

                if (apdu.objectIdentifier[0] == 'device' and apdu.propertyIdentifier == 'objectList'):
                    # object_list = apdu.propertyValue.cast_out(Array)
                    print(f"Processing object list for device {device_id}")
                    print(f"Property value type: {type(apdu.propertyValue)}")
                    points = []


                    from bacpypes.constructeddata import ArrayOf
                    from bacpypes.primitivedata import ObjectIdentifier

                    property_value = apdu.propertyValue
                    if property_value.__class__.__name__ == 'Any':
                        object_list = property_value.cast_out(ArrayOf(ObjectIdentifier))
                        print(f"Cast successful, type: {type(object_list)}")
                    else:
                        object_list = property_value
                        print(f"using property value directly, type: {type(object_list)}")

                    for i, obj_item in enumerate(object_list):
                        if obj_item is None:
                            continue

                        try: 
                            print(f"Processing item {i}: {obj_item} (type:{type(obj_item)})")

                            obj_type_name = str(obj_item[0])
                            obj_instance_num = int(obj_item[1])

                            if obj_type_name and obj_instance_num is not None:
                                points.append({
                                    'type': obj_type_name,
                                    'instance': obj_instance_num,
                                    'identifier': f"{obj_type_name}:{obj_instance_num}"
                                })
                        except Exception as e:
                            print(f"  Error parsing object {i}: {e}")
                            continue

                    print(f"---points info for {device_id}")
                    for point in points:
                        print(f"identifier: {point['identifier']}")
                    print(f"-------")
                       

                    # if self.gui_update_callback:
                    #     self.gui_update_callback('points_found', {
                    #     'device_id': device_id,
                    #     'points': points
                    # })

        except Exception as e:
            print(f"Error processing ReadProperty response: {e}")
            traceback.print_exc()

    def send_whois(self):
            """Send a WhoIs erquest as a global broadast"""
            
            if _debug: WhoIsIAmApplication._debug("Send WhoIs request")

            try:
                request = WhoIsRequest()
                request.pduDestination = GlobalBroadcast()

                # deferred(self.request, request)
                self.request(request)
                # print(f"Sent WhoIs broadcast")

            except Exception as e:
                print(f"Error sending WhoIS: {e}")

    def get_discovered_devices(self):
        return discovered_devices.copy()

    # def stop_timers(self):
    #     self.running = False
    #     if self.discovery_timer: self.discovery_timer.cancel()
    #     if self.status_timer: self.status_timercancel()

def main():
    try:
        # -------------------------
        # BACnet setup
        # -------------------------
        args = ConfigArgumentParser(description=__doc__).parse_args()
        if _debug: _log.debug("initialization")
        if _debug: _log.debug("    - args: %r", args)

        gui = BACnetGUI()

        this_device = LocalDeviceObject(
            objectName=args.ini.objectname,
            objectIdentifier=int(args.ini.objectidentifier),
            maxApduLengthAccepted=int(args.ini.maxapdulengthaccepted),
            segmentationSupported=args.ini.segmentationsupported,
            vendorIdentifier=int(args.ini.vendoridentifier),
        )
        print(f"Workstation info: {args}")

        if _debug: _log.debug("   - device object: %r", this_device)

        # this_address = Address("192.168.1.5/24")  # Replace with your IP
        bacnet_app = WhoIsIAmApplication(gui.gui_update_callback, this_device, args.ini.address)

        #Initial discovery
        # this_app.send_whois()
        gui.set_bacnet_app(bacnet_app)

        if _debug: _log.debug("running")

        import threading
        def run_bacnet():
            enable_sleeping()
            run()

        bacnet_thread = threading.Thread(target=run_bacnet)
        bacnet_thread.daemon = True
        bacnet_thread.start()

        gui.run()
    
    # except KeyboardInterrupt:
    #     print(f"\nShutting down...")
    #     this_app.stop_timers()
    #     stop()
    except Exception as e:
        # if 'this_app' in locals(): this_app.stop_timers()
        # stop()
        print(f"Error: {e}")
        traceback
        traceback.print_exc()
    finally:
        try:
            stop()
        except:
            pass

if __name__ == "__main__":
    main()