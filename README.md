# Manim Video Generator - Setup Instructions

## Requirements

Create a `requirements.txt` file:

```txt
Flask
Flask-Cors
manim
numpy
Pillow
```

## Installation Steps

1. **Install Python 3.8+** (if not already installed)

2. **Install system dependencies** (varies by OS):

   **Ubuntu/Debian:**
   ```bash
   sudo apt update
   sudo apt install python3-pip python3-venv ffmpeg
   sudo apt install build-essential python3-dev libcairo2-dev libpango1.0-dev
   ```

   **macOS (with Homebrew):**
   ```bash
   brew install python3 ffmpeg cairo pango
   ```

   **Windows:**
   - Install Python from python.org
   - Install FFmpeg and add to PATH
   - Install Microsoft C++ Build Tools

3. **Set up virtual environment:**
   ```bash
   python3 -m venv manim_env
   source manim_env/bin/activate  # On Windows: manim_env\Scripts\activate
   ```

4. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

5. **Test Manim installation:**
   ```bash
   manim --version
   ```

## Running the Application

1. **Start the Flask server:**
   ```bash
   python app.py
   ```

2. **Access the application:**
   Open your web browser and go to `http://localhost:5000`

## Usage

1. Enter your micro-instructions in the textarea (one per line)
2. Format: `1. PCout, MARin, Read, Select4, Add, Zin`
3. Click "Generate Video"
4. Wait for processing (may take 1-2 minutes)
5. Video will automatically download when ready

## Supported Micro-instructions

The system recognizes these control signals:
- `PCout`, `PCin` - Program Counter
- `MARin` - Memory Address Register
- `MDRout` - Memory Data Register  
- `IRin` - Instruction Register
- `Yin` - Y Register
- `Zout`, `Zin` - Z Register
- `R1out`, `R1in`, `R2out`, `R2in` - General Purpose Register R1
- `Add`, `Sub` - ALU Operations
- `Select4`, `SelectY` - MUX Selection
- `Read`, `WMFC`, `End` - Control signals

## Troubleshooting

**Video generation fails:**
- Check that FFmpeg is installed and in PATH
- Ensure all Python dependencies are installed
- Check server logs for detailed error messages

**Timeout errors:**
- Complex animations may take longer
- Consider reducing the number of steps
- Check system resources

**Import errors:**
- Make sure virtual environment is activated
- Reinstall requirements: `pip install -r requirements.txt --force-reinstall`

## File Structure

```
project/
├── app.py                 # Flask application
├── requirements.txt       # Python dependencies

```
