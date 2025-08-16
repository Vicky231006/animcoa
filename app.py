from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import tempfile
import os
import subprocess
import json
import re
from pathlib import Path
import shutil

app = Flask(__name__)
CORS(app)

def parse_microinstructions(input_text):
    """Parse the input microinstructions into a list of steps"""
    lines = input_text.strip().split('\n')
    steps = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Remove step numbers (e.g., "1.", "T1:", etc.)
        line = re.sub(r'^\d+\.?\s*', '', line)
        line = re.sub(r'^T\d+:\s*', '', line)
        
        if line:
            steps.append(line)
    
    return steps

@app.route('/')
def index():
    return '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Micro-instruction to Video Simulator</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
        <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🎬</text></svg>">
        <style>
            body {
                font-family: 'Inter', sans-serif;
            }
            .loader {
                border-top-color: #3498db;
                animation: spin 1s linear infinite;
            }
            @keyframes spin {
                to { transform: rotate(360deg); }
            }
        </style>
    </head>
    <body class="bg-gray-900 text-white flex items-center justify-center min-h-screen">

        <div id="main-content" class="w-full max-w-2xl p-8 space-y-6 bg-gray-800 rounded-xl shadow-lg">
            <div>
                <h1 class="text-3xl font-bold text-center text-cyan-400">Micro-instruction to Video Simulator</h1>
                <p class="text-center text-gray-400 mt-2">Enter processor micro-instructions (one step per line) to generate a simulation video.</p>
            </div>
            <form id="manim-form">
                <div class="space-y-4">
                    <label for="manim-code" class="block text-sm font-medium text-gray-300">Micro-instructions</label>
                    <textarea id="manim-code" name="code" rows="15" class="w-full p-3 bg-gray-900 border border-gray-700 rounded-md text-gray-200 focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500 transition" required>1. PCout, MARin, Read, Select4, Add, Zin
2. Zout, PCin, Yin, WMFC
3. MDRout, IRin
4. R1out, Select4, Sub, Zin
5. Zout, R1in, End</textarea>
                </div>
                <button type="submit" class="w-full bg-cyan-600 hover:bg-cyan-700 text-white font-bold py-3 px-4 rounded-md transition duration-300 ease-in-out transform hover:scale-105 mt-6">
                    Generate Video
                </button>
            </form>
        </div>

        <div id="loading-overlay" class="fixed inset-0 bg-gray-900 bg-opacity-80 flex-col items-center justify-center hidden z-50">
            <div class="loader ease-linear rounded-full border-8 border-t-8 border-gray-200 h-24 w-24 mb-4"></div>
            <h2 class="text-center text-white text-xl font-semibold">Generating Video...</h2>
            <p class="w-1/3 text-center text-white mt-2">Please wait, this might take a moment. The little hamsters are running as fast as they can!</p>
        </div>

        <script>
            document.getElementById('manim-form').addEventListener('submit', async function(event) {
                event.preventDefault();

                const manimCode = document.getElementById('manim-code').value;
                const loadingOverlay = document.getElementById('loading-overlay');
                
                loadingOverlay.classList.remove('hidden');
                loadingOverlay.classList.add('flex');

                try {
                    const response = await fetch('/generate_video', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ code: manimCode }),
                    });

                    if (response.ok) {
                        const blob = await response.blob();
                        const url = window.URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.style.display = 'none';
                        a.href = url;
                        const contentDisposition = response.headers.get('Content-Disposition');
                        let filename = 'processor_simulation.mp4';
                        if (contentDisposition && contentDisposition.includes('filename=')) {
                            const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
                            if (filenameMatch && filenameMatch.length > 1) {
                                filename = filenameMatch[1];
                            }
                        }
                        a.download = filename;
                        document.body.appendChild(a);
                        a.click();
                        window.URL.revokeObjectURL(url);
                        document.body.removeChild(a);
                        alert('Video downloaded successfully!');
                    } else {
                        let errorMessage = 'An error occurred while generating the video.';
                        try {
                            const error = await response.json();
                            errorMessage = `Error: ${error.error}`;
                            if (error.details) {
                                errorMessage += `\\n\\nDetails: ${error.details}`;
                            }
                        } catch (e) {
                            errorMessage = `Server returned status ${response.status}: ${response.statusText}`;
                        }
                        alert(errorMessage);
                    }
                } catch (error) {
                    console.error('An error occurred:', error);
                    alert('An unexpected error occurred. Please check your network connection and try again.');
                } finally {
                    loadingOverlay.classList.add('hidden');
                    loadingOverlay.classList.remove('flex');
                }
            });
        </script>
    </body>
    </html>
    '''

@app.route('/favicon.ico')
def favicon():
    return '', 204

@app.route('/generate_video', methods=['POST'])
def generate_video():
    try:
        data = request.get_json()
        if not data or 'code' not in data:
            return jsonify({'error': 'No microinstructions provided'}), 400
        
        microinstructions = data['code']
        steps = parse_microinstructions(microinstructions)
        
        if not steps:
            return jsonify({'error': 'No valid microinstructions found'}), 400
        
        # Create temporary directory for video generation
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)
            
            # Create the manim script file with the complete class definition
            script_content = f"""from manim import *
import numpy as np

class ProcessorDataFlow(Scene):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.steps = {repr(steps)}

    def construct(self):
        # ========= Setup Colors and Components =========
        self.setup_colors_and_components()
        
        # ========= Draw Initial Diagram =========
        title = Text("Single-Bus Processor Animation", font_size=40, gradient=(BLUE, GREEN)).to_edge(UP, buff=0.5)
        self.play(Write(title, run_time=1.5), rate_func=smooth)
        self.play(FadeOut(title, run_time=0.5))
        
        self.play(Create(self.diagram), run_time=3)
        self.wait(1)

        # ========= Dynamic Animation Sequence Based on Input Steps =========
        step_text = Text("", font_size=24, color=WHITE).to_edge(DOWN, buff=0.5)
        self.add(step_text)
        
        for i, step in enumerate(self.steps):
            step_num = f"T{{i+1}}"
            step_display = f"{{step_num}}: {{step}}"
            
            self.play(step_text.animate.become(Text(step_display, font_size=18, color=WHITE).to_edge(DOWN, buff=0.5)))
            self.wait(0.5)
            
            self.execute_step_animations(step)
        
        # ========= Celebration Ending =========
        self.play(step_text.animate.become(Text("🎉 INSTRUCTION COMPLETE! 🎉", font_size=32, color=self.SUCCESS_GREEN, weight=BOLD).to_edge(DOWN, buff=0.5)))
        self.play(Flash(self.diagram, color=self.SUCCESS_GREEN, flash_radius=2), run_time=2)
        self.wait(3)

    def setup_colors_and_components(self):
        # ========= Colors =========
        self.LASER_RED = "#FF6B6B"
        self.DATA_BLUE = "#4ECDC4"
        self.CTRL_COLOR = "#FFE66D"
        self.WIRE = "#95A5A6"
        self.BOX_STROKE = "#34495E"
        self.IR_STROKE = "#3498DB"
        self.LABEL = WHITE
        self.BUS_COLOR = "#E74C3C"
        self.SUCCESS_GREEN = "#2ECC71"
        self.HIGHLIGHT_PURPLE = "#9B59B6"
        self.DARK_GREEN_FILL = "#27AE60"
        self.DARK_BLUE_FILL = "#2980B9"
        self.PURPLE_FILL = "#8E44AD"
        self.ORANGE_FILL = "#E67E22"
        self.RED_FILL = "#E74C3C"
        self.YELLOW_FILL = "#F1C40F"
        self.TEAL_FILL = "#1ABC9C"
        self.MAROON_FILL = "#8B4513"
        
        # ========= Bus =========
        bus = Line(UP*2.5, DOWN*3.9, color=self.BUS_COLOR, stroke_width=10)
        bus_glow = Line(UP*2.5, DOWN*3.9, color=self.BUS_COLOR, stroke_width=18, stroke_opacity=0.3)
        self.bus_group = VGroup(bus_glow, bus)

        def project_to_bus(point):
            bus_x = bus.get_center()[0]
            return np.array([bus_x, point[1], 0.0])
        self.project_to_bus = project_to_bus

        # ========= Components =========
        h_pos_left = LEFT * 3.8
        h_pos_right = RIGHT * 3.8
        
        mar_rect = RoundedRectangle(width=2.2, height=1.0, corner_radius=0.15, color=self.BOX_STROKE, fill_color=self.DARK_BLUE_FILL, fill_opacity=0.3).move_to(h_pos_left + UP * 2.2)
        mar_lbl = Text("MAR\\n(Memory Address)", color=self.LABEL, font_size=16, line_spacing=0.8).move_to(mar_rect.get_center())
        self.mar_group = VGroup(mar_rect, mar_lbl)

        mdr_rect = RoundedRectangle(width=2.2, height=1.0, corner_radius=0.15, color=self.BOX_STROKE, fill_color=self.DARK_BLUE_FILL, fill_opacity=0.3).next_to(mar_rect, DOWN, buff=0.3)
        mdr_lbl = Text("MDR\\n(Memory Data)", color=self.LABEL, font_size=16, line_spacing=0.8).move_to(mdr_rect.get_center())
        self.mdr_group = VGroup(mdr_rect, mdr_lbl)

        const4_rect = RoundedRectangle(width=1.0, height=0.8, corner_radius=0.1, color=self.BOX_STROKE, fill_color=self.DARK_GREEN_FILL, fill_opacity=0.4).next_to(mdr_rect, DOWN, buff=0.4).shift(LEFT*0.5)
        const4_lbl = Text("4\\n(Const)", font_size=14, color=WHITE, line_spacing=0.8).move_to(const4_rect.get_center())
        self.const4_group = VGroup(const4_rect, const4_lbl)

        y_rect = RoundedRectangle(width=1.0, height=0.8, corner_radius=0.1, color=self.BOX_STROKE, fill_color=self.PURPLE_FILL, fill_opacity=0.4).next_to(const4_rect, RIGHT, buff=0.2)
        y_lbl = Text("Y\\n(Temp)", color=self.LABEL, font_size=14, line_spacing=0.8).move_to(y_rect.get_center())
        self.y_group = VGroup(y_rect, y_lbl)

        mux_vertices = [LEFT*1.2, RIGHT*1.2, RIGHT*0.8+DOWN*0.8, LEFT*0.8+DOWN*0.8]
        mux_poly = Polygon(*mux_vertices, color=self.BOX_STROKE, fill_color=self.ORANGE_FILL, fill_opacity=0.3).next_to(VGroup(y_rect, const4_rect), DOWN, buff=0.2)
        mux_lbl = Text("MUX", color=BLACK, font_size=18, weight=BOLD).move_to(mux_poly.get_center())
        self.mux_group = VGroup(mux_poly, mux_lbl)

        alu_vertices = [LEFT*1.4, RIGHT*1.4, RIGHT*1.0+DOWN*1.0, LEFT*1.0+DOWN*1.0]
        alu_poly = Polygon(*alu_vertices, color=self.BOX_STROKE, fill_color=self.RED_FILL, fill_opacity=0.4).next_to(mux_poly, DOWN, buff=0.25)
        alu_lbl = Text("ALU", color=WHITE, font_size=18, weight=BOLD).move_to(alu_poly.get_center())
        self.alu_group = VGroup(alu_poly, alu_lbl)

        z_rect = RoundedRectangle(width=2.2, height=1.0, corner_radius=0.15, color=self.BOX_STROKE, fill_color=self.DARK_BLUE_FILL, fill_opacity=0.3).next_to(alu_poly, DOWN, buff=0.15)
        z_lbl = Text("Z\\n(Result)", color=self.LABEL, font_size=16, line_spacing=0.8).move_to(z_rect.get_center())
        self.z_group = VGroup(z_rect, z_lbl)

        ctrl_rect = RoundedRectangle(width=2.8, height=1.6, corner_radius=0.15, color=self.BOX_STROKE, fill_color=self.YELLOW_FILL, fill_opacity=0.2).move_to(h_pos_right + UP*2.2)
        ctrl_lbl = Text("Control Unit\\n🧠\\n(The Brain)", font_size=18, color=BLACK, weight=BOLD, line_spacing=0.8).move_to(ctrl_rect.get_center())
        self.ctrl_group = VGroup(ctrl_rect, ctrl_lbl)

        ir_rect = RoundedRectangle(width=2.2, height=1.0, corner_radius=0.15, color=self.IR_STROKE, fill_color=self.TEAL_FILL, fill_opacity=0.3)
        ir_lbl = Text("IR\\n(Instruction)", color=WHITE, font_size=16, line_spacing=0.8).move_to(ir_rect.get_center())
        self.ir_group = VGroup(ir_rect, ir_lbl)

        pc_rect = RoundedRectangle(width=2.2, height=1.0, corner_radius=0.15, color=self.BOX_STROKE, fill_color=self.DARK_BLUE_FILL, fill_opacity=0.3)
        pc_lbl = Text("PC\\n(Counter)", color=self.LABEL, font_size=16, line_spacing=0.8).move_to(pc_rect.get_center())
        self.pc_group = VGroup(pc_rect, pc_lbl)

        gpr_rect = RoundedRectangle(width=2.2, height=1.4, corner_radius=0.15, color=self.BOX_STROKE, fill_color=self.MAROON_FILL, fill_opacity=0.3)
        gpr_lbls = VGroup(Text("R1 📦", font_size=16), Text("...", font_size=14), Text("R2 📦", font_size=16)).arrange(DOWN, buff=0.08).move_to(gpr_rect.get_center())
        self.gpr_group = VGroup(gpr_rect, gpr_lbls)
        
        right_stack = VGroup(self.ir_group, self.pc_group, self.gpr_group).arrange(DOWN, buff=0.3)
        right_stack.next_to(self.ctrl_group, DOWN, buff=0.6).align_to(self.ctrl_group, RIGHT)
        
        # ========= Wiring =========
        select_arrow = CurvedArrow(self.mux_group.get_left() + LEFT*1.2, self.mux_group.get_left(), color=self.CTRL_COLOR, stroke_width=3)
        select_lbl = Text("Select 🎛️", font_size=16, color=self.CTRL_COLOR).next_to(select_arrow, LEFT, buff=0.1)
        self.main_control_line = Line(ctrl_rect.get_left(), self.project_to_bus(ctrl_rect.get_left()), color=self.CTRL_COLOR, stroke_width=3)
        ir_to_ctrl_line = CurvedArrow(ir_rect.get_top(), ctrl_rect.get_bottom(), color=self.IR_STROKE, stroke_width=3)

        connectors = VGroup(
            Line(mar_rect.get_edge_center(RIGHT), self.project_to_bus(mar_rect.get_edge_center(RIGHT)), color=self.WIRE, stroke_width=2),
            Line(mdr_rect.get_edge_center(RIGHT), self.project_to_bus(mdr_rect.get_edge_center(RIGHT)), color=self.WIRE, stroke_width=2),
            Line(y_rect.get_edge_center(RIGHT), self.project_to_bus(y_rect.get_edge_center(RIGHT)), color=self.WIRE, stroke_width=2),
            Line(z_rect.get_edge_center(RIGHT), self.project_to_bus(z_rect.get_edge_center(RIGHT)), color=self.WIRE, stroke_width=2),
            Line(pc_rect.get_edge_center(LEFT), self.project_to_bus(pc_rect.get_edge_center(LEFT)), color=self.WIRE, stroke_width=2),
            Line(ir_rect.get_edge_center(LEFT), self.project_to_bus(ir_rect.get_edge_center(LEFT)), color=self.WIRE, stroke_width=2),
            Line(gpr_rect.get_edge_center(LEFT), self.project_to_bus(gpr_rect.get_edge_center(LEFT)), color=self.WIRE, stroke_width=2),
            Line(alu_poly.get_edge_center(RIGHT), self.project_to_bus(alu_poly.get_edge_center(RIGHT)), color=self.WIRE, stroke_width=2),
            Line(const4_rect.get_bottom(), mux_poly.get_top() + LEFT*0.4, color=self.WIRE, stroke_width=2),
            Line(y_rect.get_bottom(), mux_poly.get_top() + RIGHT*0.4, color=self.WIRE, stroke_width=2),
            Line(mux_poly.get_bottom(), alu_poly.get_top(), color=self.WIRE, stroke_width=2),
            Line(alu_poly.get_bottom(), z_rect.get_top(), color=self.WIRE, stroke_width=2),
            ir_to_ctrl_line, self.main_control_line
        )

        self.signal_map = {{
            "PCout": self.pc_group, "PCin": self.pc_group, "MARin": self.mar_group,
            "MDRout": self.mdr_group, "IRin": self.ir_group, "Yin": self.y_group,
            "Zout": self.z_group, "Zin": self.z_group, "R1out": self.gpr_group,
            "R1in": self.gpr_group, "Add": self.alu_group, "Sub": self.alu_group,
            "R2out": self.gpr_group, "R2in": self.gpr_group, "End": self.ctrl_group,
            "Select4": VGroup(select_arrow, select_lbl, self.const4_group),
            "SelectY": VGroup(select_arrow, select_lbl, self.y_group)
        }}

        self.diagram = VGroup(
            self.mar_group, self.mdr_group, self.pc_group, self.ir_group, self.gpr_group,
            self.y_group, self.z_group, self.alu_group, self.mux_group, self.ctrl_group, self.const4_group,
            self.bus_group, connectors, select_arrow, select_lbl
        )
        self.diagram.shift(UP * 0.7)

    def animate_control_signal(self, signal_name, description=""):
        if signal_name not in self.signal_map: return
        signal_group = self.signal_map[signal_name]
        control_flash = AnimationGroup(
            ShowPassingFlash(self.main_control_line.copy().set_color(self.CTRL_COLOR), time_width=0.6, run_time=1),
            Flash(self.ctrl_group, color=self.CTRL_COLOR, flash_radius=0.5),
            Indicate(signal_group, color=self.CTRL_COLOR, scale_factor=1.2),
            run_time=1.5
        )
        if description:
            desc_text = Text(description, font_size=20, color=self.CTRL_COLOR).next_to(signal_group, UP, buff=0.3)
            self.play(control_flash, FadeIn(desc_text), run_time=1.5)
            self.play(FadeOut(desc_text), run_time=0.5)
        else:
            self.play(control_flash)

    def animate_bus_transfer(self, src_group, dst_group, data_label, signals, color=None):
        if color is None: color = self.DATA_BLUE
        self.animate_control_signal(signals[0], f"Activate {{signals[0]}}")
        src_center, dst_center = src_group.get_center(), dst_group.get_center()
        src_anchor = src_center + (RIGHT if src_center[0] < 0 else LEFT) * (src_group[0].width/2 + 0.1)
        dst_anchor = dst_center + (RIGHT if dst_center[0] < 0 else LEFT) * (dst_group[0].width/2 + 0.1)
        path = VMobject(color=color, stroke_width=8)
        path.set_points_as_corners([src_anchor, self.project_to_bus(src_anchor), self.project_to_bus(dst_anchor), dst_anchor])
        
        emoji_map = {{"Addr": "📍", "PC+4": "➡️", "Instruction": "📝", "R1": "📦", "R1": "📦", "4": "4️⃣"}}
        emoji = emoji_map.get(data_label, "💾")
        lbl = Text(f"{{emoji}} {{data_label}}", font_size=20, color=color, weight=BOLD)
        lbl_bg = RoundedRectangle(width=lbl.width + 0.3, height=lbl.height + 0.15, corner_radius=0.08, color=color, fill_color=BLACK, fill_opacity=0.8, stroke_width=2)
        moving_lbl = VGroup(lbl_bg, lbl).move_to(src_anchor + UP*0.5)
        
        self.play(FadeIn(moving_lbl, scale=0.5), src_group.animate.set_color(color), run_time=0.8)
        self.play(ShowPassingFlash(path, time_width=0.5, run_time=1.5), moving_lbl.animate.move_to(dst_anchor + UP*0.5), run_time=1.5)
        self.animate_control_signal(signals[1], f"Store in {{signals[1]}}")
        self.play(dst_group.animate.set_color(color), run_time=1)
        self.play(FadeOut(moving_lbl), src_group.animate.set_color(self.BOX_STROKE), dst_group.animate.set_color(self.BOX_STROKE), run_time=0.8)

    def animate_alu_op(self, op_signals, data_from_bus_group, use_const4=False, operation=""):
        if operation:
            op_text = Text(f"🧮 {{operation}}", font_size=20, color=self.LASER_RED).next_to(self.alu_group, UP, buff=0.2)
            self.play(Write(op_text))
        
        for i, sig in enumerate(op_signals):
            self.animate_control_signal(sig, f"Output from {{sig}}" if i == 0 else None)
        
        bus_anchor = (data_from_bus_group.get_left() if data_from_bus_group.get_center()[0] > 0 else data_from_bus_group.get_right())
        alu_bus_in = self.alu_group[0].get_right()
        path_to_alu = VMobject(color=self.LASER_RED, stroke_width=8).set_points_as_corners([bus_anchor, self.project_to_bus(bus_anchor), self.project_to_bus(alu_bus_in), alu_bus_in])
        self.play(ShowPassingFlash(path_to_alu, time_width=0.5), data_from_bus_group.animate.set_color(self.LASER_RED), run_time=1.5)
        
        if use_const4:
            selected_input, mux_input_path, select_text = self.const4_group, Line(self.const4_group[0].get_bottom(), self.mux_group[0].get_top() + LEFT*0.4, color=self.HIGHLIGHT_PURPLE, stroke_width=6), "Using Constant 4 4️⃣"
        else:
            selected_input, mux_input_path, select_text = self.y_group, Line(self.y_group[0].get_bottom(), self.mux_group[0].get_top() + RIGHT*0.5, color=self.HIGHLIGHT_PURPLE, stroke_width=6), "Using Y Register 📦"
        
        select_indicator = Text(select_text, font_size=18, color=self.HIGHLIGHT_PURPLE).next_to(self.mux_group, LEFT, buff=0.3)
        self.play(ShowPassingFlash(mux_input_path, time_width=0.5), selected_input.animate.set_color(self.HIGHLIGHT_PURPLE), Write(select_indicator), run_time=1.5)
        path_mux_alu = VMobject(color=self.HIGHLIGHT_PURPLE, stroke_width=6).set_points_as_corners([self.mux_group[0].get_bottom(), self.alu_group[0].get_top()])
        self.play(ShowPassingFlash(path_mux_alu, time_width=0.5), self.mux_group.animate.set_color(self.HIGHLIGHT_PURPLE), run_time=1.5)
        self.play(self.alu_group.animate.set_color(self.LASER_RED), Flash(self.alu_group, color=self.LASER_RED, flash_radius=1), rate_func=there_and_back, run_time=1.5)
        path_alu_z = Line(self.alu_group[0].get_bottom(), self.z_group[0].get_top(), color=self.SUCCESS_GREEN, stroke_width=6)
        result_text = Text("✨ Result Ready!", font_size=18, color=self.SUCCESS_GREEN).next_to(self.z_group, DOWN, buff=0.2)
        self.play(ShowPassingFlash(path_alu_z, time_width=0.5), Write(result_text), self.z_group.animate.set_color(self.SUCCESS_GREEN), run_time=1.5)
        
        cleanup_group = VGroup(select_indicator, result_text)
        if operation:
            cleanup_group.add(op_text)
        self.play(FadeOut(cleanup_group), *[group.animate.set_color(self.BOX_STROKE) for group in [data_from_bus_group, selected_input, self.mux_group, self.alu_group, self.z_group]], run_time=1)

    def execute_step_animations(self, step):
        step_lower = step.lower()
        
        # Step 1 logic: PCout, MARin, Read, Select4, Add, Zin
        if "pcout" in step_lower and "marin" in step_lower:
            self.animate_bus_transfer(self.pc_group, self.mar_group, "Addr", signals=["PCout", "MARin"], color=BLUE)
        if "select4" in step_lower and "add" in step_lower and "zin" in step_lower:
            self.animate_alu_op(op_signals=["PCout", "Select4", "Add", "Zin"], data_from_bus_group=self.pc_group, use_const4=True, operation="PC + 4")
        
        # Step 2 logic: Zout, PCin, Yin, WMFC
        if "zout" in step_lower and "pcin" in step_lower:
            self.animate_bus_transfer(self.z_group, self.pc_group, "PC+4", signals=["Zout", "PCin"], color=GREEN)
        if "zout" in step_lower and "yin" in step_lower:
            self.animate_bus_transfer(self.z_group, self.y_group, "PC+4", signals=["Zout", "Yin"], color=PURPLE)
        
        # Step 3 logic: MDRout, IRin
        if "mdrout" in step_lower and "irin" in step_lower:
            memory_ready = Text("Memory Ready!", font_size=18, color=self.SUCCESS_GREEN).next_to(self.mdr_group, LEFT, buff=0.3)
            self.play(self.mdr_group.animate.set_color(self.SUCCESS_GREEN), Write(memory_ready), run_time=1)
            self.play(FadeOut(memory_ready), self.mdr_group.animate.set_color(self.BOX_STROKE))
            self.animate_bus_transfer(self.mdr_group, self.ir_group, "Instruction", signals=["MDRout", "IRin"], color=TEAL)
            
            decode_text = Text("🧠 DECODING...", color=self.CTRL_COLOR, font_size=24, weight=BOLD).next_to(self.ir_group, UP, buff=0.3)
            self.play(Indicate(self.ir_group, color=self.IR_STROKE, scale_factor=0.9), run_time=1)
            self.play(Write(decode_text), run_time=1.5)
            self.play(Flash(self.ir_group, color=self.CTRL_COLOR, flash_radius=1), run_time=1)
            
            decoded_text = Text("✅ Decoded", font_size=22, color=self.SUCCESS_GREEN, weight=BOLD).move_to(decode_text)
            self.play(ReplacementTransform(decode_text, decoded_text))
            self.wait(1.5)
            self.play(FadeOut(decoded_text))
        
        # Step 4 logic: R1out, Select4, Sub, Zin
        if "r1out" in step_lower and "sub" in step_lower:
            self.animate_alu_op(op_signals=["R1out", "Select4", "Sub", "Zin"], data_from_bus_group=self.gpr_group, use_const4=True, operation="R1 - 4")
        
        # Step 5 logic: Zout, R1in, End
        if "zout" in step_lower and "r1in" in step_lower:
            self.animate_bus_transfer(self.z_group, self.gpr_group, "R1in", signals=["Zout", "R1in"], color=self.SUCCESS_GREEN)
            self.play(Indicate(self.gpr_group, color=self.SUCCESS_GREEN, scale_factor=1.3), Flash(self.gpr_group, color=self.SUCCESS_GREEN), run_time=1.5)
        if "r2out" in step_lower and "r1in" in step_lower:
            self.animate_bus_transfer(self.gpr_group, self.gpr_group, "R2 value", signals=["R2out", "R1in"], color=self.DATA_BLUE)
            self.play(Indicate(self.gpr_group, color=self.SUCCESS_GREEN, scale_factor=1.3), run_time=1.5)
        if "r2out" in step_lower and "selecty" in step_lower and "add" in step_lower:
            self.animate_alu_op(op_signals=["R2out", "SelectY", "Add", "Zin"], data_from_bus_group=self.gpr_group, use_const4=False, operation="R2 + Y")

        # UPDATED: General purpose Zout, can go to PC, Y, or R1
        if "zout" in step_lower and "yin" in step_lower:
            self.animate_bus_transfer(self.z_group, self.y_group, "PC+4", signals=["Zout", "Yin"], color=PURPLE)
        if "r1out" in step_lower and "yin" in step_lower:
            self.animate_bus_transfer(self.gpr_group, self.y_group, "R1 value", signals=["R1out", "Yin"], color=PURPLE)


        # UPDATED: More generic label for storing ALU result
        if "zout" in step_lower and "r1in" in step_lower:
            self.animate_bus_transfer(self.z_group, self.gpr_group, "ALU Result", signals=["Zout", "R1in"], color=self.SUCCESS_GREEN)
            self.play(Indicate(self.gpr_group, color=self.SUCCESS_GREEN, scale_factor=1.3), Flash(self.gpr_group, color=self.SUCCESS_GREEN), run_time=1.5)

""" 
            
            script_path = temp_dir_path / "processor_simulation.py"
            with open(script_path, 'w') as f:
                f.write(script_content)
            
            # Run manim to generate the video
            cmd = [
                "manim", 
                str(script_path),
                "ProcessorDataFlow",
                "-ql",  # Low quality for faster processing
                "--disable_caching"
            ]
            
            print(f"Running command: {' '.join(cmd)}")
            
            try:
                result = subprocess.run(
                    cmd, 
                    capture_output=True, 
                    text=True, 
                    cwd=temp_dir,
                    timeout=180  # 3 minute timeout
                )
                
                print(f"Return code: {result.returncode}")
                print(f"Stdout: {result.stdout}")
                print(f"Stderr: {result.stderr}")
                
                if result.returncode != 0:
                    return jsonify({
                        'error': 'Manim execution failed',
                        'details': f"Command: {' '.join(cmd)}\\nReturn code: {result.returncode}\\nStderr: {result.stderr}"
                    }), 500
                
                # Find the generated video file
                video_files = list(temp_dir_path.rglob("*.mp4"))
                print(f"Found video files: {video_files}")
                
                if not video_files:
                    all_files = list(temp_dir_path.rglob("*"))
                    return jsonify({
                        'error': 'Video file not found after generation',
                        'details': f"All files in directory: {all_files}\\nStderr: {result.stderr}"
                    }), 500
                
                video_file = video_files[0]
                print(f"Using video file: {video_file}")
                
                # Send the video file
                return send_file(
                    video_file,
                    as_attachment=True,
                    download_name="processor_simulation.mp4",
                    mimetype='video/mp4'
                )
                
            except subprocess.TimeoutExpired:
                return jsonify({
                    'error': 'Video generation timed out',
                    'details': 'The video generation process took too long and was terminated. Try with simpler instructions.'
                }), 500
            
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error: {error_details}")
        return jsonify({
            'error': 'Unexpected error occurred',
            'details': str(e)
        }), 500

if __name__ == '__main__':
    print("Starting Flask server...")
    print("Make sure Manim is installed: pip install manim")
    app.run(debug=True, host='0.0.0.0', port=5000)