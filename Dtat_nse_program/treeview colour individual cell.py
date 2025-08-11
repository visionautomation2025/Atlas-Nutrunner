import customtkinter as ctk

# Set CustomTkinter theme
ctk.set_appearance_mode("dark")  # Try "light" for light mode
ctk.set_default_color_theme("blue")  # Other options: "green", "dark-blue"

# Create the main window
app = ctk.CTk()
app.title("CustomTkinter Table Example")
app.geometry("400x300")

# Create a frame to hold the table
frame = ctk.CTkFrame(app)
frame.pack(fill="both", expand=True, padx=10, pady=10)

# Define the table data
data = [
    ("Ku", 31),
    ("Se", 45),
    ("John", 38),
    ("Alice", 50),
    ("Bob", 29)
]

# Create headers for the table
header_name = ctk.CTkLabel(frame, text="Name", width=150, fg_color="gray", corner_radius=5)
header_name.grid(row=0, column=0, padx=5, pady=5)

header_age = ctk.CTkLabel(frame, text="Age", width=150, fg_color="gray", corner_radius=5)
header_age.grid(row=0, column=1, padx=5, pady=5)

# Function to add a row to the table
def add_row(row_index, name, age):
    # Create a label for the Name column
    name_label = ctk.CTkLabel(frame, text=name, width=150)
    name_label.grid(row=row_index, column=0, padx=5, pady=5)

    # Create a label for the Age column
    age_label = ctk.CTkLabel(frame, text=str(age), width=150)

    # Apply red background if age > 40
    if age > 40:
        age_label.configure(fg_color="red", text_color="white", corner_radius=5)

    age_label.grid(row=row_index, column=1, padx=5, pady=5)

# Add rows to the table
for i, (name, age) in enumerate(data, start=1):
    add_row(i, name, age)

# Run the app
app.mainloop()