import time
import tkinter as tk
from tkinter import ttk


class BACnetGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("BACnet Device Discovery")
        self.root.geometry("800x600")

        self.bacnet_client = None

        # self.style = ttk.Style()
        # self.style.theme_use('clam')

        self.setup_gui()

    def setup_gui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        title_label = ttk.Label(
            main_frame, text="BACnet Device Discovery", font=("Ariel", 14, "bold")
        )
        title_label.pack(pady=(0, 10))

        # Discovery button
        self._create_control_buttons(main_frame)
        # self.discover_btn = ttk.Button(main_frame, text="Discover Devices",
        #                                 command=self.discover_devices)
        # self.discover_btn.pack(pady=(0, 20))

        # notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self._create_devices_tab()
        self._create_points_tab()
        self._create_log_area(main_frame)

    def _create_control_buttons(self, parent):
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, pady=(0, 10))

        self.discover_btn = ttk.Button(
            button_frame, text="Discover Devices", command=self.discover_devices
        )
        self.discover_btn.pack(side=tk.LEFT, padx=(0, 10))

        # self.read_points_btn = ttk.Button(
        #     button_frame,
        #     text="Read Points from Selected",
        #     command=self.read_selected_points)

        self.read_points_btn = ttk.Button(
            button_frame,
            text="Read Points from Selected",
            command=self.discover_devices,
        )
        self.read_points_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.clear_btn = ttk.Button(
            button_frame, text="Clear All", command=self.clear_all_data
        )
        self.clear_btn.pack(side=tk.LEFT)

    def _create_devices_tab(self):
        self.devices_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.devices_frame, text="Devices")

        ttk.Label(self.devices_frame, text="Discovered Devices:").pack(anchor=tk.W)
        self.device_listbox = tk.Listbox(self.devices_frame, height=12)
        self.device_listbox.pack(fill=tk.BOTH, expand=True, pady=(5, 10))

    def _create_points_tab(self):
        self.points_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.points_frame, text="Points")

        ttk.Label(self.points_frame, text="Points in Selected Device:").pack(
            anchor=tk.W
        )

        columns = ("Type", "Instance", "Identifier")
        self.points_tree = ttk.Treeview(
            self.points_frame, columns=columns, show="headings", height=15
        )
        self.points_tree.heading("Type", text="Object Type")
        self.points_tree.heading("Instance", text="Instance")
        self.points_tree.heading("Identifier", text="Full Identifier")

        self.points_tree.column("Type", width=150)
        self.points_tree.column("Instance", width=100)
        self.points_tree.column("Identifier", width=200)

        scrollbar = ttk.Scrollbar(
            self.points_frame, orient=tk.VERTICAL, command=self.points_tree.yview
        )
        self.points_tree.configure(yscrollcommand=scrollbar.set)

        self.points_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=(5, 10))
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=(5, 10))

    def _create_log_area(self, parent):
        log_label = ttk.Label(parent, text="Activity Log:")
        log_label.pack(anchor=tk.W)

        self.log_text = tk.Text(parent, height=8)
        self.log_text.pack(fill=tk.X, pady=(5, 0))

    def set_bacnet_client(self, bacnet_client):
        self.bacnet_client = bacnet_client

    def discover_devices(self):
        if self.bacnet_client:
            self.log_message("Sending WhoIs broadcast...")
            self.bacnet_client.send_whois()

            self.root.after(3000, self.update_device_list)

    def update_device_list(self):

        self.device_listbox.delete(0, tk.END)

        if self.bacnet_client:
            devices = self.bacnet_client.get_discovered_devices()

            for device_id, info in devices.items():
                points_status = (
                    "x Points read"
                    if info.get("points_read", False)
                    else "o Points not read"
                )
                device_text = f"""Device {device_id}: {info['address']} 
                (Vendor: {info['vendor_id']} - {points_status})"""
                self.device_listbox.insert(tk.END, device_text)

            self.log_message(f"Found {len(devices)} devices(s)")

    def clear_all_data(self):
        # clear_devices()
        # self.update_device_list()
        # self.update_points_display(None)
        # self.log_message("All data cleared.")
        print(f"clear")

    def gui_update_callback(self):
        devices = (
            self.bacnet_client.get_discovered_devices() if self.bacnet_client else {}
        )
        print(f"GUI callback: {len(devices)} devices found")

    def log_message(self, message):
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)

    def run(self):
        self.root.mainloop()
