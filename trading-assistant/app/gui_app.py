"""Trading Assistant - desktop app window.

Wraps app_core.AppController in a Tkinter window: pick a strategy, pick
Trade Assistant or Auto Trade, connect to your MetaTrader 5 terminal,
and press Start. See ../README.md for the full manual, and
build_exe.bat for turning this into a standalone TradingAssistant.exe.

IMPORTANT: the MetaTrader5 Python package (used by live_data.py) only
works on Windows, and only once you already have the MT5 terminal
installed and logged into your broker account (Exness or any other
MT5 broker) on the same machine. This app talks to that local
terminal - it does not connect to a broker directly.
"""

import queue
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

from app_core import MODE_CHOICES, STRATEGY_CHOICES, TIMEFRAME_CHOICES, AppController
from broker import FakeBroker
from live_data import Mt5DataSource


class TradingAssistantApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Trading Assistant")
        self.root.geometry("640x640")
        self.root.minsize(560, 480)

        self._log_queue: "queue.Queue[str]" = queue.Queue()
        self._data_source = None  # created on Connect
        self._broker = None       # created on Connect
        self._controller = AppController(log=self._log_queue.put)

        self._build_widgets()
        self._poll_log_queue()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------
    def _build_widgets(self) -> None:
        pad = dict(padx=8, pady=4)

        conn = ttk.LabelFrame(self.root, text="Connection")
        conn.pack(fill="x", padx=10, pady=(10, 4))
        self.connect_btn = ttk.Button(conn, text="Connect to MT5", command=self._on_connect_clicked)
        self.connect_btn.grid(row=0, column=0, **pad)
        self.connection_status = tk.StringVar(value="Not connected")
        ttk.Label(conn, textvariable=self.connection_status).grid(row=0, column=1, sticky="w", **pad)

        settings = ttk.LabelFrame(self.root, text="Settings")
        settings.pack(fill="x", padx=10, pady=4)

        self.symbol_var = tk.StringVar(value="XAUUSD")
        self.timeframe_var = tk.StringVar(value="M15")
        self.strategy_var = tk.StringVar(value=STRATEGY_CHOICES[0])
        self.mode_var = tk.StringVar(value=MODE_CHOICES[0])
        self.volume_var = tk.StringVar(value="0.01")
        self.stop_distance_var = tk.StringVar(value="5.0")
        self.reward_multiple_var = tk.StringVar(value="2.0")
        self.cooldown_bars_var = tk.StringVar(value="5")
        self.max_losses_var = tk.StringVar(value="3")
        self.poll_seconds_var = tk.StringVar(value="5")

        def row(label, widget, r):
            ttk.Label(settings, text=label).grid(row=r, column=0, sticky="w", **pad)
            widget.grid(row=r, column=1, sticky="ew", **pad)

        settings.columnconfigure(1, weight=1)
        row("Symbol", ttk.Entry(settings, textvariable=self.symbol_var), 0)
        row("Timeframe", ttk.Combobox(settings, textvariable=self.timeframe_var,
                                       values=TIMEFRAME_CHOICES, state="readonly"), 1)
        row("Strategy", ttk.Combobox(settings, textvariable=self.strategy_var,
                                      values=STRATEGY_CHOICES, state="readonly", width=32), 2)
        row("Mode", ttk.Combobox(settings, textvariable=self.mode_var,
                                  values=MODE_CHOICES, state="readonly", width=32), 3)
        row("Volume (lots)", ttk.Entry(settings, textvariable=self.volume_var), 4)
        row("Stop distance (price, e.g. 5.0 = $5 on XAUUSD)", ttk.Entry(settings, textvariable=self.stop_distance_var), 5)
        row("Reward multiple (x stop)", ttk.Entry(settings, textvariable=self.reward_multiple_var), 6)
        row("Cooldown bars after a loss", ttk.Entry(settings, textvariable=self.cooldown_bars_var), 7)
        row("Max losses in a row before halt", ttk.Entry(settings, textvariable=self.max_losses_var), 8)
        row("Check every N seconds", ttk.Entry(settings, textvariable=self.poll_seconds_var), 9)

        controls = ttk.Frame(self.root)
        controls.pack(fill="x", padx=10, pady=4)
        self.start_btn = ttk.Button(controls, text="Start", command=self._on_start_clicked)
        self.start_btn.pack(side="left", padx=(0, 6))
        self.stop_btn = ttk.Button(controls, text="Stop", command=self._on_stop_clicked, state="disabled")
        self.stop_btn.pack(side="left", padx=6)
        self.reset_gate_btn = ttk.Button(controls, text="Reset Risk Gate", command=self._on_reset_gate_clicked)
        self.reset_gate_btn.pack(side="left", padx=6)
        self.running_status = tk.StringVar(value="Stopped")
        ttk.Label(controls, textvariable=self.running_status).pack(side="right")

        log_frame = ttk.LabelFrame(self.root, text="Log")
        log_frame.pack(fill="both", expand=True, padx=10, pady=(4, 10))
        self.log_widget = scrolledtext.ScrolledText(log_frame, state="disabled", wrap="word")
        self.log_widget.pack(fill="both", expand=True)

    # ------------------------------------------------------------------
    def _log(self, message: str) -> None:
        self.log_widget.configure(state="normal")
        self.log_widget.insert("end", message + "\n")
        self.log_widget.see("end")
        self.log_widget.configure(state="disabled")

    def _poll_log_queue(self) -> None:
        try:
            while True:
                self._log(self._log_queue.get_nowait())
        except queue.Empty:
            pass
        self.root.after(150, self._poll_log_queue)

    # ------------------------------------------------------------------
    def _on_connect_clicked(self) -> None:
        self._data_source = Mt5DataSource()
        try:
            self._data_source.connect()
        except Exception as exc:
            self._data_source = None
            self.connection_status.set("Connection failed")
            messagebox.showerror(
                "Could not connect to MT5",
                f"{exc}\n\nMake sure the MetaTrader 5 terminal is open and you are "
                f"logged into your broker account, and that this app was built/run "
                f"on the same Windows machine as that terminal.",
            )
            return

        symbol = self.symbol_var.get().strip()
        if not self._data_source.symbol_exists(symbol):
            self.connection_status.set("Connected, but symbol not found")
            messagebox.showwarning(
                "Symbol not found",
                f"Connected to MT5, but '{symbol}' isn't a known symbol on this account. "
                f"Check the spelling your broker uses (e.g. XAUUSD, XAUUSDm, GOLD).",
            )
            return

        self.connection_status.set(f"Connected ({symbol} found)")
        self._log(f"Connected to MetaTrader 5. Symbol '{symbol}' confirmed.")

    def _read_config(self) -> dict:
        return dict(
            symbol=self.symbol_var.get().strip(),
            timeframe=self.timeframe_var.get(),
            strategy=self.strategy_var.get(),
            mode=self.mode_var.get(),
            volume=float(self.volume_var.get()),
            stop_distance=float(self.stop_distance_var.get()),
            reward_multiple=float(self.reward_multiple_var.get()),
            cooldown_bars=int(self.cooldown_bars_var.get()),
            max_consecutive_losses=int(self.max_losses_var.get()),
            poll_seconds=float(self.poll_seconds_var.get()),
            history_bars=300,
        )

    def _on_start_clicked(self) -> None:
        if self._data_source is None:
            messagebox.showwarning("Not connected", "Click \"Connect to MT5\" first.")
            return

        try:
            config = self._read_config()
        except ValueError as exc:
            messagebox.showerror("Invalid setting", f"Check your numbers: {exc}")
            return

        if config["mode"].startswith("Auto"):
            from broker import Mt5Broker
            try:
                self._broker = Mt5Broker()
            except Exception as exc:
                messagebox.showerror("Could not set up trading", str(exc))
                return
        else:
            self._broker = FakeBroker()  # Assistant mode never trades - this is never touched for real orders

        self._controller.start(config, self._data_source, self._broker)
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.running_status.set("Running")

    def _on_stop_clicked(self) -> None:
        self._controller.stop()
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.running_status.set("Stopped")

    def _on_reset_gate_clicked(self) -> None:
        self._controller.reset_gate()

    def _on_close(self) -> None:
        self._controller.stop()
        if self._data_source is not None:
            self._data_source.disconnect()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    TradingAssistantApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
