"""Experiment 7: Tkinter GUI that draws geometric shapes for India HeatWatch."""
import tkinter as tk
from tkinter import messagebox

BG = "#101827"
PANEL = "#182338"
ORANGE = "#F28C45"
TEXT = "#F4F7FB"
MUTED = "#A9B6C9"

root = tk.Tk()
root.title("India HeatWatch — Tkinter Drawing Demo")
root.geometry("760x520")
root.configure(bg=BG)
root.minsize(620, 460)

title = tk.Label(root, text="India HeatWatch | Temperature Visualiser", bg=BG, fg=TEXT,
                 font=("Segoe UI", 18, "bold"))
title.pack(pady=(18, 4))
subtitle = tk.Label(root, text="Experiment 7: GUI development using Tkinter Canvas and geometric shapes",
                    bg=BG, fg=MUTED, font=("Segoe UI", 10))
subtitle.pack(pady=(0, 12))

canvas = tk.Canvas(root, width=690, height=290, bg=PANEL, highlightthickness=0)
canvas.pack(padx=20, pady=8, fill="both", expand=True)

controls = tk.Frame(root, bg=BG)
controls.pack(pady=12)
tk.Label(controls, text="Maximum temperature (°C):", bg=BG, fg=TEXT,
         font=("Segoe UI", 10)).grid(row=0, column=0, padx=8)
temp_var = tk.StringVar(value="35")
entry = tk.Entry(controls, textvariable=temp_var, width=8, font=("Segoe UI", 11))
entry.grid(row=0, column=1, padx=8)
status = tk.Label(root, text="Enter a value from 0 to 50 and click Draw.", bg=BG, fg=MUTED,
                  font=("Segoe UI", 10))
status.pack(pady=(0, 12))


def draw_shapes():
    try:
        temp = float(temp_var.get())
        if not 0 <= temp <= 50:
            raise ValueError("Temperature must be between 0 and 50°C.")
    except ValueError as exc:
        messagebox.showerror("Invalid temperature", str(exc) if str(exc) else "Enter a number between 0 and 50.")
        return
    canvas.delete("all")
    width = max(canvas.winfo_width(), 600)
    # Rectangle: temperature gauge background and filled bar.
    canvas.create_text(35, 34, anchor="w", text="TEMPERATURE RANGE", fill=MUTED,
                       font=("Segoe UI", 10, "bold"))
    x1, y1, x2, y2 = 35, 58, width - 35, 100
    canvas.create_rectangle(x1, y1, x2, y2, outline="#34445E", fill="#26344A", width=2)
    fill_x = x1 + (x2 - x1) * temp / 50
    colour = "#55B88A" if temp < 30 else (ORANGE if temp < 40 else "#EF5B5B")
    canvas.create_rectangle(x1, y1, fill_x, y2, outline="", fill=colour)
    canvas.create_text(x1, 119, anchor="w", text="0°C", fill=MUTED, font=("Segoe UI", 9))
    canvas.create_text(x2, 119, anchor="e", text="50°C", fill=MUTED, font=("Segoe UI", 9))
    canvas.create_text(width / 2, 80, text=f"{temp:.1f}°C", fill=TEXT, font=("Segoe UI", 15, "bold"))
    # Circle: indicator and label.
    canvas.create_oval(70, 160, 150, 240, fill=colour, outline=TEXT, width=2)
    canvas.create_text(110, 200, text="TEMP", fill=TEXT, font=("Segoe UI", 10, "bold"))
    # Rectangle: classification panel.
    canvas.create_rectangle(190, 160, width - 45, 240, fill="#202E44", outline="#34445E", width=2)
    if temp < 30:
        label = "Lower range in this demo"
    elif temp < 40:
        label = "High temperature — review conditions"
    else:
        label = "Very high temperature — review conditions"
    canvas.create_text(210, 188, anchor="w", text=label, fill=TEXT, font=("Segoe UI", 12, "bold"))
    canvas.create_text(210, 216, anchor="w", text="Illustrative visual category, not an official warning threshold.",
                       fill=MUTED, font=("Segoe UI", 9))
    status.config(text=f"Canvas redrawn for {temp:.1f}°C using rectangles, an oval and text.")

button = tk.Button(controls, text="Draw", command=draw_shapes, bg=ORANGE, fg="#101827",
                   activebackground="#FFAD73", relief="flat", padx=18, pady=5,
                   font=("Segoe UI", 10, "bold"))
button.grid(row=0, column=2, padx=8)
draw_shapes()
root.mainloop()
