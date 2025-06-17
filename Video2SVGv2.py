import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
from PIL import Image, ImageTk
import cv2
import numpy as np
import os
import threading
import subprocess
import re
import io
import datetime

# this script was created by ProjectileObjects. It is designed to help convert video files into .SVG sequences for the use of RGB laser projectors (such as the LaserCube, Pangolin, and others).
# --- Constants ---
PREVIEW_WIDTH = 640
PREVIEW_HEIGHT = 480
OUTPUT_PREVIEW_SIZE = 210 # For the 1:1 aspect ratio preview

class InfoWindow(tk.Toplevel):
    """A simple popup window to display help text."""
    def __init__(self, parent, title, message):
        super().__init__(parent)
        self.title(title)
        self.geometry("350x180") # Increased height for text
        self.resizable(False, False)
        
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(expand=True, fill="both")

        msg_label = ttk.Label(main_frame, text=message, wraplength=330, justify="left")
        msg_label.pack(expand=True, fill="both", pady=5)
        
        ok_button = ttk.Button(main_frame, text="OK", command=self.destroy)
        ok_button.pack(pady=5)
        
        self.transient(parent)
        self.grab_set()
        parent.wait_window(self)

class VideoToSVGConverter:
    """
    A GUI application for converting video segments to a sequence of SVG frames
    using Canny edge detection and the Potrace utility.
    """
    def __init__(self, root):
        self.root = root
        self.root.title("Video to SVG Converter v2")
        self.root.resizable(True, True) # Make window resizable

        # --- State Variables ---
        self.video_path = None
        self.output_path = None
        self.capture = None
        self.total_frames = 0
        self.fps = 30 # Default FPS
        self.in_frame = 0
        self.out_frame = -1
        self.is_potrace_installed = self.check_potrace()
        self.preview_update_job = None
        self.preview_thread = None
        self.preview_image_size = (0, 0) # Store actual size of image in preview
        self.preview_image_offset = (0, 0) # Store offset of image in preview

        # --- New Feature State Variables ---
        self.is_crop_enabled = tk.BooleanVar(value=False)
        self.crop_rect_id = None
        self.crop_coords = None
        self.is_1_to_1_aspect = tk.BooleanVar(value=True) # Default to 1:1
        self.is_multipass = tk.BooleanVar(value=False)
        self.stroke_color = tk.StringVar(value="#000000")
        self.scale_mode = tk.StringVar(value="Fill") # Default to Fill
        
        # Optimized Defaults
        self.zoom_level = tk.DoubleVar(value=1.0)
        self.x_offset = tk.DoubleVar(value=0.0)
        self.y_offset = tk.DoubleVar(value=0.0)
        self.brightness = tk.IntVar(value=0)
        self.contrast = tk.DoubleVar(value=1.0)
        self.pre_blur = tk.IntVar(value=0) # Start with blur off
        self.optimization_level = tk.DoubleVar(value=0.2)
        self.speckle_removal = tk.IntVar(value=2)
        self.corner_smoothing = tk.DoubleVar(value=1.0)

        # --- UI Setup ---
        self.create_styles()
        self.create_widgets()
        
        if not self.is_potrace_installed:
            messagebox.showerror("Dependency Missing","'potrace' not found. Please install it using Homebrew:\n'brew install potrace'")
            self.start_button.config(state=tk.DISABLED)

    def check_potrace(self):
        try:
            subprocess.run(['potrace', '--version'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def create_styles(self):
        style = ttk.Style()
        style.configure("TButton", padding=6, relief="flat")
        style.configure("Help.TButton", padding=(2,0), font=("Helvetica", 12, "bold"))
        style.configure("TLabel", padding=5)

    def create_widgets(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=0)
        main_frame.rowconfigure(0, weight=1)

        # --- Left Column ---
        left_frame = ttk.Frame(main_frame)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left_frame.rowconfigure(1, weight=1)
        left_frame.columnconfigure(0, weight=1)
        
        ttk.Label(left_frame, text="Input Window", font=("Helvetica", 10, "italic")).grid(row=0, column=0, sticky='w', padx=5)

        self.preview_canvas = tk.Canvas(left_frame, width=PREVIEW_WIDTH, height=PREVIEW_HEIGHT, bg="black", highlightthickness=0)
        self.preview_canvas.grid(row=1, column=0, sticky="nsew")
        self.preview_canvas.bind("<ButtonPress-1>", self.on_mouse_press)
        self.preview_canvas.bind("<B1-Motion>", self.on_mouse_move)
        self.preview_canvas.bind("<ButtonRelease-1>", self.on_mouse_release)
        
        timeline_controls_frame = ttk.Frame(left_frame)
        timeline_controls_frame.grid(row=2, column=0, sticky="ew")
        timeline_controls_frame.columnconfigure(0, weight=1)
        
        self.current_time_label = ttk.Label(timeline_controls_frame, text="00:00:00:00", font=("Courier", 10), anchor="center")
        self.current_time_label.grid(row=0, column=0, sticky="ew")
        
        self.timeline_slider = ttk.Scale(timeline_controls_frame, from_=0, to=100, orient="horizontal", command=self.schedule_preview_update, state=tk.DISABLED)
        self.timeline_slider.grid(row=1, column=0, sticky="ew")
        self.timeline_slider.bind("<Button-1>", self.on_slider_click)

        self.timeline_indicator = tk.Canvas(timeline_controls_frame, height=8, bg="#2e2e2e", highlightthickness=0)
        self.timeline_indicator.grid(row=2, column=0, sticky="ew")
        
        self.output_preview_frame = ttk.Frame(left_frame)
        self.output_preview_frame.grid(row=4, column=0, pady=10) # Always visible
        self.output_preview_canvas = tk.Canvas(self.output_preview_frame, width=OUTPUT_PREVIEW_SIZE, height=OUTPUT_PREVIEW_SIZE, bg="black", highlightthickness=0)
        self.output_preview_canvas.pack()
        ttk.Label(self.output_preview_frame, text="Output Preview", font=("Helvetica", 10, "italic")).pack()

        # --- Right Column ---
        right_frame = ttk.Frame(main_frame)
        right_frame.grid(row=0, column=1, sticky="ns")

        # File Setup
        file_lf = self._create_control_group(right_frame, "1. File Setup", 0)
        ttk.Button(file_lf, text="Select Video", command=self.select_video_file).grid(row=0, column=0, padx=5, pady=5)
        self.video_path_label = ttk.Label(file_lf, text="No video", relief="sunken", anchor="w", width=30)
        self.video_path_label.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        ttk.Button(file_lf, text="Select Output", command=self.select_output_folder).grid(row=1, column=0, padx=5, pady=5)
        self.output_path_label = ttk.Label(file_lf, text="No folder", relief="sunken", anchor="w", width=30)
        self.output_path_label.grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        
        # Timeline Controls
        inout_lf = self._create_control_group(right_frame, "2. Timeline Controls", 1)
        self.set_in_button = ttk.Button(inout_lf, text="Set In", command=self.set_in_point, state=tk.DISABLED)
        self.set_in_button.grid(row=0, column=0, padx=5)
        self.in_time_entry = ttk.Entry(inout_lf, width=12, justify='center')
        self.in_time_entry.grid(row=0, column=1)
        self.in_time_entry.bind("<Return>", self.set_in_from_entry)
        
        self.set_out_button = ttk.Button(inout_lf, text="Set Out", command=self.set_out_point, state=tk.DISABLED)
        self.set_out_button.grid(row=0, column=2, padx=5)
        self.out_time_entry = ttk.Entry(inout_lf, width=12, justify='center')
        self.out_time_entry.grid(row=0, column=3)
        self.out_time_entry.bind("<Return>", self.set_out_from_entry)

        # Image Adjustments
        controls_lf = self._create_control_group(right_frame, "3. Image Adjustments", 2)
        crop_row = self._create_row(controls_lf, 0)
        ttk.Checkbutton(crop_row, text="Crop", variable=self.is_crop_enabled, command=self.toggle_framing_mode).grid(row=0, column=0, padx=5)
        ttk.Button(crop_row, text="Clear Crop", command=self.clear_crop).grid(row=0, column=1)
        ttk.Checkbutton(crop_row, text="1:1", variable=self.is_1_to_1_aspect, command=self.schedule_preview_update).grid(row=0, column=2, padx=5)
        self.scale_mode_combo = ttk.Combobox(crop_row, textvariable=self.scale_mode, values=["Fit", "Fill", "Stretch"], width=8, state="readonly")
        self.scale_mode_combo.grid(row=0, column=3, padx=5)
        self.scale_mode_combo.bind("<<ComboboxSelected>>", self.schedule_preview_update)

        self.threshold1_slider_var = tk.IntVar(value=50)
        self.threshold2_slider_var = tk.IntVar(value=150)
        self.zoom_slider = self._create_labeled_slider(controls_lf, 1, "Zoom:", 1.0, 4.0, self.zoom_level)
        self.x_offset_slider = self._create_labeled_slider(controls_lf, 2, "X Offset:", -100, 100, self.x_offset)
        self.y_offset_slider = self._create_labeled_slider(controls_lf, 3, "Y Offset:", -100, 100, self.y_offset)
        self._create_labeled_slider(controls_lf, 4, "Brightness:", -100, 100, self.brightness)
        self._create_labeled_slider(controls_lf, 5, "Contrast:", 0.1, 3.0, self.contrast)
        self._create_labeled_slider(controls_lf, 6, "Pre-Blur:", 0, 25, self.pre_blur)
        self._create_labeled_slider(controls_lf, 7, "Threshold 1:", 0, 255, self.threshold1_slider_var)
        self._create_labeled_slider(controls_lf, 8, "Threshold 2:", 0, 255, self.threshold2_slider_var)
        
        # Laser Optimization
        style_lf = self._create_control_group(right_frame, "4. Laser Optimization", 3)
        ttk.Label(style_lf, text="(Affects final export only)", font=("Helvetica", 8, "italic"), foreground="gray").grid(row=0, sticky='w', padx=5)
        
        color_row = self._create_row(style_lf, 1)
        ttk.Button(color_row, text="Stroke Color", command=self.choose_stroke_color).grid(row=0, column=0, padx=5)
        self.color_swatch_label = tk.Label(color_row, text="  ", bg=self.stroke_color.get(), relief='sunken')
        self.color_swatch_label.grid(row=0, column=1, padx=5)
        ttk.Checkbutton(color_row, text="Multi-Pass (Centerline)", variable=self.is_multipass).grid(row=0, column=2, padx=5)

        self._create_labeled_slider(style_lf, 2, "Speckle Removal:", 0, 50, self.speckle_removal, help_text="Removes small, noisy pixel groups before vectorization. Higher values remove larger noise but can erase detail. A value of 2-5 is a good starting point.")
        self._create_labeled_slider(style_lf, 3, "Curve Smoothing:", 0.0, 5.0, self.optimization_level, help_text="Controls how closely the vector path follows the pixel outline. Higher values create simpler, smoother (but less accurate) curves.")
        self._create_labeled_slider(style_lf, 4, "Corner Smoothing:", 0.0, 1.334, self.corner_smoothing, help_text="Controls the sharpness of corners. Higher values produce more rounded, fluid corners, which is ideal for reducing laser burns and mechanical stress.")
        
        # Conversion
        conv_lf = self._create_control_group(right_frame, "5. Convert", 4)
        
        self.point_estimate_label = ttk.Label(conv_lf, text="Point Estimate: ---", font=("Helvetica", 10, "italic"))
        self.point_estimate_label.grid(row=0, column=0, sticky="ew", pady=(0,5))
        
        self.start_button = ttk.Button(conv_lf, text="Start Conversion", command=self.start_conversion)
        self.start_button.grid(row=1, column=0, sticky='ew', padx=5, pady=5)
        
        self.progress_bar = ttk.Progressbar(right_frame, orient="horizontal", mode='determinate')
        self.progress_bar.grid(row=5, column=0, sticky="ew", pady=5)
        self.status_label = ttk.Label(right_frame, text="Status: Ready", anchor="w")
        self.status_label.grid(row=6, column=0, sticky="ew")

        ttk.Label(main_frame, text="Free to use thanks to ProjectileObjects", font=("Helvetica", 8, "italic"), foreground="gray").grid(row=1, column=0, sticky='sw', pady=(10,0))

        # Bind keyboard shortcuts
        self.root.bind('<KeyPress-i>', lambda e: self.set_in_point())
        self.root.bind('<KeyPress-o>', lambda e: self.set_out_point())

    def _create_control_group(self, parent, text, row):
        lf = ttk.Labelframe(parent, text=text, padding=5)
        lf.grid(row=row, column=0, sticky="ew", pady=(0, 10))
        lf.columnconfigure(0, weight=1)
        return lf

    def _create_row(self, parent, row):
        frame = ttk.Frame(parent)
        frame.grid(row=row, column=0, sticky='ew')
        return frame

    def _create_labeled_slider(self, parent, row, text, from_, to, variable, help_text=None):
        frame = self._create_row(parent, row)
        frame.columnconfigure(1, weight=1)
        
        ttk.Label(frame, text=text).grid(row=0, column=0, padx=5, sticky='w')
        slider = ttk.Scale(frame, from_=from_, to=to, variable=variable, orient="horizontal")
        slider.grid(row=0, column=1, sticky='ew')
        
        label_var = tk.StringVar()
        label = ttk.Label(frame, textvariable=label_var, width=6)
        label.grid(row=0, column=2, padx=5)

        if help_text:
            help_button = ttk.Button(frame, text="?", style="Help.TButton", width=2, command=lambda: InfoWindow(self.root, text, help_text))
            help_button.grid(row=0, column=3)
        
        slider.label_var = label_var # Attach for easy access
        slider.configure(command=lambda v, s=slider: self.update_slider_label(v, s))
        self.update_slider_label(None, slider)
        return slider

    def update_slider_label(self, value, slider):
        val = slider.get()
        slider.label_var.set(f"{val:.2f}" if isinstance(val, float) else f"{int(val)}")
        self.schedule_preview_update()
        
    def toggle_framing_mode(self):
        """Disables zoom/pan when cropping is active, and vice-versa."""
        if self.is_crop_enabled.get():
            self.zoom_slider.config(state="disabled")
            self.x_offset_slider.config(state="disabled")
            self.y_offset_slider.config(state="disabled")
        else:
            self.zoom_slider.config(state="normal")
            self.x_offset_slider.config(state="normal")
            self.y_offset_slider.config(state="normal")
        self.schedule_preview_update()

    def schedule_preview_update(self, *args):
        if self.preview_update_job: self.root.after_cancel(self.preview_update_job)
        self.preview_update_job = self.root.after(50, self.start_preview_generation_thread)

    def start_preview_generation_thread(self):
        if self.preview_thread and self.preview_thread.is_alive(): return
        if not self.capture or not self.capture.isOpened(): return
        self.preview_thread = threading.Thread(target=self._process_frame_for_preview, daemon=True)
        self.preview_thread.start()

    def _process_frame_for_preview(self):
        try:
            frame_num = int(self.timeline_slider.get())
            self.capture.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
            ret, frame = self.capture.read()
            if not ret: return

            processed_full = self.apply_image_adjustments(frame)
            
            preview_w = self.preview_canvas.winfo_width()
            preview_h = self.preview_canvas.winfo_height()
            if preview_w <= 1: preview_w = PREVIEW_WIDTH
            if preview_h <= 1: preview_h = PREVIEW_HEIGHT
            
            h, w = processed_full.shape[:2]
            scale = min(preview_w/w, preview_h/h) if h > 0 and w > 0 else 1
            self.preview_image_size = (int(w*scale), int(h*scale))
            self.preview_image_offset = ((preview_w - self.preview_image_size[0])//2, (preview_h - self.preview_image_size[1])//2)

            resized = cv2.resize(processed_full, self.preview_image_size, interpolation=cv2.INTER_AREA) if h > 0 and w > 0 else processed_full
            main_edges = cv2.Canny(resized, self.threshold1_slider_var.get(), self.threshold2_slider_var.get())
            main_photo = self._get_photo_from_data(main_edges)
            
            output_edges = self._get_output_preview_edges(frame)
            output_photo = self._get_photo_from_data(output_edges) if output_edges is not None else None

            inverted_edges = cv2.bitwise_not(main_edges)
            point_count = self._run_potrace_estimate(inverted_edges)

            self.root.after(0, self._update_ui_from_thread, frame_num, main_photo, output_photo, point_count)
        except Exception as e:
            print(f"Error in preview thread: {e}")

    def _get_photo_from_data(self, image_data):
        img_rgb = cv2.cvtColor(image_data, cv2.COLOR_GRAY2RGB) if len(image_data.shape) == 2 else image_data
        img_pil = Image.fromarray(img_rgb)
        return ImageTk.PhotoImage(image=img_pil)

    def _update_ui_from_thread(self, frame_num, main_photo, output_photo, point_count):
        self.preview_canvas.create_image(self.preview_image_offset[0], self.preview_image_offset[1], anchor="nw", image=main_photo)
        self.preview_canvas.photo = main_photo
        if self.crop_rect_id: self.preview_canvas.tag_raise(self.crop_rect_id)

        if output_photo:
            self.output_preview_canvas.create_image(0, 0, anchor="nw", image=output_photo)
            self.output_preview_canvas.photo = output_photo
        else:
             self.output_preview_canvas.delete("all")

        self.point_estimate_label.config(text=f"Point Estimate: ~{point_count}")
        self._update_timeline_indicator()
        self.current_time_label.config(text=self.format_time(frame_num))

    def on_slider_click(self, event):
        slider = event.widget
        clicked_value = (event.x / slider.winfo_width()) * (slider['to'] - slider['from'])
        slider.set(clicked_value)
        self.schedule_preview_update()
        
    def on_mouse_press(self, event):
        if not self.is_crop_enabled.get(): return
        if self.crop_rect_id: self.preview_canvas.delete(self.crop_rect_id)
        self.crop_coords = [event.x, event.y, event.x, event.y]
        self.crop_rect_id = self.preview_canvas.create_rectangle(*self.crop_coords, outline="red", width=2, dash=(4, 2))

    def on_mouse_move(self, event):
        if not self.is_crop_enabled.get() or not self.crop_coords: return
        self.crop_coords[2], self.crop_coords[3] = event.x, event.y
        self.preview_canvas.coords(self.crop_rect_id, *self.crop_coords)
    
    def on_mouse_release(self, event):
        if not self.is_crop_enabled.get() or not self.crop_coords: return
        x1, y1, x2, y2 = self.crop_coords
        self.crop_coords = [min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)]
        self.preview_canvas.coords(self.crop_rect_id, *self.crop_coords)
        self.schedule_preview_update()

    def clear_crop(self):
        if self.crop_rect_id: self.preview_canvas.delete(self.crop_rect_id)
        self.crop_rect_id = None; self.crop_coords = None
        self.is_crop_enabled.set(False)
        self.toggle_framing_mode()
            
    def select_video_file(self):
        path = filedialog.askopenfilename(filetypes=[("Video Files", "*.mp4 *.avi *.mov")])
        if not path: return
        self.video_path = path; self.video_path_label.config(text=os.path.basename(path))
        self.load_video()
        
    def select_output_folder(self):
        path = filedialog.askdirectory()
        if not path: return
        self.output_path = path; self.output_path_label.config(text=self.output_path)

    def load_video(self):
        if self.capture: self.capture.release()
        self.capture = cv2.VideoCapture(self.video_path)
        if not self.capture.isOpened():
            messagebox.showerror("Error", "Could not open video file."); return
            
        self.total_frames = int(self.capture.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.capture.get(cv2.CAP_PROP_FPS) or 30
        
        self.timeline_slider.config(to=self.total_frames - 1, state="normal")
        self.set_in_button.config(state='normal'); self.set_out_button.config(state='normal')
        
        self.in_frame = 0
        self.out_frame = self.total_frames - 1
        self.update_in_out_entries()
        self.clear_crop()
        
        self.timeline_slider.set(0); self.schedule_preview_update()

    def apply_pan_and_zoom(self, frame):
        zoom = self.zoom_level.get()
        
        h, w = frame.shape[:2]
        
        # Calculate the size of the zoomed-in window
        zoomed_w = int(w / zoom)
        zoomed_h = int(h / zoom)
        
        # Calculate the maximum possible offset from the center
        max_offset_x = (w - zoomed_w) / 2
        max_offset_y = (h - zoomed_h) / 2
        
        # Normalize slider values from -100,100 to a -1,1 range
        norm_x = self.x_offset.get() / 100.0
        norm_y = self.y_offset.get() / 100.0
        
        # Calculate the actual pixel offset based on the max possible offset
        offset_x = int(norm_x * max_offset_x)
        offset_y = int(norm_y * max_offset_y)
        
        # Calculate the top-left corner of the crop window
        center_x, center_y = w // 2, h // 2
        x1 = center_x - (zoomed_w // 2) + offset_x
        y1 = center_y - (zoomed_h // 2) + offset_y
        
        # Clamp coordinates to ensure they are within the frame bounds
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x1 + zoomed_w), min(h, y1 + zoomed_h)
        
        return frame[y1:y2, x1:x2]
        
    def apply_image_adjustments(self, frame):
        adjusted = cv2.convertScaleAbs(frame, alpha=self.contrast.get(), beta=self.brightness.get())
        blur_k = self.pre_blur.get() * 2 + 1
        return cv2.GaussianBlur(adjusted, (blur_k, blur_k), 0) if blur_k > 1 else adjusted

    def _update_timeline_indicator(self):
        self.timeline_indicator.delete("all")
        if self.total_frames <= 1: return
        self.root.update_idletasks()
        widget_width = self.timeline_slider.winfo_width()
        if widget_width <= 1: return
        
        in_x = (self.in_frame / self.total_frames) * widget_width
        out_x = (self.out_frame / self.total_frames) * widget_width
        self.timeline_indicator.create_rectangle(in_x, 0, out_x, 8, fill="#0078d4", outline="")
        
    def _get_output_preview_edges(self, original_frame):
        source_img = original_frame
        
        if self.is_crop_enabled.get() and self.crop_coords:
            h, w = original_frame.shape[:2]
            scale_w = w / self.preview_image_size[0]
            scale_h = h / self.preview_image_size[1]
            x1, y1 = self.crop_coords[0] - self.preview_image_offset[0], self.crop_coords[1] - self.preview_image_offset[1]
            x2, y2 = self.crop_coords[2] - self.preview_image_offset[0], self.crop_coords[3] - self.preview_image_offset[1]
            
            frame_x1, frame_y1 = int(x1 * scale_w), int(y1 * scale_h)
            frame_x2, frame_y2 = int(x2 * scale_w), int(y2 * scale_h)
            
            if frame_x2 > frame_x1 and frame_y2 > frame_y1:
                source_img = original_frame[frame_y1:frame_y2, frame_x1:frame_x2]
        else:
             source_img = self.apply_pan_and_zoom(source_img)

        if self.is_1_to_1_aspect.get():
            h, w = source_img.shape[:2]
            side = min(h, w); x_off = (w - side) // 2; y_off = (h - side) // 2
            source_img = source_img[y_off:y_off+side, x_off:x_off+side]
        
        h, w = source_img.shape[:2]
        if h == 0 or w == 0: return None
        out_w, out_h = OUTPUT_PREVIEW_SIZE, OUTPUT_PREVIEW_SIZE
        mode = self.scale_mode.get()
        
        if mode == "Stretch":
            scaled = cv2.resize(source_img, (out_w, out_h), interpolation=cv2.INTER_AREA)
        else: # Fit or Fill
            scale = min(out_w/w, out_h/h) if mode == "Fit" else max(out_w/w, out_h/h)
            scaled_w, scaled_h = int(w * scale), int(h * scale)
            scaled_resized = cv2.resize(source_img, (scaled_w, scaled_h), interpolation=cv2.INTER_AREA)
            
            scaled = np.zeros((out_h, out_w, 3), dtype=np.uint8)
            if mode == "Fit":
                x_off = (out_w - scaled_w) // 2
                y_off = (out_h - scaled_h) // 2
                scaled[y_off:y_off+scaled_h, x_off:x_off+scaled_w] = scaled_resized
            else: # Fill
                cx_off = (scaled_w - out_w) // 2
                cy_off = (scaled_h - out_h) // 2
                scaled = scaled_resized[cy_off:cy_off+out_h, cx_off:cx_off+out_w]

        processed = self.apply_image_adjustments(scaled)
        return cv2.Canny(processed, self.threshold1_slider_var.get(), self.threshold2_slider_var.get())

    def _run_potrace_estimate(self, image_data):
        try:
            command = ['potrace', '-', '-s', '--turdsize', str(self.speckle_removal.get()), '--opttolerance', str(self.optimization_level.get())]
            proc = subprocess.run(command, input=cv2.imencode('.bmp', image_data)[1].tobytes(), capture_output=True, check=True, timeout=1)
            return len(re.findall(b'[MLC]', proc.stdout))
        except Exception:
            return "---"

    def format_time(self, frame_num):
        if self.fps == 0: return "00:00:00:00"
        seconds_total = frame_num / self.fps
        hours, remainder = divmod(seconds_total, 3600)
        minutes, seconds = divmod(remainder, 60)
        frames = int((seconds_total * self.fps) % self.fps)
        return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}:{int(frames):02}"
        
    def parse_time(self, time_str):
        try:
            parts = time_str.split(':')
            if len(parts) == 4:
                h, m, s, f = [int(p) for p in parts]
                total_seconds = (h * 3600) + (m * 60) + s + (f / self.fps)
                return total_seconds
            return -1
        except Exception:
            return -1

    def update_in_out_entries(self):
        self.in_time_entry.delete(0, tk.END)
        self.in_time_entry.insert(0, self.format_time(self.in_frame))
        self.out_time_entry.delete(0, tk.END)
        self.out_time_entry.insert(0, self.format_time(self.out_frame))

    def set_in_point(self):
        self.in_frame = int(self.timeline_slider.get())
        self.update_in_out_entries()
        self.schedule_preview_update()
    
    def set_out_point(self):
        self.out_frame = int(self.timeline_slider.get())
        self.update_in_out_entries()
        self.schedule_preview_update()

    def set_in_from_entry(self, event):
        seconds = self.parse_time(self.in_time_entry.get())
        if seconds != -1:
            self.in_frame = min(max(0, int(seconds * self.fps)), self.total_frames -1)
            self.timeline_slider.set(self.in_frame)
            self.schedule_preview_update()
        self.update_in_out_entries()
        
    def set_out_from_entry(self, event):
        seconds = self.parse_time(self.out_time_entry.get())
        if seconds != -1:
            self.out_frame = min(max(0, int(seconds * self.fps)), self.total_frames -1)
            self.timeline_slider.set(self.out_frame)
            self.schedule_preview_update()
        self.update_in_out_entries()
        
    def choose_stroke_color(self):
        color_code = colorchooser.askcolor(title="Choose SVG stroke color")
        if color_code and color_code[1]:
            self.stroke_color.set(color_code[1])
            self.color_swatch_label.config(bg=self.stroke_color.get())

    def start_conversion(self):
        if not self.video_path or not self.output_path or self.in_frame >= self.out_frame:
            messagebox.showerror("Error", "Please set valid video, output, and in/out points."); return
        self.start_button.config(state="disabled"); self.progress_bar['value'] = 0
        threading.Thread(target=self.run_conversion_logic, daemon=True).start()

    def run_conversion_logic(self):
        video_name = os.path.splitext(os.path.basename(self.video_path))[0]
        final_output_folder = os.path.join(self.output_path, video_name); os.makedirs(final_output_folder, exist_ok=True)
        local_capture = cv2.VideoCapture(self.video_path)
        total_frames_to_process = self.out_frame - self.in_frame + 1
        
        for i, frame_num in enumerate(range(self.in_frame, self.out_frame + 1)):
            self.root.after(0, self.status_label.config, {'text': f"Processing frame {i+1} of {total_frames_to_process}..."})
            local_capture.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
            ret, frame = local_capture.read()
            if not ret: continue

            source_img = frame
            if self.is_crop_enabled.get() and self.crop_coords:
                h, w = frame.shape[:2]
                scale_w = w / self.preview_canvas.winfo_width()
                scale_h = h / self.preview_canvas.winfo_height()
                x1, y1 = self.crop_coords[0] - self.preview_image_offset[0], self.crop_coords[1] - self.preview_image_offset[1]
                x2, y2 = self.crop_coords[2] - self.preview_image_offset[0], self.crop_coords[3] - self.preview_image_offset[1]
                
                frame_x1, frame_y1 = int(x1 * scale_w), int(y1 * scale_h)
                frame_x2, frame_y2 = int(x2 * scale_w), int(y2 * scale_h)

                if frame_x2 > frame_x1 and frame_y2 > frame_y1:
                    source_img = frame[frame_y1:frame_y2, frame_x1:frame_x2]
            else:
                 source_img = self.apply_pan_and_zoom(source_img)
                 
            if self.is_1_to_1_aspect.get():
                h, w = source_img.shape[:2]
                side = min(h, w); x_off = (w - side) // 2; y_off = (h - side) // 2
                source_img = source_img[y_off:y_off+side, x_off:x_off+side]

            processed = self.apply_image_adjustments(source_img)
            if self.is_multipass.get():
                edges = cv2.Canny(processed, self.threshold1_slider_var.get(), self.threshold2_slider_var.get())
                skeleton = cv2.ximgproc.thinning(edges)
                processed = skeleton
            
            edges_inverted = cv2.bitwise_not(cv2.Canny(processed, self.threshold1_slider_var.get(), self.threshold2_slider_var.get()))
            temp_bmp_path = os.path.join(final_output_folder, "temp_frame.bmp")
            cv2.imwrite(temp_bmp_path, edges_inverted)
            
            svg_filename = f"{i+1:05d}.svg"; svg_filepath = os.path.join(final_output_folder, svg_filename)
            try:
                command = ['potrace', temp_bmp_path, '-s', '--turdsize', str(self.speckle_removal.get()), '--opttolerance', str(self.optimization_level.get()), '--alphamax', str(self.corner_smoothing.get()), '-o', svg_filepath]
                subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                self.colorize_svg_file(svg_filepath, self.stroke_color.get())
            except Exception as e:
                self.root.after(0, self.handle_conversion_error, str(e)); break
            finally:
                if os.path.exists(temp_bmp_path): os.remove(temp_bmp_path)
            self.root.after(0, self.progress_bar.config, {'value': (i + 1) / total_frames_to_process * 100})
        
        local_capture.release()
        self.root.after(0, self.handle_conversion_complete, final_output_folder)

    def colorize_svg_file(self, filepath, color_hex):
        try:
            with open(filepath, 'r') as f: content = f.read()
            content = re.sub(r'<path', f'<path stroke="{color_hex}" fill="none"', content)
            with open(filepath, 'w') as f: f.write(content)
        except Exception as e:
            print(f"Could not colorize SVG {filepath}: {e}")

    def handle_conversion_complete(self, output_folder):
        self.status_label.config(text=f"Success! Files saved to: {output_folder}")
        self.start_button.config(state="normal")
        messagebox.showinfo("Complete", f"Conversion successful.\nFiles saved to:\n{output_folder}")

    def handle_conversion_error(self, error_message):
        self.status_label.config(text="Error during conversion.")
        self.start_button.config(state="normal")
        messagebox.showerror("Conversion Error", f"An error occurred: {error_message}")

if __name__ == "__main__":
    root = tk.Tk()
    app = VideoToSVGConverter(root)
    root.mainloop()
