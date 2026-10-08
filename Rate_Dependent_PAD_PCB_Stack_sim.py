#!/usr/bin/env python3
"""Rate-dependent gap filler pad / PCB stack simulator.

Standalone version of Rate_Dependent_PAD_PCB_Stack_sim_corrected.ipynb.
No Jupyter or IPython installation is required.

Install: python -m pip install numpy pandas scipy matplotlib pillow
Run:     python Rate_Dependent_PAD_PCB_Stack_sim.py

Place pad_rate_curves.csv and pcb_curve.csv alongside this script, or set
USE_EXAMPLE_DATA = True to use the notebook's illustrative sample data.

Required CSV headers and units:
  pad_rate_curves.csv: Rate_mm_min,Disp_mm,Force_N
  pcb_curve.csv:      Disp_mm,Force_N

Configure the simulation constants in the SETTINGS cell section below.
Plots appear when a GUI Matplotlib backend is available. The animation GIF
is saved alongside this script when RUN_ANIMATION and SAVE_GIF are True.
"""

# --- Original notebook code cell 2 ---
from pathlib import Path
import os

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter

from matplotlib.animation import FuncAnimation, PillowWriter
from scipy.interpolate import PchipInterpolator
from scipy.optimize import brentq

plt.style.use("seaborn-v0_8-whitegrid")


# --- Original notebook code cell 4 ---
USE_EXAMPLE_DATA = False

# Measured-data files
PAD_RATE_DATA_FILE = Path(__file__).resolve().parent / "pad_rate_curves.csv"
PCB_DATA_FILE = Path(__file__).resolve().parent / "pcb_curve.csv"

# Assembly settings
PAD_ORIGINAL_THICKNESS_MM = 1.5
STACK_SPEED_MM_MIN = 5.00
TARGET_TOTAL_DISPLACEMENT_MM = 0.70
TIME_STEP_SECONDS = 0.20

# Animation settings
RUN_ANIMATION = True
ANIMATION_FRAMES = 60
FRAME_INTERVAL_MS = 80
SAVE_GIF = True
GIF_FILE = "tim_pcb_rate_dependent_animation.gif"
GIF_FPS = 15


# --- Original notebook code cell 7 ---
if USE_EXAMPLE_DATA:
    example_displacements = [
        0.00, 0.10, 0.20, 0.30, 0.40, 0.50, 0.60
    ]

    # Independent illustrative curves. No multiplier is used.
    example_force_curves = {
        0.10: [0.00, 0.20, 1.50, 5.00, 12.0, 25.0, 44.0],
        0.50: [0.00, 0.25, 1.80, 5.80, 13.5, 28.0, 48.0],
        1.00: [0.00, 0.30, 2.10, 6.50, 15.0, 31.0, 52.0],
        2.00: [0.00, 0.38, 2.60, 7.50, 17.0, 34.0, 57.0],
        5.00: [0.00, 0.50, 3.40, 9.00, 20.0, 39.0, 65.0],
    }

    example_rows = []
    for rate, force_values in example_force_curves.items():
        for displacement, force_value in zip(example_displacements, force_values):
            example_rows.append({
                "Rate_mm_min": rate,
                "Disp_mm": displacement,
                "Force_N": force_value,
            })

    pad_rate_data = pd.DataFrame(example_rows)

    pcb_curve = pd.DataFrame({
        "Disp_mm": [0.00, 0.20, 0.40, 0.60, 0.80, 1.00],
        "Force_N": [0.00, 10.0, 20.0, 30.0, 40.0, 50.0],
    })

    print("Using independent illustrative pad curves.")
else:
    pad_rate_data = pd.read_csv(PAD_RATE_DATA_FILE)
    pcb_curve = pd.read_csv(PCB_DATA_FILE)
    print(f"Loaded pad data from: {PAD_RATE_DATA_FILE}")
    print(f"Loaded PCB data from: {PCB_DATA_FILE}")

print("\nPad input data (first 10 rows):\n", pad_rate_data.head(10).to_string(index=False))
print("\nPCB input data (first 5 rows):\n", pcb_curve.head().to_string(index=False))


# --- Original notebook code cell 10 ---
required_pad_columns = {"Rate_mm_min", "Disp_mm", "Force_N"}
missing_pad_columns = required_pad_columns.difference(pad_rate_data.columns)

if missing_pad_columns:
    raise ValueError(
        "Pad data are missing columns: "
        + ", ".join(sorted(missing_pad_columns))
    )

for column in required_pad_columns:
    pad_rate_data[column] = pd.to_numeric(
        pad_rate_data[column], errors="coerce"
    )

pad_rate_data = (
    pad_rate_data
    .dropna(subset=list(required_pad_columns))
    .copy()
)

if (pad_rate_data["Rate_mm_min"] <= 0).any():
    raise ValueError("All compression speeds must be greater than zero.")

if (pad_rate_data[["Disp_mm", "Force_N"]] < 0).any().any():
    raise ValueError("Pad displacement and force cannot be negative.")

pad_rate_data = (
    pad_rate_data
    .groupby(["Rate_mm_min", "Disp_mm"], as_index=False)["Force_N"]
    .mean()
    .sort_values(["Rate_mm_min", "Disp_mm"])
    .reset_index(drop=True)
)

measured_rates = np.sort(pad_rate_data["Rate_mm_min"].unique())

if len(measured_rates) < 2:
    raise ValueError("At least two pad compression speeds are required.")

pad_curves_by_rate = {}
minimum_displacements = []
maximum_displacements = []

for rate in measured_rates:
    rate_curve = (
        pad_rate_data[pad_rate_data["Rate_mm_min"] == rate]
        .sort_values("Disp_mm")
        .copy()
    )

    if len(rate_curve) < 2:
        raise ValueError(
            f"The {rate:g} mm/min curve needs at least two points."
        )

    if rate_curve["Disp_mm"].duplicated().any():
        raise ValueError(
            f"The {rate:g} mm/min curve contains duplicate displacements."
        )

    if np.any(np.diff(rate_curve["Force_N"]) < 0):
        raise ValueError(
            f"Force must not decrease on the {rate:g} mm/min loading curve."
        )

    pad_curves_by_rate[rate] = PchipInterpolator(
        rate_curve["Disp_mm"],
        rate_curve["Force_N"],
        extrapolate=False,
    )

    minimum_displacements.append(float(rate_curve["Disp_mm"].min()))
    maximum_displacements.append(float(rate_curve["Disp_mm"].max()))

pad_surface_min_disp = max(minimum_displacements)
pad_surface_max_disp = min(maximum_displacements)

if pad_surface_max_disp <= pad_surface_min_disp:
    raise ValueError(
        "The pad curves do not have a common displacement range."
    )

log_measured_rates = np.log(measured_rates)


def pad_force_from_surface(
    pad_displacement_mm,
    pad_rate_mm_min,
):
    if not (
        pad_surface_min_disp
        <= pad_displacement_mm
        <= pad_surface_max_disp
    ):
        raise ValueError(
            "Pad displacement is outside the measured surface range."
        )

    bounded_rate = float(np.clip(
        pad_rate_mm_min,
        measured_rates.min(),
        measured_rates.max(),
    ))

    forces_at_measured_rates = np.array([
        float(
            pad_curves_by_rate[rate](
                pad_displacement_mm
            )
        )
        for rate in measured_rates
    ])

    rate_interpolator = PchipInterpolator(
        log_measured_rates,
        forces_at_measured_rates,
        extrapolate=False,
    )

    return float(
        rate_interpolator(np.log(bounded_rate))
    )


# --- Original notebook code cell 12 ---
surface_displacements = np.linspace(
    pad_surface_min_disp, pad_surface_max_disp, 120
)
surface_rates = np.geomspace(
    measured_rates.min(), measured_rates.max(), 80
)

measured_force_grid = np.vstack([
    pad_curves_by_rate[rate](surface_displacements)
    for rate in measured_rates
])

surface_force = np.empty((len(surface_rates), len(surface_displacements)))

for displacement_index in range(len(surface_displacements)):
    surface_force[:, displacement_index] = np.interp(
        np.log(surface_rates),
        log_measured_rates,
        measured_force_grid[:, displacement_index],
    )

displacement_mesh, rate_mesh = np.meshgrid(
    surface_displacements, surface_rates
)

fig = plt.figure(figsize=(12, 8))
ax = fig.add_subplot(111, projection="3d")

surface_plot = ax.plot_surface(
    displacement_mesh,
    rate_mesh,
    surface_force,
    cmap="viridis",
    alpha=0.85,
    edgecolor="none",
)

for rate in measured_rates:
    measured_curve = pad_rate_data[
        pad_rate_data["Rate_mm_min"] == rate
    ]
    ax.scatter(
        measured_curve["Disp_mm"],
        np.full(len(measured_curve), rate),
        measured_curve["Force_N"],
        color="black",
        s=22,
    )

ax.set_xlabel("Pad compression displacement (mm)", labelpad=10)
ax.set_ylabel("Pad compression speed (mm/min)", labelpad=10)
ax.set_zlabel("Pad force (N)", labelpad=10)
ax.set_title("Rate-Dependent Pad Force Surface", fontsize=15, pad=18)
ax.view_init(elev=28, azim=-130)

fig.colorbar(
    surface_plot,
    ax=ax,
    shrink=0.65,
    pad=0.10,
    label="Force (N)",
)

plt.tight_layout()
plt.show()

print("Measured rates:", measured_rates)
print(
    "Common pad-displacement range:",
    f"{pad_surface_min_disp:.4f} to {pad_surface_max_disp:.4f} mm",
)


# --- Original notebook code cell 14 ---
required_pcb_columns = {"Disp_mm", "Force_N"}
missing_pcb_columns = required_pcb_columns.difference(pcb_curve.columns)

if missing_pcb_columns:
    raise ValueError(
        "PCB data are missing columns: "
        + ", ".join(sorted(missing_pcb_columns))
    )

pcb_curve = pcb_curve[["Disp_mm", "Force_N"]].copy()

for column in ["Disp_mm", "Force_N"]:
    pcb_curve[column] = pd.to_numeric(pcb_curve[column], errors="coerce")

pcb_curve = (
    pcb_curve
    .dropna()
    .query("Disp_mm >= 0 and Force_N >= 0")
    .groupby("Disp_mm", as_index=False)["Force_N"]
    .mean()
    .sort_values("Disp_mm")
    .reset_index(drop=True)
)

if len(pcb_curve) < 2:
    raise ValueError("The PCB curve needs at least two valid points.")

if pcb_curve.iloc[0]["Disp_mm"] > 0:
    pcb_curve = pd.concat([
        pd.DataFrame({"Disp_mm": [0.0], "Force_N": [0.0]}),
        pcb_curve,
    ], ignore_index=True)

if np.any(np.diff(pcb_curve["Force_N"]) < 0):
    raise ValueError("PCB force must not decrease as deflection increases.")

pcb_force_from_displacement = PchipInterpolator(
    pcb_curve["Disp_mm"],
    pcb_curve["Force_N"],
    extrapolate=False,
)

print("\nValidated PCB data:\n", pcb_curve.to_string(index=False))


# --- Original notebook code cell 16 ---
def solve_rate_dependent_stack():
    stack_speed_mm_s = STACK_SPEED_MM_MIN / 60.0
    total_loading_time_s = (
        TARGET_TOTAL_DISPLACEMENT_MM / stack_speed_mm_s
    )

    time_values = np.arange(
        0.0,
        total_loading_time_s,
        TIME_STEP_SECONDS,
    )

    if (
        len(time_values) == 0
        or not np.isclose(time_values[-1], total_loading_time_s)
    ):
        time_values = np.append(time_values, total_loading_time_s)

    rows = [{
        "Time_s": 0.0,
        "Force_N": 0.0,
        "Pad_Disp_mm": 0.0,
        "Pad_Rate_mm_min": 0.0,
        "Pad_Rate_Used_mm_min": measured_rates.min(),
        "PCB_Disp_mm": 0.0,
        "Total_Disp_mm": 0.0,
        "Pad_frac": 0.0,
        "PCB_frac": 0.0,
        "Rate_Clipped": False,
    }]

    previous_pad_displacement = 0.0
    previous_time_s = 0.0

    pcb_min_disp = float(pcb_curve["Disp_mm"].min())
    pcb_max_disp = float(pcb_curve["Disp_mm"].max())

    for current_time_s in time_values[1:]:
        step_time_s = current_time_s - previous_time_s
        total_displacement = min(
            stack_speed_mm_s * current_time_s,
            TARGET_TOTAL_DISPLACEMENT_MM,
        )

        lower_pad_displacement = max(
            previous_pad_displacement,
            pad_surface_min_disp,
            total_displacement - pcb_max_disp,
        )
        upper_pad_displacement = min(
            pad_surface_max_disp,
            total_displacement - pcb_min_disp,
            total_displacement,
        )

        if upper_pad_displacement < lower_pad_displacement:
            raise ValueError(
                "No common pad/PCB displacement range exists at "
                f"{current_time_s:.3f} s."
            )

        def force_balance_error(trial_pad_displacement):
            trial_pad_rate = (
                (trial_pad_displacement - previous_pad_displacement)
                / step_time_s
                * 60.0
            )
            trial_pad_force = pad_force_from_surface(
                trial_pad_displacement,
                max(trial_pad_rate, measured_rates.min()),
            )
            trial_pcb_displacement = (
                total_displacement - trial_pad_displacement
            )
            trial_pcb_force = float(
                pcb_force_from_displacement(trial_pcb_displacement)
            )
            return trial_pad_force - trial_pcb_force

        lower_error = force_balance_error(lower_pad_displacement)
        upper_error = force_balance_error(upper_pad_displacement)

        if np.isclose(lower_error, 0.0):
            pad_displacement = lower_pad_displacement
        elif np.isclose(upper_error, 0.0):
            pad_displacement = upper_pad_displacement
        elif lower_error * upper_error > 0:
            raise ValueError(
                "A force-balance solution could not be found at "
                f"{current_time_s:.3f} s. Check the measured pad-rate "
                "and PCB displacement ranges."
            )
        else:
            pad_displacement = brentq(
                force_balance_error,
                lower_pad_displacement,
                upper_pad_displacement,
            )

        pad_rate = (
            (pad_displacement - previous_pad_displacement)
            / step_time_s
            * 60.0
        )
        pad_rate_used = float(np.clip(
            pad_rate,
            measured_rates.min(),
            measured_rates.max(),
        ))
        pcb_displacement = total_displacement - pad_displacement
        force = pad_force_from_surface(pad_displacement, pad_rate_used)

        rows.append({
            "Time_s": current_time_s,
            "Force_N": force,
            "Pad_Disp_mm": pad_displacement,
            "Pad_Rate_mm_min": pad_rate,
            "Pad_Rate_Used_mm_min": pad_rate_used,
            "PCB_Disp_mm": pcb_displacement,
            "Total_Disp_mm": total_displacement,
            "Pad_frac": pad_displacement / total_displacement,
            "PCB_frac": pcb_displacement / total_displacement,
            "Rate_Clipped": not (
                measured_rates.min() <= pad_rate <= measured_rates.max()
            ),
        })

        previous_pad_displacement = pad_displacement
        previous_time_s = current_time_s

    return pd.DataFrame(rows)


stack = solve_rate_dependent_stack()
equilibrium = stack.iloc[-1].copy()

if stack["Rate_Clipped"].any():
    print(
        "Warning: At least one calculated pad rate was outside the "
        "measured range. The nearest measured rate was used."
    )

print("\nCalculated stack (first 5 rows):\n", stack.head().to_string(index=False))
print("\nCalculated stack (last 5 rows):\n", stack.tail().to_string(index=False))


# --- Original notebook code cell 18 ---
pad_compression_percent = (
    equilibrium["Pad_Disp_mm"]
    / PAD_ORIGINAL_THICKNESS_MM
    * 100.0
)
final_pad_thickness_mm = (
    PAD_ORIGINAL_THICKNESS_MM - equilibrium["Pad_Disp_mm"]
)

results = pd.DataFrame({
    "Result": [
        "Loading time",
        "Final stack displacement",
        "Equilibrium force",
        "Pad compression displacement",
        "Pad compression",
        "Final pad thickness",
        "Final pad compression rate",
        "PCB deflection",
    ],
    "Value": [
        equilibrium["Time_s"],
        equilibrium["Total_Disp_mm"],
        equilibrium["Force_N"],
        equilibrium["Pad_Disp_mm"],
        pad_compression_percent,
        final_pad_thickness_mm,
        equilibrium["Pad_Rate_mm_min"],
        equilibrium["PCB_Disp_mm"],
    ],
    "Unit": ["s", "mm", "N", "mm", "%", "mm", "mm/min", "mm"],
})

results["Value"] = results["Value"].round(4)
print("\nFinal results:\n", results.to_string(index=False))


# --- Original notebook code cell 20 ---
def plot_stack_results(stack, pad_rate_data, pcb_curve, equilibrium):
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    ax = axes[0, 0]
    for rate in measured_rates:
        rate_curve = pad_rate_data[
            pad_rate_data["Rate_mm_min"] == rate
        ]
        ax.plot(
            rate_curve["Disp_mm"],
            rate_curve["Force_N"],
            marker="o",
            label=f"Pad: {rate:g} mm/min",
        )
    ax.plot(
        pcb_curve["Disp_mm"],
        pcb_curve["Force_N"],
        color="black",
        marker="s",
        linewidth=2,
        label="PCB",
    )
    ax.set_xlabel("Component displacement (mm)")
    ax.set_ylabel("Force (N)")
    ax.set_title("Measured component responses")
    ax.legend(fontsize=8)

    ax = axes[0, 1]
    ax.plot(
        stack["Total_Disp_mm"],
        stack["Force_N"],
        color="black",
        label="Rate-dependent stack",
    )
    ax.scatter(
        equilibrium["Total_Disp_mm"],
        equilibrium["Force_N"],
        color="red",
        s=70,
        zorder=5,
        label="Final equilibrium",
    )
    ax.set_xlabel("Total stack displacement (mm)")
    ax.set_ylabel("Force (N)")
    ax.set_title("Combined stack response")
    ax.legend()

    ax = axes[1, 0]
    ax.plot(stack["Time_s"], stack["Pad_Disp_mm"], label="Pad compression")
    ax.plot(stack["Time_s"], stack["PCB_Disp_mm"], label="PCB deflection")
    ax.plot(
        stack["Time_s"],
        stack["Total_Disp_mm"],
        linestyle="--",
        color="black",
        label="Total displacement",
    )
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Displacement (mm)")
    ax.set_title("Displacement sharing during loading")
    ax.legend()

    ax = axes[1, 1]

    

    smoothed_pad_rate = savgol_filter(
        stack["Pad_Rate_mm_min"].to_numpy(),
        window_length=15,
        polyorder=2,
        mode="interp",
    )

    ax.plot(
        stack["Time_s"],
        smoothed_pad_rate,
        color="tab:purple",
        label="Pad rate (smoothed)",
    )

    ax.axhline(
        STACK_SPEED_MM_MIN,
        color="black",
        linestyle="--",
        label="Total stack speed",
    )

    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Compression speed (mm/min)")
    ax.set_title("Actual pad compression speed")
    ax.legend()
    
    
    fig.tight_layout()
    plt.show()


plot_stack_results(stack, pad_rate_data, pcb_curve, equilibrium)


# --- Original notebook code cell 23 ---
def create_stack_animation(
    stack,
    original_pad_thickness_mm,
    number_of_frames=60,
):
    frame_count = min(number_of_frames, len(stack))
    frame_indices = np.unique(
        np.linspace(0, len(stack) - 1, frame_count).astype(int)
    )
    frames = stack.iloc[frame_indices].reset_index(drop=True)

    force = frames["Force_N"].to_numpy()
    pad_disp = frames["Pad_Disp_mm"].to_numpy()
    pcb_disp = frames["PCB_Disp_mm"].to_numpy()
    total_disp = frames["Total_Disp_mm"].to_numpy()
    pad_rate = frames["Pad_Rate_mm_min"].to_numpy()

    pad_width = 6
    pcb_half_span = 12.0
    heatsink_width = 8.0
    heatsink_height = 0.30

    fig, (ax_anim, ax_graph) = plt.subplots(
        1,
        2,
        figsize=(14, 6),
        gridspec_kw={"width_ratios": [1.5, 1]},
    )

    def draw_frame(i):
        ax_anim.clear()
        ax_graph.clear()

        current_force = force[i]
        current_pad_disp = pad_disp[i]
        current_pcb_disp = pcb_disp[i]
        current_total_disp = total_disp[i]
        current_pad_rate = pad_rate[i]

        ax_anim.set_xlim(-15, 15)
        ax_anim.set_ylim(-2, 3)
        ax_anim.set_aspect("equal")
        ax_anim.set_title(
            f"Stack Deflection\n"
            f"Force = {current_force:.2f} N | "
            f"Pad rate = {current_pad_rate:.2f} mm/min"
        )

        x_pcb = np.linspace(-pcb_half_span, pcb_half_span, 300)
        pcb_y = -current_pcb_disp * (
            1 - (x_pcb / pcb_half_span) ** 2
        )
        ax_anim.plot(
            x_pcb, pcb_y, linewidth=6, color="green", label="PCB"
        )

        pad_thickness = max(
            original_pad_thickness_mm - current_pad_disp,
            0.05,
        )
        pad_bottom = -current_pcb_disp
        pad_top = pad_bottom + pad_thickness

        ax_anim.add_patch(plt.Rectangle(
            (-pad_width / 2, pad_bottom),
            pad_width,
            pad_thickness,
            facecolor="gray",
            edgecolor="black",
            alpha=0.75,
            label="Pad",
        ))
        ax_anim.add_patch(plt.Rectangle(
            (-heatsink_width / 2, pad_top),
            heatsink_width,
            heatsink_height,
            facecolor="lightgray",
            edgecolor="black",
            alpha=0.90,
            label="Heat sink",
        ))
        ax_anim.axhline(
            0, linestyle="--", linewidth=1, color="black", alpha=0.6
        )
        ax_anim.set_xlabel("Position across PCB")
        ax_anim.set_ylabel("Vertical position (mm)")
        ax_anim.legend(loc="upper right")

        ax_graph.plot(pad_disp, force, color="gray", linewidth=2, label="Pad")
        ax_graph.plot(pcb_disp, force, color="green", linewidth=2, label="PCB")
        ax_graph.plot(total_disp, force, color="blue", linewidth=2, label="Stack")
        ax_graph.plot(current_pad_disp, current_force, "o", color="gray")
        ax_graph.plot(current_pcb_disp, current_force, "o", color="green")
        ax_graph.plot(current_total_disp, current_force, "o", color="blue")
        ax_graph.set_xlim(0, max(float(total_disp.max()) * 1.10, 0.01))
        ax_graph.set_ylim(0, max(float(force.max()) * 1.10, 0.01))
        ax_graph.set_title("Force vs. Displacement")
        ax_graph.set_xlabel("Displacement (mm)")
        ax_graph.set_ylabel("Force (N)")
        ax_graph.legend(loc="lower right")
        fig.tight_layout()

    animation = FuncAnimation(
        fig,
        draw_frame,
        frames=len(frames),
        interval=FRAME_INTERVAL_MS,
        repeat=True,
    )
    return animation


if RUN_ANIMATION:
    stack_animation = create_stack_animation(
        stack,
        PAD_ORIGINAL_THICKNESS_MM,
        ANIMATION_FRAMES,
    )

    if SAVE_GIF:
        stack_animation.save(
            Path(__file__).resolve().parent / GIF_FILE,
            writer=PillowWriter(fps=GIF_FPS),
        )
        print("GIF saved to:")
        print((Path(__file__).resolve().parent / GIF_FILE).resolve())

    plt.show()  # Displays animation when using an interactive Matplotlib backend.
else:
    print("Animation is off. Set RUN_ANIMATION = True to display it.")
