import matplotlib.pyplot as plt
import numpy as np
import tkinter as tk
from tkinter import Entry, Button
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Function to update graph
def update_graph():
    try:
        num_points = int(entry.get())
        x = np.linspace(0, 10, num_points)
        y = np.sin(x)
        
        ax.clear()
        ax.plot(x, y, marker='o', linestyle='-', color='b', label='Sine Wave')
        ax.set_xlabel('X Axis')
        ax.set_ylabel('Y Axis')
        ax.set_title('Dynamic Graph')
        ax.legend()
        canvas.draw()
    except ValueError:
        print("Please enter a valid integer")

# Create GUI window
root = tk.Tk()
root.title("Graph Updater")
root.geometry("600x600")

tk.Label(root, text="Enter number of points:").pack()
entry = Entry(root)
entry.pack()
Button(root, text="Update Graph", command=update_graph).pack()

# Create Matplotlib figure and embed it in Tkinter
fig, ax = plt.subplots(figsize=(4, 3))
canvas = FigureCanvasTkAgg(fig, master=root)
canvas.get_tk_widget().pack()

root.mainloop()

