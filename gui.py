import time
import tkinter as tk
from tkinter import ttk

class BACnetGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("BACnet Device Discovery")
        self.root.geometry("900x600")

        self.bacnet_client = None

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
    
    def set_bacnet_client(self, bacnet_client):
        self.bacnet_client = bacnet_client

    def discover_devices(self):
        if self.bacnet_client:
            self.results_text.insert(tk.END, f"\n[{time.strftime('%H:%M:%S')}] Sending WhoIS broadcast...\n")
            self.results_text.see(tk.END)
            self.bacnet_client.send_whois()

            self.root.after(3000, self.update_results)

    def update_results(self):
        devices = self.bacnet_client.get_discovered_devices() if self.bacnet_client else {}

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
        devices = self.bacnet_client.get_discovered_devices() if self.bacnet_client else {}
        print(f"GUI callback: {len(devices)} devices found")

    def run(self):
        self.root.mainloop()