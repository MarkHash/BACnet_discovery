import sys
import time
import threading
from bacpypes.core import run, stop, deferred, enable_sleeping
from bacpypes.pdu import Address, GlobalBroadcast
from bacpypes.app import BIPSimpleApplication
from bacpypes.local.device import LocalDeviceObject
from bacpypes.apdu import WhoIsRequest, IAmRequest
from bacpypes.consolelogging import ConfigArgumentParser
from bacpypes.debugging import bacpypes_debugging, ModuleLogger

_debug = 0
_log = ModuleLogger(globals())
discovered_devices = {}
DISCOVERY_THREADING_TIME = 30.0
REPORTING_THREADING_TIME = 60.0

@bacpypes_debugging
class ThreadWhoIsIAmApplication(BIPSimpleApplication):
    def __init__(self, *args):
        if _debug: ThreadWhoIsIAmApplication._debug("__init__%r", args)
        BIPSimpleApplication.__init__(self, *args)

        self.discovery_timer = None
        self.status_timer = None
        self.running = True

        self.start_periodic_discovery()
        self.start_status_reporting()

    def do_IAmRequest(self, apdu):
        if _debug: ThreadWhoIsIAmApplication._debug("do_IAmRequest %r", apdu)

        if not self.request:
            if _debug: WhoIsIAmApplication._debug("  no pending request")

        elif isinstance(apdu, IAmRequest):
            print(f"device discovered: {apdu.iAmDeviceIdentifier}")

            device_identifier = apdu.iAmDeviceIdentifier
            max_apdu_length = apdu.maxAPDULengthAccepted
            segmentation_supported = apdu.segmentationSupported
            vendor_id = apdu.vendorID

            
            device_info = {
                'device_id': device_identifier[1],
                'address': str(apdu.pduSource),
                'max_apdu_length': max_apdu_length,
                'segmentation_supported': segmentation_supported,
                'vendor_id': vendor_id,
                'last_seen': time.time()
            }

            discovered_devices[device_identifier[1]] = device_info
            print(f"Discovered device: ID={device_identifier[1]}, "
                    f"Address={apdu.pduSource}, VendorID={vendor_id})")

    def start_periodic_discovery(self):
        
        if _debug: ThreadWhoIsIAmApplication._debug("start_periodic_discovery")
        self.schedule_next_discovery()

    def schedule_next_discovery(self):
        # print(f"schedule_next_discovery")
        if self.running:
            # print(f"schedule_next_discovery")
            self.discovery_timer = threading.Timer(DISCOVERY_THREADING_TIME, self.send_whois_and_reschedule)
            self.discovery_timer.daemon = True
            self.discovery_timer.start()

    def send_whois_and_reschedule(self):
        self.send_whois()
        self.schedule_next_discovery()

    def send_whois(self):
            """Send a WhoIs erquest as a global broadast"""
            
            if _debug: ThreadWhoIsIAmApplication._debug("Send WhoIs request")

            try:
                request = WhoIsRequest()
                request.pduDestination = GlobalBroadcast()

                deferred(self.request, request)
                # self.request(request)
                # print(f"Sent WhoIs broadcast")

            except Exception as error:
                print(f"exception: %r", {error})

    def start_status_reporting(self):
        self.schedule_next_status()
    
    def schedule_next_status(self):
        if self.running:
            self.status_timer = threading.Timer(REPORTING_THREADING_TIME, self.status_report_and_reschedule)
            self.status_timer.daemon = True
            self.status_timer.start()
    
    
    def status_report_and_reschedule(self):
        self.report_status()
        self.schedule_next_status()

    def report_status(self):
        devices = self.get_discovered_devices()
        print(f"\n Device discovery status ({len(devices)} devices found)")
        for device_id, info in devices.items():
            last_seen = time.strftime('%H:%M:%S', time.localtime(info['last_seen']))
            print(f"Device {device_id}: {info['address']} (last seen: {last_seen})")

        print("="*10)

    def get_discovered_devices(self):
        return discovered_devices.copy()

    def stop_timers(self):
        self.running = False
        if self.discovery_timer: self.discovery_timer.cancel()
        if self.status_timer: self.status_timercancel()

def main():
    try:
        # -------------------------
        # BACnet setup
        # -------------------------
        args = ConfigArgumentParser(description=__doc__).parse_args()
        if _debug: _log.debug("initialization")
        if _debug: _log.debug("    - args: %r", args)

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
        this_app = ThreadWhoIsIAmApplication(this_device, args.ini.address)

        #Initial discovery
        this_app.send_whois()

        if _debug: _log.debug("running")

        enable_sleeping()
        run()
    
    except KeyboardInterrupt:
        print(f"\nShutting down...")
        this_app.stop_timers()
        stop()
    except Exception as e:
        if 'this_app' in locals(): this_app.stop_timers()
        stop()

if __name__ == "__main__":
    main()