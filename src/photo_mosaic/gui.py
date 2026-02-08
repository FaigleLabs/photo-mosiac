from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk

from photo_mosaic.config import FitMode, HexBackground, MosaicConfig, Strategy, TileShape
from photo_mosaic.core.mosaic import build_mosaic


class PhotoMosaicApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Photo Mosaic - Free [FaigleLabs]")
        self.root.geometry("1000x720")

        self.source_var = tk.StringVar()
        self.output_var = tk.StringVar()
        self.cache_var = tk.StringVar()

        self.tile_w_var = tk.StringVar(value="16")
        self.tile_h_var = tk.StringVar(value="16")
        self.out_w_var = tk.StringVar(value="")
        self.out_h_var = tk.StringVar(value="")

        self.fit_mode_var = tk.StringVar(value=FitMode.CROP.value)
        self.tile_shape_var = tk.StringVar(value=TileShape.RECT.value)
        self.hex_overlap_var = tk.StringVar(value="0.25")
        self.hex_edge_softness_var = tk.StringVar(value="0.2")
        self.hex_background_var = tk.StringVar(value=HexBackground.SOURCE.value)
        self.strategy_var = tk.StringVar(value=Strategy.GREEDY.value)

        self.max_repeats_var = tk.StringVar(value="")
        self.max_usage_pct_var = tk.StringVar(value="")

        self.lazy_randomness_var = tk.StringVar(value="0.15")
        self.lazy_top_k_var = tk.StringVar(value="5")
        self.random_steps_var = tk.StringVar(value="1000")
        self.full_steps_var = tk.StringVar(value="2000")

        self.refresh_cache_var = tk.BooleanVar(value=False)

        self.status_var = tk.StringVar(value="Ready")
        self.preview_photo: ImageTk.PhotoImage | None = None

        self.tile_dirs: list[Path] = []

        self._build_ui()

    def _build_ui(self) -> None:
        frame = ttk.Frame(self.root, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(frame)
        left.pack(side=tk.LEFT, fill=tk.Y)
        right = ttk.Frame(frame)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(12, 0))

        self._build_inputs(left)
        self._build_preview(right)

    def _build_inputs(self, parent: ttk.Frame) -> None:
        row = 0

        ttk.Label(parent, text="Source Image").grid(row=row, column=0, sticky="w")
        ttk.Entry(parent, textvariable=self.source_var, width=44).grid(row=row, column=1, sticky="ew")
        ttk.Button(parent, text="Browse", command=self._pick_source).grid(row=row, column=2, padx=(6, 0))
        row += 1

        ttk.Label(parent, text="Tile Directories").grid(row=row, column=0, sticky="nw", pady=(8, 0))
        tiles_frame = ttk.Frame(parent)
        tiles_frame.grid(row=row, column=1, columnspan=2, sticky="ew", pady=(8, 0))

        self.tile_listbox = tk.Listbox(tiles_frame, height=5, width=44)
        self.tile_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tiles_btns = ttk.Frame(tiles_frame)
        tiles_btns.pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(tiles_btns, text="Add", command=self._add_tile_dir).pack(fill=tk.X)
        ttk.Button(tiles_btns, text="Remove", command=self._remove_tile_dir).pack(fill=tk.X, pady=(6, 0))
        row += 1

        ttk.Label(parent, text="Output Image").grid(row=row, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(parent, textvariable=self.output_var, width=44).grid(row=row, column=1, sticky="ew", pady=(8, 0))
        ttk.Button(parent, text="Browse", command=self._pick_output).grid(row=row, column=2, padx=(6, 0), pady=(8, 0))
        row += 1

        ttk.Separator(parent, orient="horizontal").grid(row=row, column=0, columnspan=3, sticky="ew", pady=12)
        row += 1

        ttk.Label(parent, text="Tile Width").grid(row=row, column=0, sticky="w")
        ttk.Entry(parent, textvariable=self.tile_w_var, width=12).grid(row=row, column=1, sticky="w")
        row += 1

        ttk.Label(parent, text="Tile Height").grid(row=row, column=0, sticky="w", pady=(6, 0))
        ttk.Entry(parent, textvariable=self.tile_h_var, width=12).grid(row=row, column=1, sticky="w", pady=(6, 0))
        row += 1

        ttk.Label(parent, text="Output Width (opt)").grid(row=row, column=0, sticky="w", pady=(6, 0))
        ttk.Entry(parent, textvariable=self.out_w_var, width=12).grid(row=row, column=1, sticky="w", pady=(6, 0))
        row += 1

        ttk.Label(parent, text="Output Height (opt)").grid(row=row, column=0, sticky="w", pady=(6, 0))
        ttk.Entry(parent, textvariable=self.out_h_var, width=12).grid(row=row, column=1, sticky="w", pady=(6, 0))
        row += 1

        ttk.Label(parent, text="Tile Shape").grid(row=row, column=0, sticky="w", pady=(6, 0))
        ttk.Combobox(parent, textvariable=self.tile_shape_var, values=[s.value for s in TileShape], state="readonly", width=12).grid(
            row=row, column=1, sticky="w", pady=(6, 0)
        )
        row += 1

        ttk.Label(parent, text="Hex Overlap").grid(row=row, column=0, sticky="w", pady=(6, 0))
        ttk.Entry(parent, textvariable=self.hex_overlap_var, width=12).grid(row=row, column=1, sticky="w", pady=(6, 0))
        row += 1

        ttk.Label(parent, text="Hex Edge Softness").grid(row=row, column=0, sticky="w", pady=(6, 0))
        ttk.Entry(parent, textvariable=self.hex_edge_softness_var, width=12).grid(row=row, column=1, sticky="w", pady=(6, 0))
        row += 1

        ttk.Label(parent, text="Hex Background").grid(row=row, column=0, sticky="w", pady=(6, 0))
        ttk.Combobox(
            parent,
            textvariable=self.hex_background_var,
            values=[s.value for s in HexBackground],
            state="readonly",
            width=12,
        ).grid(row=row, column=1, sticky="w", pady=(6, 0))
        row += 1

        ttk.Label(parent, text="Fit Mode").grid(row=row, column=0, sticky="w", pady=(6, 0))
        ttk.Combobox(parent, textvariable=self.fit_mode_var, values=[m.value for m in FitMode], state="readonly", width=12).grid(
            row=row, column=1, sticky="w", pady=(6, 0)
        )
        row += 1

        ttk.Label(parent, text="Strategy").grid(row=row, column=0, sticky="w", pady=(6, 0))
        ttk.Combobox(
            parent,
            textvariable=self.strategy_var,
            values=[s.value for s in Strategy],
            state="readonly",
            width=12,
        ).grid(row=row, column=1, sticky="w", pady=(6, 0))
        row += 1

        ttk.Label(parent, text="Max Repeats (opt)").grid(row=row, column=0, sticky="w", pady=(6, 0))
        ttk.Entry(parent, textvariable=self.max_repeats_var, width=12).grid(row=row, column=1, sticky="w", pady=(6, 0))
        row += 1

        ttk.Label(parent, text="Max Usage % (opt)").grid(row=row, column=0, sticky="w", pady=(6, 0))
        ttk.Entry(parent, textvariable=self.max_usage_pct_var, width=12).grid(row=row, column=1, sticky="w", pady=(6, 0))
        row += 1

        ttk.Label(parent, text="Lazy Randomness").grid(row=row, column=0, sticky="w", pady=(6, 0))
        ttk.Entry(parent, textvariable=self.lazy_randomness_var, width=12).grid(row=row, column=1, sticky="w", pady=(6, 0))
        row += 1

        ttk.Label(parent, text="Lazy Top K").grid(row=row, column=0, sticky="w", pady=(6, 0))
        ttk.Entry(parent, textvariable=self.lazy_top_k_var, width=12).grid(row=row, column=1, sticky="w", pady=(6, 0))
        row += 1

        ttk.Label(parent, text="Random Steps").grid(row=row, column=0, sticky="w", pady=(6, 0))
        ttk.Entry(parent, textvariable=self.random_steps_var, width=12).grid(row=row, column=1, sticky="w", pady=(6, 0))
        row += 1

        ttk.Label(parent, text="Full Steps").grid(row=row, column=0, sticky="w", pady=(6, 0))
        ttk.Entry(parent, textvariable=self.full_steps_var, width=12).grid(row=row, column=1, sticky="w", pady=(6, 0))
        row += 1

        ttk.Label(parent, text="Cache Path (opt)").grid(row=row, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(parent, textvariable=self.cache_var, width=44).grid(row=row, column=1, sticky="ew", pady=(8, 0))
        ttk.Button(parent, text="Browse", command=self._pick_cache).grid(row=row, column=2, padx=(6, 0), pady=(8, 0))
        row += 1

        ttk.Checkbutton(parent, text="Refresh cache", variable=self.refresh_cache_var).grid(row=row, column=1, sticky="w", pady=(8, 0))
        row += 1

        ttk.Button(parent, text="Build Mosaic", command=self._start_build).grid(row=row, column=1, sticky="w", pady=(14, 0))
        row += 1

        ttk.Label(parent, textvariable=self.status_var, foreground="#1f2937").grid(row=row, column=0, columnspan=3, sticky="w", pady=(10, 0))

    def _build_preview(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="Output Preview").pack(anchor="w")
        self.preview_label = ttk.Label(parent)
        self.preview_label.pack(fill=tk.BOTH, expand=True)

    def _pick_source(self) -> None:
        path = filedialog.askopenfilename(
            title="Choose source image",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.webp *.tif *.tiff")],
        )
        if path:
            self.source_var.set(path)

    def _pick_output(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Choose output image",
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg"), ("WEBP", "*.webp")],
        )
        if path:
            self.output_var.set(path)

    def _pick_cache(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Choose cache path",
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
        )
        if path:
            self.cache_var.set(path)

    def _add_tile_dir(self) -> None:
        path = filedialog.askdirectory(title="Choose tile directory")
        if not path:
            return
        p = Path(path)
        if p not in self.tile_dirs:
            self.tile_dirs.append(p)
            self.tile_listbox.insert(tk.END, str(p))

    def _remove_tile_dir(self) -> None:
        selected = list(self.tile_listbox.curselection())
        for idx in reversed(selected):
            self.tile_listbox.delete(idx)
            del self.tile_dirs[idx]

    def _start_build(self) -> None:
        try:
            config = self._build_config()
        except Exception as exc:
            messagebox.showerror("Invalid Configuration", str(exc))
            return

        self.status_var.set("Building mosaic...")
        thread = threading.Thread(target=self._run_build, args=(config,), daemon=True)
        thread.start()

    def _run_build(self, config: MosaicConfig) -> None:
        try:
            output = build_mosaic(config)
            self.root.after(0, lambda: self._on_build_success(output))
        except Exception as exc:  # noqa: BLE001
            self.root.after(0, lambda: self._on_build_failure(exc))

    def _on_build_success(self, output: Path) -> None:
        self.status_var.set(f"Done: {output}")
        self._render_preview(output)

    def _on_build_failure(self, exc: Exception) -> None:
        self.status_var.set("Build failed")
        messagebox.showerror("Build Failed", str(exc))

    def _render_preview(self, path: Path) -> None:
        with Image.open(path) as img:
            preview = img.convert("RGB")
            preview.thumbnail((640, 640), Image.Resampling.BICUBIC)

        self.preview_photo = ImageTk.PhotoImage(preview)
        self.preview_label.configure(image=self.preview_photo)

    def _build_config(self) -> MosaicConfig:
        if not self.source_var.get().strip():
            raise ValueError("Source image is required")
        if not self.output_var.get().strip():
            raise ValueError("Output image path is required")
        if not self.tile_dirs:
            raise ValueError("At least one tile directory is required")

        out_w = self._parse_optional_int(self.out_w_var.get())
        out_h = self._parse_optional_int(self.out_h_var.get())
        max_repeats = self._parse_optional_int(self.max_repeats_var.get())
        max_usage = self._parse_optional_float(self.max_usage_pct_var.get())

        cache_value = self.cache_var.get().strip()
        cache_path = Path(cache_value) if cache_value else None

        return MosaicConfig(
            source_image=Path(self.source_var.get().strip()),
            tile_dirs=self.tile_dirs[:],
            output_path=Path(self.output_var.get().strip()),
            tile_width=int(self.tile_w_var.get().strip()),
            tile_height=int(self.tile_h_var.get().strip()),
            output_width=out_w,
            output_height=out_h,
            tile_shape=TileShape(self.tile_shape_var.get()),
            hex_overlap=float(self.hex_overlap_var.get().strip()),
            hex_edge_softness=float(self.hex_edge_softness_var.get().strip()),
            hex_background=HexBackground(self.hex_background_var.get()),
            fit_mode=FitMode(self.fit_mode_var.get()),
            strategy=Strategy(self.strategy_var.get()),
            max_repeats=max_repeats,
            max_usage_percent=max_usage,
            lazy_randomness=float(self.lazy_randomness_var.get().strip()),
            lazy_top_k=int(self.lazy_top_k_var.get().strip()),
            random_steps=int(self.random_steps_var.get().strip()),
            full_steps=int(self.full_steps_var.get().strip()),
            cache_path=cache_path,
            refresh_cache=self.refresh_cache_var.get(),
        )

    @staticmethod
    def _parse_optional_int(value: str) -> int | None:
        value = value.strip()
        if not value:
            return None
        return int(value)

    @staticmethod
    def _parse_optional_float(value: str) -> float | None:
        value = value.strip()
        if not value:
            return None
        return float(value)


def launch_gui() -> None:
    root = tk.Tk()
    PhotoMosaicApp(root)
    root.mainloop()
