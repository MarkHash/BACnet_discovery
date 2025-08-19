import time
import traceback
from datetime import datetime

from bacpypes.apdu import ReadPropertyRequest, WhoIsRequest
from bacpypes.app import BIPSimpleApplication
from bacpypes.constructeddata import ArrayOf
from bacpypes.debugging import ModuleLogger, bacpypes_debugging
from bacpypes.iocb import IOCB
from bacpypes.pdu import Address, GlobalBroadcast
from bacpypes.primitivedata import ObjectIdentifier

_debug = 0
_log = ModuleLogger(globals())
discovered_devices = {}


@bacpypes_debugging
class BACnetClient(BIPSimpleApplication):
    def __init__(self, gui_update_callback, *args):
        if _debug:
            BACnetClient._debug("__init__%r", args)
        BIPSimpleApplication.__init__(self, *args)
        self.gui_update_callback = gui_update_callback

    def do_IAmRequest(self, apdu):
        if _debug:
            BACnetClient._debug("do_IAmRequest %r", apdu)

        try:
            print(f"device discovered: {apdu.iAmDeviceIdentifier}")

            device_identifier = apdu.iAmDeviceIdentifier
            vendor_id = apdu.vendorID
            device_id = device_identifier[1]

            device_info = {
                "device_id": device_id,
                "address": str(apdu.pduSource),
                "vendor_id": vendor_id,
                "last_seen": time.time(),
                "discovery_time": datetime.now().strftime("%H:%M:%S"),
                "points_read": False,
            }

            discovered_devices[device_id] = device_info
            print(
                f"Discovered device: ID={device_info['device_id']}, "
                f"""Address={device_info['address']},
                VendorID={device_info['vendor_id']},
                discovery_time: {device_info['discovery_time']}"""
            )
            self.read_device_objects(device_id)

            if self.gui_update_callback:
                self.gui_update_callback()

        except Exception as e:
            print(f"Error in do_IamRequest: {e}")

    def process_read_response(self, iocb):
        if _debug:
            BACnetClient._debug("do_ReadPropertyACK %r", iocb)

        try:
            if iocb.ioResponse:
                apdu = iocb.ioResponse
                device_address = str(apdu.pduSource)
                device_id = None

                for dev_id, dev_info in discovered_devices.items():
                    if dev_info["address"] == device_address:
                        device_id = dev_id
                        break

                if device_id is None:
                    print(
                        f"""ReadProperty response from unknown device:
                         {device_address}"""
                    )
                    return

                if (
                    apdu.objectIdentifier[0] == "device"
                    and apdu.propertyIdentifier == "objectList"
                ):
                    # object_list = apdu.propertyValue.cast_out(Array)
                    print(f"Processing object list for device {device_id}")
                    print(f"Property value type: {type(apdu.propertyValue)}")
                    points = []

                    property_value = apdu.propertyValue
                    if property_value.__class__.__name__ == "Any":
                        object_list = property_value.cast_out(ArrayOf(ObjectIdentifier))
                        print(f"Cast successful, type: {type(object_list)}")
                    else:
                        object_list = property_value
                        print(
                            f"using property value directly, type: {type(object_list)}"
                        )

                    for i, obj_item in enumerate(object_list):
                        if obj_item is None:
                            continue

                        print(
                            f"Processing item {i}: {obj_item} (type:{type(obj_item)})"
                        )

                        obj_type_name = str(obj_item[0])
                        obj_instance_num = int(obj_item[1])

                        if obj_type_name and obj_instance_num is not None:
                            points.append(
                                {
                                    "type": obj_type_name,
                                    "instance": obj_instance_num,
                                    "identifier": f"{obj_type_name}:{obj_instance_num}",
                                }
                            )

                    print(f"---points info for {device_id}")
                    for point in points:
                        print(f"identifier: {point['identifier']}")
                    print("-------")

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

        if _debug:
            BACnetClient._debug("Send WhoIs request")

        try:
            request = WhoIsRequest()
            request.pduDestination = GlobalBroadcast()

            # deferred(self.request, request)
            self.request(request)
            # print(f"Sent WhoIs broadcast")

        except Exception as e:
            print(f"Error sending WhoIs: {e}")

    def read_device_objects(self, device_id):
        if _debug:
            BACnetClient._debug("read_device_objeccts %r", device_id)

        try:
            if device_id not in discovered_devices:
                print(f"Device {device_id} not found")
                return

            device_info = discovered_devices[device_id]
            device_address = Address(device_info["address"])

            request = ReadPropertyRequest(
                objectIdentifier=("device", device_id), propertyIdentifier="objectList"
            )
            request.pduDestination = device_address

            iocb = IOCB(request)

            self.request_io(iocb)
            iocb.add_callback(self.process_read_response)
            print(f"Reading object list from device {device_id}")

        except Exception as e:
            print(f"Error reading device objects: {e}")
            traceback.print_exc()

    def get_discovered_devices(self):
        return discovered_devices.copy()
