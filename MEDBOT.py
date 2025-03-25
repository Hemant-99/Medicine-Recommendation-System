import pandas as pd
import re
import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk
from ttkthemes import ThemedTk
from tkinter import font as tkFont
from hashlib import sha256  # For password hashing
from datetime import datetime  # To store search date and time
import json  # To store and load user credentials

# Load your dataset (replace 'your_dataset.csv' with your actual file path)
try:
    df = pd.read_csv('updated_indian_medicine_data.csv')  # Load your dataset
except FileNotFoundError:
    print("Error: Dataset file not found. Please check the file path.")
    exit()

# Check if required columns exist in the dataset
required_columns = ['name', 'manufacturer_name', 'medicine_desc']
if not all(column in df.columns for column in required_columns):
    print("Error: The dataset must contain the following columns: 'name', 'manufacturer_name', 'medicine_desc'")
    exit()

# Function to extract single disease from medicine_desc using regex
def extract_single_disease(description):
    if not isinstance(description, str):
        return None
    pattern = r"(used to treat|treat|for the treatment of)\s*([^.,]+)"
    match = re.search(pattern, description, re.IGNORECASE)
    if match:
        return match.group(2).strip()
    return None

# Add a new column 'single_disease' to the DataFrame
df['single_disease'] = df['medicine_desc'].apply(extract_single_disease)

# Drop rows where 'single_disease' is NaN
df = df.dropna(subset=['single_disease'])

# Function to normalize symptoms
def normalize_symptom(symptom):
    symptom = re.sub(r"(used to treat|treat|for the treatment of|ment of)", "", symptom, flags=re.IGNORECASE)
    symptom = re.sub(r"[^a-zA-Z\s]", "", symptom).strip()
    return symptom

# Normalize the 'single_disease' column
df['normalized_symptom'] = df['single_disease'].apply(normalize_symptom)

# Function to determine medicine type from name
def get_medicine_type(name):
    if "tablet" in name.lower():
        return "Tablet"
    elif "syrup" in name.lower():
        return "Syrup"
    else:
        return "Other"

# Add a new column 'type' to the DataFrame based on medicine name
df['type'] = df['name'].apply(get_medicine_type)

# Create the main GUI window with a modern theme
root = ThemedTk(theme="arc")
root.title("Medicine Recommendation System")
root.geometry("1200x800")

# Custom fonts
title_font = tkFont.Font(family="Helvetica", size=14, weight="bold")
label_font = tkFont.Font(family="Helvetica", size=12)
button_font = tkFont.Font(family="Helvetica", size=12, weight="bold")
cart_font = tkFont.Font(family="Georgia", size=16, weight="bold")  # Font for cart headings

# Connect to SQLite database (or create it if it doesn't exist)
conn = sqlite3.connect('user_data.db')
cursor = conn.cursor()

# Drop existing tables if they exist
cursor.execute('DROP TABLE IF EXISTS users')
cursor.execute('DROP TABLE IF EXISTS search_history')

# Create a table to store user profiles with the correct schema
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    patient_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    number TEXT NOT NULL,
    location TEXT NOT NULL,
    password TEXT NOT NULL
)
''')

# Create a table to store search history
cursor.execute('''
CREATE TABLE IF NOT EXISTS search_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT NOT NULL,
    search_query TEXT NOT NULL,
    search_date TEXT NOT NULL,
    FOREIGN KEY (patient_id) REFERENCES users (patient_id)
)
''')
conn.commit()

# Function to hash passwords
def hash_password(password):
    return sha256(password.encode()).hexdigest()

# Function to save user profile to the database
def save_profile():
    patient_id = patient_id_entry.get()
    name = name_entry.get()
    number = number_entry.get()
    location = location_entry.get()
    password = hash_password(password_entry.get())

    if not patient_id or not name or not number or not location or not password:
        messagebox.showwarning("Input Error", "All fields are required!")
        return

    try:
        cursor.execute('''
        INSERT INTO users (patient_id, name, number, location, password)
        VALUES (?, ?, ?, ?, ?)
        ''', (patient_id, name, number, location, password))
        conn.commit()
        messagebox.showinfo("Profile Saved", "Your profile has been saved successfully!")
        show_login()
    except sqlite3.IntegrityError:
        messagebox.showwarning("Error", "Patient ID already exists. Please choose a different one.")

# Function to authenticate user
def login():
    patient_id = login_patient_id_entry.get()
    password = hash_password(login_password_entry.get())

    cursor.execute('SELECT * FROM users WHERE patient_id = ? AND password = ?', (patient_id, password))
    user_data = cursor.fetchone()

    if user_data:
        messagebox.showinfo("Login Successful", "Welcome back!")
        show_medicine_recommendation()
        current_user.set(patient_id)  # Set the current user
        save_credentials(patient_id, password)  # Save credentials
    else:
        messagebox.showwarning("Login Failed", "Invalid Patient ID or Password.")

# Function to save credentials to a file
def save_credentials(patient_id, password):
    credentials = {"patient_id": patient_id, "password": password}
    with open("user_credentials.json", "w") as file:
        json.dump(credentials, file)

# Function to load credentials from a file
def load_credentials():
    try:
        with open("user_credentials.json", "r") as file:
            credentials = json.load(file)
            return credentials
    except FileNotFoundError:
        return None

# Function to save search history
def save_search_history(search_query):
    patient_id = current_user.get()
    if patient_id:
        search_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Current date and time
        cursor.execute('''
        INSERT INTO search_history (patient_id, search_query, search_date)
        VALUES (?, ?, ?)
        ''', (patient_id, search_query, search_date))
        conn.commit()

# Function to display search history in a table-like structure
def show_search_history():
    patient_id = current_user.get()
    if not patient_id:
        messagebox.showwarning("Error", "You must be logged in to view search history.")
        return

    cursor.execute('SELECT search_query, search_date FROM search_history WHERE patient_id = ?', (patient_id,))
    history = cursor.fetchall()

    if not history:
        messagebox.showinfo("Search History", "No search history found.")
        return

    history_window = tk.Toplevel(root)
    history_window.title("Search History")
    history_window.geometry("600x400")

    # Create a frame for the table
    table_frame = tk.Frame(history_window)
    table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    # Create a treeview widget for the table
    tree = ttk.Treeview(table_frame, columns=("Symptoms", "Date"), show="headings")
    tree.heading("Symptoms", text="Symptoms")
    tree.heading("Date", text="Date")
    tree.column("Symptoms", width=400)
    tree.column("Date", width=150)
    tree.pack(fill=tk.BOTH, expand=True)

    # Add data to the table
    for entry in history:
        tree.insert("", tk.END, values=entry)

# Function to recommend medicine for multiple symptoms
def recommend_medicine():
    symptoms = symptom_var.get().strip()
    if not symptoms:
        messagebox.showwarning("Input Error", "Please enter symptoms!")
        return

    # Save search history
    save_search_history(symptoms)

    # Split the input into individual symptoms
    symptom_list = [s.strip().lower() for s in symptoms.split(",")]
    medicine_type = type_var.get()

    # Clear previous results
    for widget in inner_frame.winfo_children():
        widget.destroy()

    # Find matching rows in the DataFrame
    matches = df[
        df['medicine_desc'].apply(lambda desc: all(symptom in desc.lower() for symptom in symptom_list))
    ]

    # Filter by medicine type if not 'All'
    if medicine_type != 'All':
        matches = matches[matches['type'] == medicine_type]

    # Drop duplicates based on medicine name
    matches = matches.drop_duplicates(subset=['name'])

    if matches.empty:
        no_result_label = tk.Label(inner_frame, text=f"No medicine found for the symptoms: '{symptoms}' and type: '{medicine_type}'.", font=label_font)
        no_result_label.pack(pady=10)
        return

    # Define card colors based on the selected medicine type
    if medicine_type == "All":
        bg_color = "#F0FFF0"  # Very light green
        border_color = "#D0FFD0"  # Very light green border
    elif medicine_type == "Tablet":
        bg_color = "#F0F8FF"  # Very light blue
        border_color = "#D0E0FF"  # Very light blue border
    elif medicine_type == "Syrup":
        bg_color = "#FFF8DC"  # Very light orange
        border_color = "#FFE8B0"  # Very light orange border

    # Display medicine details in cards (two columns)
    row, col = 0, 0
    for index, row_data in matches.iterrows():
        card = tk.Frame(
            inner_frame,
            bg=bg_color,
            bd=2,
            relief=tk.RAISED,
            padx=20,
            pady=20,
            highlightbackground=border_color,
            highlightthickness=2,
        )
        card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")

        # Medicine Name (bold and underlined)
        name_label = tk.Label(card, text=f"Medicine Name: {row_data['name']}", font=(label_font, 12, "bold", "underline"), bg=card["bg"], anchor="w")
        name_label.pack(fill=tk.X)

        # Manufacturer (bold and underlined)
        manufacturer_label = tk.Label(card, text=f"Manufacturer: {row_data['manufacturer_name']}", font=(label_font, 12, "bold", "underline"), bg=card["bg"], anchor="w")
        manufacturer_label.pack(fill=tk.X)

        # Description
        description_label = tk.Label(card, text=f"Description: {row_data['medicine_desc']}", font=label_font, bg=card["bg"], anchor="w", wraplength=400)
        description_label.pack(fill=tk.X)

        # Update row and column for the next card
        col += 1
        if col == 2:  # Two columns
            col = 0
            row += 1

    # Update the canvas scroll region
    inner_frame.update_idletasks()
    canvas.config(scrollregion=canvas.bbox("all"))

    # Center the inner frame
    canvas_width = canvas.winfo_width()
    inner_frame_width = inner_frame.winfo_reqwidth()
    if inner_frame_width < canvas_width:
        canvas.create_window((canvas_width // 2, 0), window=inner_frame, anchor=tk.N)

# Function to show the registration section
def show_registration():
    medicine_recommendation_frame.pack_forget()
    login_frame.pack_forget()
    registration_frame.pack(fill=tk.BOTH, expand=True)

# Function to show the login section
def show_login():
    medicine_recommendation_frame.pack_forget()
    registration_frame.pack_forget()
    login_frame.pack(fill=tk.BOTH, expand=True)

# Function to show the medicine recommendation section
def show_medicine_recommendation():
    registration_frame.pack_forget()
    login_frame.pack_forget()
    medicine_recommendation_frame.pack(fill=tk.BOTH, expand=True)

# Main Frame for Medicine Recommendation
medicine_recommendation_frame = tk.Frame(root)

# Symptom Input Section
symptom_label = tk.Label(medicine_recommendation_frame, text="Enter your symptoms (comma-separated):", font=title_font)
symptom_label.pack(pady=10)

symptom_var = tk.StringVar()
symptom_entry = ttk.Entry(medicine_recommendation_frame, textvariable=symptom_var, font=label_font, width=50)
symptom_entry.pack(pady=10)

# Medicine Type Buttons
button_frame = tk.Frame(medicine_recommendation_frame)
button_frame.pack(pady=10)

all_button = tk.Button(button_frame, text="All", font=button_font, bg="#90EE90", fg="white", command=lambda: select_button("All"))
all_button.pack(side=tk.LEFT, padx=10)

tablet_button = tk.Button(button_frame, text="Tablet", font=button_font, bg="#ADD8E6", fg="white", command=lambda: select_button("Tablet"))
tablet_button.pack(side=tk.LEFT, padx=10)

syrup_button = tk.Button(button_frame, text="Syrup", font=button_font, bg="#FFA07A", fg="white", command=lambda: select_button("Syrup"))
syrup_button.pack(side=tk.LEFT, padx=10)

type_var = tk.StringVar(value="All")

def select_button(button_type):
    all_button.config(bg="#90EE90")
    tablet_button.config(bg="#ADD8E6")
    syrup_button.config(bg="#FFA07A")
    if button_type == "All":
        all_button.config(bg="#32CD32")
    elif button_type == "Tablet":
        tablet_button.config(bg="#87CEEB")
    elif button_type == "Syrup":
        syrup_button.config(bg="#FF8C00")
    type_var.set(button_type)

select_button("All")

# Result Display Section
result_frame = tk.Frame(medicine_recommendation_frame)
result_frame.pack(pady=20, fill=tk.BOTH, expand=True)

scrollbar = ttk.Scrollbar(result_frame)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

canvas = tk.Canvas(result_frame, yscrollcommand=scrollbar.set)
canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

scrollbar.config(command=canvas.yview)

inner_frame = tk.Frame(canvas)
canvas.create_window((0, 0), window=inner_frame, anchor=tk.NW)

def on_mouse_scroll(event):
    canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

canvas.bind_all("<MouseWheel>", on_mouse_scroll)

# Recommend Medicine Button
recommend_button = ttk.Button(medicine_recommendation_frame, text="Recommend Medicine", command=recommend_medicine, style="Accent.TButton")
recommend_button.pack(pady=20)

# Search History Button
history_button = tk.Button(medicine_recommendation_frame, text="View Search History", font=button_font, command=show_search_history)
history_button.pack(pady=10)

# Settings Button at Top-Right Corner
settings_button = tk.Button(
    medicine_recommendation_frame,
    text="Login/Register",
    font=button_font,
    command=show_login
)
settings_button.place(relx=0.95, rely=0.02, anchor=tk.NE)  # Top-right corner

# Main Frame for Login
login_frame = tk.Frame(root)

# Cart-like structure for Login
login_cart = tk.Frame(login_frame, bg="#F0F8FF", bd=2, relief=tk.RAISED, padx=20, pady=20)
login_cart.place(relx=0.5, rely=0.5, anchor=tk.CENTER)  # Center the cart

# Login Heading
login_label = tk.Label(login_cart, text="Login", font=cart_font, bg="#F0F8FF")
login_label.pack(pady=10)

# Patient ID
tk.Label(login_cart, text="Patient ID:", font=label_font, bg="#F0F8FF").pack()
login_patient_id_entry = tk.Entry(login_cart, font=label_font)
login_patient_id_entry.pack(pady=5)

# Password
tk.Label(login_cart, text="Password:", font=label_font, bg="#F0F8FF").pack()
login_password_entry = tk.Entry(login_cart, font=label_font, show="*")
login_password_entry.pack(pady=5)

# Login Button
login_button = tk.Button(login_cart, text="Login", font=button_font, command=login)
login_button.pack(pady=10)

# Register Button
register_button = tk.Button(login_cart, text="Register", font=button_font, command=show_registration)
register_button.pack(pady=10)

# Main Frame for Registration
registration_frame = tk.Frame(root)

# Cart-like structure for Registration
registration_cart = tk.Frame(registration_frame, bg="#FFF8DC", bd=2, relief=tk.RAISED, padx=20, pady=20)
registration_cart.place(relx=0.5, rely=0.5, anchor=tk.CENTER)  # Center the cart

# Registration Heading
registration_label = tk.Label(registration_cart, text="Register", font=cart_font, bg="#FFF8DC")
registration_label.pack(pady=10)

# Patient ID
tk.Label(registration_cart, text="Patient ID:", font=label_font, bg="#FFF8DC").pack()
patient_id_entry = tk.Entry(registration_cart, font=label_font)
patient_id_entry.pack(pady=5)

# Name
tk.Label(registration_cart, text="Name:", font=label_font, bg="#FFF8DC").pack()
name_entry = tk.Entry(registration_cart, font=label_font)
name_entry.pack(pady=5)

# Number
tk.Label(registration_cart, text="Number:", font=label_font, bg="#FFF8DC").pack()
number_entry = tk.Entry(registration_cart, font=label_font)
number_entry.pack(pady=5)

# Location
tk.Label(registration_cart, text="Location:", font=label_font, bg="#FFF8DC").pack()
location_entry = tk.Entry(registration_cart, font=label_font)
location_entry.pack(pady=5)

# Password
tk.Label(registration_cart, text="Password:", font=label_font, bg="#FFF8DC").pack()
password_entry = tk.Entry(registration_cart, font=label_font, show="*")
password_entry.pack(pady=5)

# Submit Button
register_submit_button = tk.Button(registration_cart, text="Submit", font=button_font, command=save_profile)
register_submit_button.pack(pady=10)

# Back Button
back_button = tk.Button(registration_cart, text="⬅️ Back", font=button_font, command=show_login)
back_button.pack(pady=10)

# Variable to store the current logged-in user
current_user = tk.StringVar()

# Load saved credentials (if any)
credentials = load_credentials()
if credentials:
    login_patient_id_entry.insert(0, credentials["patient_id"])
    login_password_entry.insert(0, credentials["password"])

# Initially show the medicine recommendation section
show_medicine_recommendation()

# Run the GUI application
root.mainloop()

# Close the database connection when the application exits
conn.close()