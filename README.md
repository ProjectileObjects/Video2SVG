Video to SVG Converter v2

An advanced desktop application for macOS that converts video files into a sequence of optimized SVG (Scalable Vector Graphics) frames, designed specifically for laser projection and other vector-based art.

The application uses OpenCV for video processing, the Canny edge detection algorithm to find edges, and the Potrace command-line utility to convert the resulting edge-detected images into clean, scalable vector format.

Features

- Advanced Framing Tools:
  - Interactive Crop: Draw a precise box on the input preview to select a specific region.
  - Digital Pan & Zoom: Pan and zoom into the source video to frame your shot perfectly, an alternative to cropping.
- Live Previews:
  - Input Preview: A real-time preview of the edge detection effect on the full input frame.
  - Output Preview: A dedicated "what you see is what you get" preview that shows exactly how your final cropped, scaled, and aspect-ratio-adjusted image will look.
- Precise Timeline Control:
  - Scrub through the video with a timeline slider.
  - Set "In" and "Out" points using buttons or by typing in HH:MM:SS:FF timecodes.
  - A visual indicator bar shows your selected range on the timeline.
- Comprehensive Image Adjustments:
  - Fine-tune the look with sliders for Brightness, Contrast, Pre-Blur, and Canny Edge Thresholds.
  - Numerical feedback next to each slider shows the exact current value.
- Powerful Laser Optimization (Potrace Controls):
  - Speckle Removal: Eliminates small, noisy vector paths.
  - Curve Smoothing: Simplifies curves for more fluid laser movement.
  - Corner Smoothing: Rounds sharp corners to reduce burning and mechanical stress.
  - Centerline Tracing (Multi-Pass): A sophisticated option that uses a skeletonization algorithm to convert thick or double lines into a single, clean path.
  - Help icons (?) explain what each optimization setting does.
- Output Control:
  - Choose the output folder. Files are automatically saved into a subfolder named after the video.
  - Select stroke color for the final SVG lines.
  - Force a 1:1 square aspect ratio.
  - Choose scaling options (Fit, Fill, Stretch) for how the source image fits into the final output dimensions.

Requirements

To run this application, you will need:

- A computer running macOS.
- Python 3 installed.
- Homebrew package manager installed.

Installation

Follow these steps in your Terminal to set up the application and its dependencies.

1. Install Potrace

The core vectorization engine is a command-line tool called potrace. Install it using Homebrew:

    brew install potrace

2. Install Python Libraries

The script depends on several Python libraries for the GUI, image processing, and advanced algorithms. Install them using pip3.

Important: The opencv-contrib-python package is required for the "Multi-Pass (Centerline)" feature.

    pip3 install opencv-contrib-python Pillow

- opencv-contrib-python: Used for reading/processing video frames and for the skeletonization algorithm (ximgproc).
- Pillow: Used by the GUI framework (Tkinter) to display images.

3. Download the Application Script

Save the Python code for the application into a file, for example video_converter_app.py.

How to Run

Once all dependencies are installed and the script is downloaded, you can run the application from your Terminal.

1. Navigate to the directory where you saved the application script.
2. Run the following command:
       python3 Video2SVGv2.py

The application window should now appear on your screen.

How to Use the Application

1. Select Files: Use the "Select Video" and "Select Output" buttons to get started.
2. Set Range: Use the timeline slider and the "Set In" / "Set Out" buttons (or i/o keys) to define the segment you want to convert. You can also type HH:MM:SS:FF values directly into the text boxes and press Enter.
3. Frame Your Shot:
   - To Crop: Check the "Crop" box and draw a rectangle on the Input Window. The Output Preview will update to show the result of this crop.
   - To Pan/Zoom: Uncheck the "Crop" box. Use the "Zoom", "X Offset", and "Y Offset" sliders to digitally frame your shot. The Output Preview will show the result.
   - Use the "1:1" and "Fit/Fill/Stretch" options to control the final output dimensions.
4. Adjust Image: Use the sliders under "Image Adjustments" to change the brightness, contrast, blur, and edge detection thresholds. The Input Window will update in real-time.
5. Optimize for Laser: Use the sliders and checkboxes under "Laser Optimization" to control the final vector output. Remember, these settings do not change the previews; they are only applied during the final conversion.
6. Convert: Click the "Start Conversion" button. The progress bar will show the status, and a confirmation will appear when the process is complete.
