import tkinter as tk
from tkinter import ttk
from tkinter import filedialog, messagebox
import json
import os
from wgconfig import WGConfig
from pyroute2 import IPRoute, NetlinkError
import subprocess

class VPNApp:
    def __init__(self, root):
        self.conf_tunnel_btn()

        self.root = root
        self.root.title("Giga VPN")
        self.root.geometry("800x550")
        self.root.minsize(485, 365)

        self.tunnel_buttons = {}
        self.selected_tunnel = None

        self.tunnels = tk.Frame(root, pady=20, padx=10)
        self.tunnels.pack(side=tk.LEFT, fill=tk.BOTH, expand=False)

        self.canvas = tk.Canvas(self.tunnels, width=211, borderwidth=1, relief="solid", highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.tunnels, orient=tk.VERTICAL, command=self.canvas.yview)
        self.tunnels_frame = ttk.Frame(self.canvas, width=100)

        self.info_frame = tk.Frame(self.root, bd=1, relief="solid", padx=5, pady=5, bg="#f0f0f0")
        self.info_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=(20, 0), padx=(0, 10))

        self.canvas.create_window((0, 0), window=self.tunnels_frame, anchor="nw")
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.buttons = tk.Frame(self.root, pady=5, bg="#f0f0f0")
        self.buttons.pack(side=tk.BOTTOM, fill=tk.Y, expand=0, anchor="nw", pady=(0, 14))

        self.add_tunnel_btn = ttk.Button(self.buttons, text="add tunnel", command=self.add_tunnel)
        self.add_tunnel_btn.pack(side=tk.LEFT, fill=tk.X, padx=(0, 10))

        self.remove_tunnel_btn = ttk.Button(self.buttons, text="remove tunnel", command=self.remove_tunnel)
        self.remove_tunnel_btn.pack(side=tk.LEFT, fill=tk.X)

        self.tunnels_frame.bind("<Configure>", self.update_scrollbar)
        self.root.bind("<Configure>", self.update_scrollbar)

        self.load_tunnels()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def conf_tunnel_btn(self):
        btn_style = ttk.Style()
        btn_style.configure("TButton",
                            font=("Roboto", 9),
                            padding=(0, 0),
                            anchor="w",
                            highlightbackground="#000")

        btn_style.map("TButton",
                      background=[("active", "#ADD8E6"), ("focus", "#87CEEB"), ("pressed", "#87CEEB")],
                      relief=[("active", "solid"), ("focus", "solid"), ("pressed", "solid")],
                      bordercolor=[("active", "#ADD8E6"), ("focus", "#87CEEB"), ("pressed", "#87CEEB")],
                      borderwidth=[("active", 1), ("focus", 1), ("pressed", 1)])

    def _on_mouse_wheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def update_scrollbar(self, event=None):
        frame_height = self.tunnels_frame.winfo_reqheight()
        canvas_height = self.canvas.winfo_height()

        if frame_height < canvas_height:
            self.canvas.unbind_all("<MouseWheel>")
            self.tunnels_frame.unbind_all("<MouseWheel>")
            self.scrollbar.pack_forget()
        else:
            self.canvas.bind_all("<MouseWheel>", self._on_mouse_wheel)
            self.tunnels_frame.bind_all("<MouseWheel>", self._on_mouse_wheel)
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            self.canvas.configure(yscrollcommand=self.scrollbar.set)
            self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def add_tunnel_button(self, text, file_path=None):
        if len(text) > 29:
            messagebox.showwarning("Warning", "Invalid file name")
        else:
            tunnel_btn = ttk.Button(self.tunnels_frame, text=text, style="TButton", width=29, command=lambda btn=text: self.display_info(btn))
            tunnel_btn.pack(fill=tk.X, pady=0, padx=0)
            tunnel_btn.bind("<Button-1>", lambda event, btn=tunnel_btn: self.select_tunnel(btn))
            tunnel_btn.bind("<Button-2>", lambda btn=text: self.display_info(btn))
            self.tunnel_buttons[text] = (tunnel_btn, file_path)

    def select_tunnel(self, btn):
        self.selected_tunnel = btn
        for button, _ in self.tunnel_buttons.values():
            button.state(["!focus"])
        btn.state(["focus", "pressed"])

    def add_tunnel(self):
        file_path = filedialog.askopenfilename(title="Select Config File", filetypes=(("Config Files", "*.conf"),))
        if file_path:
            file_name = os.path.basename(file_path).rsplit('.', 1)[0]
            if file_name not in self.tunnel_buttons:
                self.add_tunnel_button(file_name, file_path)
            else:
                messagebox.showwarning("Warning", "Duplicate config file")

    def remove_tunnel(self):
        if self.selected_tunnel:
            button_text = self.selected_tunnel.cget("text")
            self.selected_tunnel.destroy()
            del self.tunnel_buttons[button_text]
            self.selected_tunnel = None
            self.display_info(button_text)
            self.save_tunnels()
        else:
            messagebox.showwarning("Warning", "No tunnel selected to remove")

    def display_info(self, button_text):
        for widget in self.info_frame.winfo_children():
            widget.destroy()
        if button_text in self.tunnel_buttons:
            file_path = self.tunnel_buttons[button_text][1]
            if file_path:
                with open(file_path, 'r') as file:
                    content = file.readlines()
                tk.Label(self.info_frame, text=f"Interface: {button_text}", anchor="w", justify="left", font="Roboto 11", bg="#f0f0f0").pack(fill=tk.X, pady=1)
                for line in content:
                    if line.strip() and not line.startswith("[") and not line.strip().startswith("PrivateKey"):
                        label = tk.Label(self.info_frame, text=line.strip(), anchor="w", justify="left", font="Roboto 11", bg="#f0f0f0")
                        label.pack(fill=tk.X, pady=1)
                self.toggle_button = ttk.Button(self.info_frame, text="Connect", style="TButton", command=self.toggle_connection)
                self.toggle_button.pack(side=tk.BOTTOM, fill=tk.Y, pady=(10, 0))
                self.connection_status = False
            else:
                label = tk.Label(self.info_frame, text="No file path associated with this button.", anchor="w", justify="left", bg="#f0f0f0")
                label.pack(fill=tk.X, pady=1)

    def toggle_connection(self):
        if self.selected_tunnel:
            button_text = self.selected_tunnel.cget("text")
            _, file_path = self.tunnel_buttons[button_text]

            wg = WGConfig(file_path)
            wg.read_file()
            interface = wg.get_interface()
            ip = interface['Address']
            private_key = interface['PrivateKey']
            peer = wg.peers
            str_peer = wg.get_peers()[0]

            ipr = IPRoute()

            if self.connection_status:
                try:
                    idx = ipr.link_lookup(ifname=f"{button_text}.conf")  # Правильное использование имени интерфейса
                    if idx:
                        ipr.link('set', index=idx[0], state='down')
                        ipr.link('del', index=idx[0])
                    self.connection_status = False
                    self.toggle_button.config(text="Connect")
                except NetlinkError as e:
                    print(f"Error bringing down interface: {e}")
            else:
                try:
                    idx = ipr.link_lookup(ifname=f"{button_text}.conf")
                    if not idx:
                        ipr.link('add', ifname=f"{button_text}.conf", kind='wireguard')
                        idx = ipr.link_lookup(ifname=f"{button_text}.conf")[0]
                        ipr.addr('add', index=idx, address=ip.split('/')[0], prefixlen=int(ip.split('/')[1]))
                        ipr.link('set', index=idx, state='up')

                        # Configure WireGuard
                        cmd = [
                            'wg', 'set', f"{button_text}.conf",  # Правильное использование имени интерфейса
                            'private-key', private_key,
                            'peer', peer[str_peer]['PublicKey'],
                            'endpoint', peer[str_peer]['Endpoint'],
                            'allowed-ips', peer[str_peer]['AllowedIPs']
                        ]
                        subprocess.run(cmd, check=True)
                    else:
                        print(f"Interface {button_text} already exists.")
                        self.connection_status = True  # Устанавливаем статус соединения как True
                        self.toggle_button.config(text="Disconnect")
                except NetlinkError as e:
                    print(f"Error bringing up interface: {e}")
                except subprocess.CalledProcessError as e:
                    print(f"Error configuring WireGuard: {e}")

    def save_tunnels(self):
        tunnels = {name: path for name, (_, path) in self.tunnel_buttons.items()}
        with open("tunnels.json", "w") as f:
            json.dump(tunnels, f)

    def load_tunnels(self):
        try:
            with open("tunnels.json", "r") as f:
                tunnels = json.load(f)
                for name, path in tunnels.items():
                    self.add_tunnel_button(name, path)
        except FileNotFoundError:
            pass

    def on_closing(self):
        self.save_tunnels()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = VPNApp(root)
    root.mainloop()