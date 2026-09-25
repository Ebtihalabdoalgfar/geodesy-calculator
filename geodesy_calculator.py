import tkinter as tk
from tkinter import messagebox
import math


# =========================================================
# Constants - WGS84
# =========================================================

WGS84_A = 6378137.0
WGS84_F = 1 / 298.257223563


# =========================================================
# Helper Functions
# =========================================================

def parse_number(value):
    """
    Convert a text value to float.
    Supports normal numbers and simple fractions such as:
    1/298.257223563
    """
    value = value.strip()

    if "/" in value:
        parts = value.split("/")

        if len(parts) != 2:
            raise ValueError("Invalid fraction")

        numerator = float(parts[0])
        denominator = float(parts[1])

        if denominator == 0:
            raise ValueError("Division by zero")

        return numerator / denominator

    return float(value)


def validate_finite(value):
    if not math.isfinite(value):
        raise ValueError("Value must be finite")


def validate_latitude(latitude):
    if not -90 <= latitude <= 90:
        raise ValueError("Latitude must be between -90° and 90°")


def validate_longitude(longitude):
    if not -180 <= longitude <= 180:
        raise ValueError("Longitude must be between -180° and 180°")


# =========================================================
# Geodetic Calculations
# =========================================================

def ellipsoid_parameters(a, f, phi_deg):
    """
    Calculate ellipsoid parameters:
    b, e, e', N and M
    """

    if a <= 0:
        raise ValueError("Semi-major axis must be positive.")

    if f <= 0 or f >= 1:
        raise ValueError("Flattening must be between 0 and 1.")

    validate_latitude(phi_deg)

    phi = math.radians(phi_deg)

    b = a * (1 - f)

    e2 = 2 * f - f ** 2
    e = math.sqrt(e2)

    ep2 = (a  2 - b  2) / b ** 2
    ep = math.sqrt(ep2)

    sin_phi = math.sin(phi)

    N = a / math.sqrt(1 - e2 * sin_phi ** 2)

    M = (
        a * (1 - e2)
        / (1 - e2 * sin_phi  2)  1.5
    )

    return b, e, ep, N, M


def calculate_ellipsoid(values):

    try:
        a = parse_number(values[0])
        f = parse_number(values[1])
        phi = parse_number(values[2])

        b, e, ep, N, M = ellipsoid_parameters(a, f, phi)

        return (
            "Ellipsoid Parameters\n"
            "-------------------------\n"
            f"b = {b:.3f} m\n"
            f"e = {e:.9f}\n"
            f"e' = {ep:.9f}\n"
            f"N = {N:.3f} m\n"
            f"M = {M:.3f} m"
        )

    except ValueError as error:
        return f"Error: {error}"


# =========================================================
# Geodetic → Cartesian (ECEF)
# =========================================================

def geodetic_to_cartesian(phi_deg, lam_deg, h):

    validate_latitude(phi_deg)
    validate_longitude(lam_deg)

    a = WGS84_A
    f = WGS84_F

    e2 = 2 * f - f ** 2

    phi = math.radians(phi_deg)
    lam = math.radians(lam_deg)

    sin_phi = math.sin(phi)
    cos_phi = math.cos(phi)

    N = a / math.sqrt(
        1 - e2 * sin_phi ** 2
    )

    X = (N + h) * cos_phi * math.cos(lam)

    Y = (N + h) * cos_phi * math.sin(lam)

    Z = (
        N * (1 - e2) + h
    ) * sin_phi

    return X, Y, Z


def calculate_geodetic_to_cartesian(values):

    try:
        phi = parse_number(values[0])
        lam = parse_number(values[1])
        h = parse_number(values[2])

        X, Y, Z = geodetic_to_cartesian(phi, lam, h)

        return (
            "WGS84 Geodetic → Cartesian\n"
            "-------------------------\n"
            f"X = {X:.3f} m\n"
            f"Y = {Y:.3f} m\n"
            f"Z = {Z:.3f} m"
        )

    except ValueError as error:
        return f"Error: {error}"


# =========================================================
# Cartesian → Geodetic
# Bowring's closed-form approach
# =========================================================

def cartesian_to_geodetic(X, Y, Z):

    a = WGS84_A
    f = WGS84_F

    b = a * (1 - f)
    e2 = 2 * f - f ** 2

    ep2 = (a  2 - b  2) / b ** 2

    p = math.hypot(X, Y)

    # Special case: point is on the Z-axis
    if p < 1e-12:

        longitude = 0.0

        if Z > 0:
            latitude = 90.0
        elif Z < 0:
            latitude = -90.0
        else:
            latitude = 0.0

        height = abs(Z) - b

        return latitude, longitude, height

    # Bowring auxiliary angle
    theta = math.atan2(
        Z * a,
        p * b
    )

    sin_theta = math.sin(theta)
    cos_theta = math.cos(theta)

    latitude = math.atan2(
        Z + ep2 * b * sin_theta ** 3,
        p - e2 * a * cos_theta ** 3
    )

    longitude = math.atan2(Y, X)

    sin_latitude = math.sin(latitude)

    N = a / math.sqrt(
        1 - e2 * sin_latitude ** 2
    )

    height = (
        p / math.cos(latitude)
    ) - N

    return (
        math.degrees(latitude),
        math.degrees(longitude),
        height
    )


def calculate_cartesian_to_geodetic(values):

    try:
        X = parse_number(values[0])
        Y = parse_number(values[1])
        Z = parse_number(values[2])

        validate_finite(X)
        validate_finite(Y)
        validate_finite(Z)

        latitude, longitude, height = (
            cartesian_to_geodetic(X, Y, Z)
        )

        return (
            "WGS84 Cartesian → Geodetic\n"
            "-------------------------\n"
            f"Latitude = {latitude:.8f}°\n"
            f"Longitude = {longitude:.8f}°\n"
            f"Height = {height:.3f} m"
        )

    except ValueError as error:
        return f"Error: {error}"


# =========================================================
# Cartesian → ENU
# =========================================================

def calculate_cartesian_to_enu(values):

    try:

        X = parse_number(values[0])
        Y = parse_number(values[1])
        Z = parse_number(values[2])

        X0 = parse_number(values[3])
        Y0 = parse_number(values[4])
        Z0 = parse_number(values[5])

        # Reference point geodetic coordinates
        lat0, lon0, _ = cartesian_to_geodetic(
            X0, Y0, Z0
        )

        lat0 = math.radians(lat0)
        lon0 = math.radians(lon0)

        dX = X - X0
        dY = Y - Y0
        dZ = Z - Z0

        sin_lat = math.sin(lat0)
        cos_lat = math.cos(lat0)

        sin_lon = math.sin(lon0)
        cos_lon = math.cos(lon0)

        E = (
            -sin_lon * dX
            + cos_lon * dY
        )

        N = (
            -sin_lat * cos_lon * dX
            - sin_lat * sin_lon * dY
            + cos_lat * dZ
        )

        U = (
            cos_lat * cos_lon * dX
            + cos_lat * sin_lon * dY
            + sin_lat * dZ
        )

        return (
            "Cartesian → ENU\n"
            "-------------------------\n"
            f"E = {E:.3f} m\n"
            f"N = {N:.3f} m\n"
            f"U = {U:.3f} m"
        )

    except ValueError as error:
        return f"Error: {error}"


# =========================================================
# 7-Parameter Helmert Transformation
# Position Vector Convention
# =========================================================

def calculate_helmert_transformation(values):

    try:

        X = parse_number(values[0])
        Y = parse_number(values[1])
        Z = parse_number(values[2])

        dx = parse_number(values[3])
        dy = parse_number(values[4])
        dz = parse_number(values[5])

        rx_arcsec = parse_number(values[6])
        ry_arcsec = parse_number(values[7])
        rz_arcsec = parse_number(values[8])

        scale_ppm = parse_number(values[9])

        # Arc-seconds → radians
        arcsec_to_rad = math.pi / (
            180 * 3600
        )

        rx = rx_arcsec * arcsec_to_rad
        ry = ry_arcsec * arcsec_to_rad
        rz = rz_arcsec * arcsec_to_rad

        # ppm → scale factor
        scale = 1 + scale_ppm * 1e-6

        # Position Vector convention
        Xp = scale * ( X - rz * Y + ry * z ) + dx
        Yp = scale * ( rz * X + Y - rx * Z ) + dy

        Zp = scale * ( -ry * X + rx * Y + Z ) + dz

        return (
            "7-Parameter Helmert Transformation\n"
            "Position Vector Convention\n"
            "-------------------------\n"
            f"X' = {Xp:.6f} m\n"
            f"Y' = {Yp:.6f} m\n"
            f"Z' = {Zp:.6f} m"
        )

    except ValueError as error:
        return f"Error: {error}"


# =========================================================
# Spherical Sine Rule
# =========================================================

def calculate_spherical_sine_rule(values):

    try:

        A = math.radians(parse_number(values[0]))
        a = math.radians(parse_number(values[1]))
        b = math.radians(parse_number(values[2]))

        if math.isclose(math.sin(a), 0, abs_tol=1e-12):
            raise ValueError(
                "Arc a cannot produce sin(a) = 0."
            )

        sin_B = (
            math.sin(b) * math.sin(A)
        ) / math.sin(a)

        if sin_B < -1 or sin_B > 1:
            raise ValueError(
                "No valid spherical angle B for these inputs."
            )

        # Avoid tiny floating-point overflow
        sin_B = max(-1.0, min(1.0, sin_B))

        B1 = math.degrees(
            math.asin(sin_B)
        )

        B2 = 180 - B1

        return (
            "Spherical Sine Rule\n"
            "-------------------------\n"
            f"sin(B) = {sin_B:.9f}\n"
            f"B₁ = {B1:.6f}°\n"
            f"B₂ = {B2:.6f}°\n\n"
            "Note: The sine rule can produce two possible angles."
        )

    except ValueError as error:
        return f"Error: {error}"


# =========================================================
# Spherical Cosine Rule
# =========================================================

def calculate_spherical_cosine_rule(values):

    try:

        a = math.radians(parse_number(values[0]))
        b = math.radians(parse_number(values[1]))
        C = math.radians(parse_number(values[2]))

        cos_c = (
            math.cos(a) * math.cos(b)
            + math.sin(a)
            * math.sin(b)
            * math.cos(C)
        )

        # Protect against floating-point errors
        cos_c = max(-1.0, min(1.0, cos_c))

        c = math.acos(cos_c)

        return (
            "Spherical Cosine Rule\n"
            "-------------------------\n"
            f"cos(c) = {cos_c:.9f}\n"
            f"Arc c = {math.degrees(c):.6f}°"
        )

    except ValueError as error:
        return f"Error: {error}"


# =========================================================
# Orthometric Height
# =========================================================

def calculate_orthometric_from_geopotential(values):

    try:

        C = parse_number(values[0])
        g = parse_number(values[1])

        if g <= 0:
            raise ValueError(
                "Mean gravity must be greater than zero."
            )

        H = C / g

        return (
            "Orthometric Height\n"
            "-------------------------\n"
            f"H = {H:.3f} m"
        )

    except ValueError as error:
        return f"Error: {error}"


# =========================================================
# GUI
# =========================================================

root = tk.Tk()

root.title("Geodesy Calculator")

root.geometry("600x720")

root.configure(
    bg="#fce4ec"
)


frame = tk.Frame(
    root,
    bg="#fce4ec"
)

frame.place(
    relx=0.5,
    rely=0.4,
    anchor="center"
)


# =========================================================
# Frame Management
# =========================================================

def clear_frame():

    for widget in frame.winfo_children():
        widget.destroy()


# =========================================================
# Welcome Screen
# =========================================================

def show_welcome():

    clear_frame()
tk.Label(
        frame,
        text="Geodesy Calculator",
        font=("Helvetica", 26, "bold"),
        fg="#880e4f",
        bg="#fce4ec"
    ).pack(pady=10)

    tk.Label(
        frame,
        text="Welcome to my Geodesy Project",
        font=("Helvetica", 16),
        fg="#6a1b9a",
        bg="#fce4ec"
    ).pack(pady=10)

    tk.Label(
        frame,
        text="Prepared by: Ebtihal",
        font=("Helvetica", 14),
        fg="#4a148c",
        bg="#fce4ec"
    ).pack(pady=5)

    tk.Button(
        frame,
        text="Enter",
        font=("Helvetica", 14),
        bg="#ad1457",
        fg="white",
        width=10,
        command=show_menu
    ).pack(pady=20)


# =========================================================
# Main Menu
# =========================================================

def show_menu():

    clear_frame()

    menu_text = (
        "1. Ellipsoid Parameters\n"
        "2. Geodetic → Cartesian (WGS84)\n"
        "3. Cartesian → Geodetic (WGS84)\n"
        "4. Cartesian → ENU (WGS84)\n"
        "5. 7-Parameter Helmert Transformation\n"
        "6. Spherical Sine Rule\n"
        "7. Spherical Cosine Rule\n"
        "8. Orthometric Height\n"
        "9. Exit\n"
    )

    tk.Label(
        frame,
        text="Geodesy Calculator",
        font=("Helvetica", 20, "bold"),
        fg="#880e4f",
        bg="#fce4ec"
    ).pack(pady=10)

    tk.Label(
        frame,
        text=menu_text,
        font=("Helvetica", 12),
        fg="#6a1b9a",
        bg="#fce4ec",
        justify="left"
    ).pack(pady=10)

    tk.Label(
        frame,
        text="Enter your choice (1–9):",
        font=("Helvetica", 12),
        fg="#6a1b9a",
        bg="#fce4ec"
    ).pack()

    choice_entry = tk.Entry(
        frame,
        font=("Helvetica", 12),
        width=5
    )

    choice_entry.pack(pady=5)

    keypad_frame = tk.Frame(
        frame,
        bg="#fce4ec"
    )

    keypad_frame.pack(pady=5)

    def insert_menu_digit(value):
        choice_entry.insert(
            tk.END,
            value
        )

    def clear_menu_entry():
        choice_entry.delete(
            0,
            tk.END
        )

    digits = [
        ("1", "2", "3"),
        ("4", "5", "6"),
        ("7", "8", "9"),
        ("0", "Clear")
    ]

    for row in digits:

        row_frame = tk.Frame(
            keypad_frame,
            bg="#fce4ec"
        )

        row_frame.pack()

        for char in row:

            if char == "Clear":

                button = tk.Button(
                    row_frame,
                    text=char,
                    width=12,
                    command=clear_menu_entry
                )

            else:

                button = tk.Button(
                    row_frame,
                    text=char,
                    width=4,
                    command=lambda c=char:
                    insert_menu_digit(c)
                )

            button.pack(
                side=tk.LEFT,
                padx=2,
                pady=2
            )

    def process_choice():

        choice = choice_entry.get().strip()

        if choice == "1":

            fields = [
                "a (m)",
                "f",
                "φ (deg)"
            ]

            show_calculation_interface(
                "Ellipsoid Parameters",
                fields,
                calculate_ellipsoid
            )

        elif choice == "2":

            fields = [
                "φ (deg)",
                "λ (deg)",
                "h (m)"
            ]

            show_calculation_interface(
                "Geodetic → Cartesian",
                fields,
                calculate_geodetic_to_cartesian
            )

        elif choice == "3":

            fields = [
                "X (m)",
                "Y (m)",
                "Z (m)"
            ]

            show_calculation_interface(
                "Cartesian → Geodetic",
                fields,
                calculate_cartesian_to_geodetic
            )

        elif choice == "4":
          fields = [
                "X (m)",
                "Y (m)",
                "Z (m)",
                "X₀ (m)",
                "Y₀ (m)",
                "Z₀ (m)"
            ]

            show_calculation_interface(
                "Cartesian → ENU",
                fields,
                calculate_cartesian_to_enu
            )

        elif choice == "5":

            fields = [
                "X (m)",
                "Y (m)",
                "Z (m)",
                "dx (m)",
                "dy (m)",
                "dz (m)",
                "rx (arc-sec)",
                "ry (arc-sec)",
                "rz (arc-sec)",
                "scale (ppm)"
            ]

            show_calculation_interface(
                "7-Parameter Helmert",
                fields,
                calculate_helmert_transformation
            )

        elif choice == "6":

            fields = [
                "Angle A (°)",
                "Arc a (°)",
                "Arc b (°)"
            ]

            show_calculation_interface(
                "Spherical Sine Rule",
                fields,
                calculate_spherical_sine_rule
            )

        elif choice == "7":

            fields = [
                "Arc a (°)",
                "Arc b (°)",
                "Angle C (°)"
            ]

            show_calculation_interface(
                "Spherical Cosine Rule",
                fields,
                calculate_spherical_cosine_rule
            )

        elif choice == "8":

            fields = [
                "C (m²/s²)",
                "ḡ (m/s²)"
            ]

            show_calculation_interface(
                "Orthometric Height",
                fields,
                calculate_orthometric_from_geopotential
            )

        elif choice == "9":

            root.destroy()

        else:

            messagebox.showerror(
                "Error",
                "Please choose a number from 1 to 9."
            )

    tk.Button(
        frame,
        text="Submit",
        font=("Helvetica", 12),
        bg="#6a1b9a",
        fg="white",
        command=process_choice
    ).pack(pady=10)


# =========================================================
# Calculation Interface
# =========================================================

def show_calculation_interface(
    title,
    field_labels,
    calculation_function
):

    clear_frame()

    tk.Label(
        frame,
        text=title,
        font=("Helvetica", 18, "bold"),
        fg="#880e4f",
        bg="#fce4ec"
    ).pack(pady=10)

    entries = []

    for label in field_labels:

        tk.Label(
            frame,
            text=label,
            bg="#fce4ec",
            fg="#4a148c"
        ).pack()

        entry = tk.Entry(
            frame,
            font=("Helvetica", 11)
        )

        entry.pack(
            pady=2
        )

        entries.append(entry)

    active_entry = {
        "widget": None
    }

    for entry in entries:

        entry.bind(
            "<FocusIn>",
            lambda event, ent=entry:
            active_entry.update(
                {"widget": ent}
            )
        )

    keypad = tk.Frame(
        frame,
        bg="#fce4ec"
    )

    keypad.pack(
        pady=10
    )

    def insert_value(value):

        if active_entry["widget"]:

            active_entry["widget"].insert(
                tk.END,
                value
            )

    def backspace():

        if active_entry["widget"]:

            entry = active_entry["widget"]

            text = entry.get()

            entry.delete(
                0,
                tk.END
            )

            entry.insert(
                0,
                text[:-1]
            )

    def clear_entry():

        if active_entry["widget"]:

            active_entry["widget"].delete(
                0,
                tk.END
            )

    keys = [
        ("7", "8", "9"),
        ("4", "5", "6"),
        ("1", "2", "3"),
        ("0", ".", "/", "←"),
        ("Clear",)
    ]

    for row in keys:
      row_frame = tk.Frame(
            keypad,
            bg="#fce4ec"
        )

        row_frame.pack()

        for key in row:

            if key == "←":

                button = tk.Button(
                    row_frame,
                    text=key,
                    width=4,
                    command=backspace
                )

            elif key == "Clear":

                button = tk.Button(
                    row_frame,
                    text=key,
                    width=12,
                    command=clear_entry
                )

            else:

                button = tk.Button(
                    row_frame,
                    text=key,
                    width=4,
                    command=lambda value=key:
                    insert_value(value)
                )

            button.pack(
                side=tk.LEFT,
                padx=2,
                pady=2
            )

    def calculate():

        values = [
            entry.get()
            for entry in entries
        ]

        if any(not value.strip() for value in values):

            messagebox.showerror(
                "Missing Input",
                "Please fill in all fields."
            )

            return

        result = calculation_function(
            values
        )

        messagebox.showinfo(
            "Results",
            result
        )

    tk.Button(
        frame,
        text="Calculate",
        bg="#6a1b9a",
        fg="white",
        width=12,
        command=calculate
    ).pack(pady=8)

    tk.Button(
        frame,
        text="Back to Menu",
        bg="#ad1457",
        fg="white",
        width=12,
        command=show_menu
    ).pack(pady=5)


# =========================================================
# Start Application
# =========================================================

show_welcome()

root.mainloop()
