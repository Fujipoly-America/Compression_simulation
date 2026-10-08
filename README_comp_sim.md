# Rate-Dependent Thermal Gap Pad and PCB Stack Simulation

An educational engineering tool for estimating how **thermal gap pad compression** and **PCB deflection** share the movement of a heat sink during assembly. It combines measured force–displacement curves for a gap pad at multiple compression speeds with a force–deflection curve for the PCB.

The model is available as a **Jupyter notebook** for an interactive, step-by-step walkthrough. A **standalone Python version** can also be run without Jupyter, provided the corresponding `.py` script is included in the repository.

> **Engineering limitation:** This is an approximate, measured-data-based mechanical model, not a finite-element analysis (FEA) or a substitute for testing the actual assembly.

## 1. Files and requirements

The notebook uses the following default filenames:

| File | Purpose |
| --- | --- |
| `Rate_Dependent_PAD_PCB_Stack_sim_corrected.ipynb` | Jupyter notebook version of the simulation |
| `pad_rate_curves.csv` | Measured gap pad compression curves at two or more speeds |
| `pcb_curve.csv` | Measured PCB force–deflection curve |
| Standalone `.py` script | Alternative execution without Jupyter; use the actual script filename included in this repository |

If the notebook has been renamed in this repository, open the `.ipynb` file listed here instead. Example input curves can be generated within the notebook, so measured CSV files are not required for a demonstration run.

**Python dependencies:** Python 3, NumPy, pandas, Matplotlib, SciPy, IPython. Running the `.ipynb` file also requires JupyterLab or Jupyter Notebook. GIF export uses Matplotlib's Pillow writer, so install Pillow if needed.

A typical local installation is:

```bash
python -m pip install numpy pandas matplotlib scipy ipython jupyterlab pillow
```

The notebook's plotting style uses `seaborn-v0_8-whitegrid`, which is included in compatible recent Matplotlib versions; this does not require installing the seaborn package separately.

## 2. How to download and run the Jupyter notebook

### Option A — Run locally with JupyterLab

1. On GitHub, select **Code → Download ZIP**, then extract the repository. Alternatively, clone it using Git.
2. Install Python 3 if it is not already installed.
3. Open a terminal or command prompt in the extracted repository folder.
4. Install the dependencies shown above.
5. Start JupyterLab:

   ```bash
   jupyter lab
   ```

6. Open `Rate_Dependent_PAD_PCB_Stack_sim_corrected.ipynb` (or the notebook filename shown in the repository).
7. In **Section 2 — Customer inputs**, choose example or measured data and edit the settings.
8. Use **Run → Run All Cells** to execute the notebook in order. Tables, plots, and the optional animation will be displayed below their respective cells.

For the measured-data option, keep the CSV files in the notebook's working directory or change their paths in Section 2.

### Option B — Use Google Colab without a local Jupyter installation

1. Download the `.ipynb` file from GitHub, or copy its GitHub URL.
2. Open [Google Colab](https://colab.research.google.com/).
3. Use **File → Upload notebook**, or Colab's GitHub tab, to open the notebook.
4. If using your own CSV data, upload those files to the Colab runtime and update the file paths if necessary. Colab's working files may be cleared when the runtime resets.
5. Set your customer inputs, then select **Runtime → Run all**. Install missing packages in Colab if prompted.

### Option C — Run the standalone Python script (no Jupyter required)

The standalone version is intended for users who prefer to run Python directly. Download the `.py` file and the required CSVs, install its dependencies, edit its input variables or file paths as provided in the script, and run:

```bash
python YOUR_SCRIPT_FILENAME.py
```

Replace `YOUR_SCRIPT_FILENAME.py` with the actual standalone script filename in this repository. **The standalone script was not included with the notebook used to prepare this README**, so its exact name, configuration options, and output behavior have not been independently verified. The notebook's specific variables and output descriptions below are confirmed from the `.ipynb` implementation.

## 3. Customer-adjustable inputs

In **Section 2 — Customer inputs** of the notebook, the following settings can be changed:

| Variable | Example setting in notebook | Description |
| --- | --- | --- |
| `USE_EXAMPLE_DATA` | `False` | `True` uses internally generated demonstration curves; `False` loads measured CSV files. |
| `PAD_RATE_DATA_FILE` | `Path("pad_rate_curves.csv")` | Path to the measured pad CSV file. |
| `PCB_DATA_FILE` | `Path("pcb_curve.csv")` | Path to the measured PCB CSV file. |
| `PAD_ORIGINAL_THICKNESS_MM` | `1.5` | Original, uncompressed pad thickness in millimeters; used to calculate compression percentage and final thickness. |
| `STACK_SPEED_MM_MIN` | `5.00` | Prescribed **total stack/heat-sink displacement rate**, in mm/min. This is not necessarily the pad's actual compression rate. |
| `TARGET_TOTAL_DISPLACEMENT_MM` | `0.70` | Total imposed heat-sink/stack displacement in millimeters. |
| `TIME_STEP_SECONDS` | `0.20` | Solver time increment in seconds; generally leave at the default unless exploring numerical behavior. |
| `RUN_ANIMATION` | `True` | Display an animation of the calculated loading history. |
| `ANIMATION_FRAMES` | `60` | Maximum number of animation frames. |
| `FRAME_INTERVAL_MS` | `80` | Display interval between animation frames in milliseconds. |
| `SAVE_GIF` | `True` | Save an animated GIF to disk. |
| `GIF_FILE` | `"tim_pcb_rate_dependent_animation.gif"` | Destination filename/path for the GIF. |
| `GIF_FPS` | `15` | Saved GIF playback frame rate. |

To start with an example rather than measured CSV files, change:

```python
USE_EXAMPLE_DATA = True
```

To use actual measurements, set it to `False` and supply both CSV files. The example pad and PCB curves are illustrative and are **not** material qualification data.

## 4. Required CSV data formats

Use **plain-text, comma-separated values (`.csv`)** with a header row. The column names are **case-sensitive and must match exactly** as written below. The data cells should contain numeric values only—do **not** append units such as `mm`, `N`, or `mm/min` to individual numbers. Use decimal points (`0.10`), not decimal commas. No extra title line is required.

### A. Pad compression data: `pad_rate_curves.csv`

Required column headers, in the example order:

```csv
Rate_mm_min,Disp_mm,Force_N
0.5,0.00,0.0
0.5,0.10,1.5
0.5,0.20,4.2
1.0,0.00,0.0
1.0,0.10,1.9
1.0,0.20,5.1
```

| Header | Units | Meaning |
| --- | --- | --- |
| `Rate_mm_min` | mm/min | Compression speed at which **that force–displacement curve was measured**. Repeat the speed value on each row belonging to that curve. |
| `Disp_mm` | mm | Pad compression displacement from the start of loading. |
| `Force_N` | N | Measured **total compressive force**, not pressure or stress. |

**Pad data rules:**

- Provide **at least two distinct positive compression speeds**, with **at least two displacement–force points per speed**.
- For each speed, provide a measured loading curve with nonnegative displacements and forces. Force must not decrease as compression increases after the data are sorted by displacement; the code rejects such curves.
- The speed must be greater than zero. A static (`0 mm/min`) curve is not valid input for logarithmic speed interpolation.
- Curves should span an **overlapping displacement range** sufficient for the simulated pad compression. The model does not extrapolate beyond their common displacement interval.
- Rows can be grouped by speed as shown. The notebook sorts the data and averages duplicate records with the same speed and displacement. Nevertheless, using cleaned, representative measurements is preferable.
- You can include more than two speeds; additional measured curves provide more information about the rate dependence.

**Example:** A row `1.0,0.20,5.1` means that at a measured compression speed of **1.0 mm/min**, the pad had been compressed **0.20 mm** and the measured total force was **5.1 N**.

### B. PCB deflection data: `pcb_curve.csv`

Required headers:

```csv
Disp_mm,Force_N
0.00,0.0
0.10,5.0
0.20,10.0
```

| Header | Units | Meaning |
| --- | --- | --- |
| `Disp_mm` | mm | PCB deflection at the representative load location. |
| `Force_N` | N | Corresponding total applied force. |

**PCB data rules:**

- Provide **at least two valid points** with nonnegative displacement and force.
- Force must not decrease as deflection increases; the notebook validates this after sorting.
- No speed column is needed: the PCB response is treated as **rate-independent**.
- Include measurements over the relevant PCB deflection range. The notebook does not extrapolate beyond the input curve. If the first provided point is at a displacement greater than zero, the notebook inserts `(0 mm, 0 N)` automatically, but supplying a measured zero point is preferable when appropriate.
- A straight-line force–deflection relationship is allowed, but a measured nonlinear PCB curve may also be supplied.

### Important measurement considerations

Use test data representative of the actual design. Pad force depends on the pad material, thickness, contact area, compression history and test conditions. PCB deflection depends on board thickness, support spacing, load location, mounting and other assembly details. **Do not mix force and pressure**; the model expects total force in newtons for both components. Ensure both datasets describe mechanically compatible areas and loading conditions. This model does not automatically rescale force for a different pad area.

If exporting from Excel, save as **CSV (comma delimited)** and confirm the header names and decimal separators. Keep your original raw measurements separately.

## 5. How the simulation works

The thermal pad and PCB are modeled as two deforming components **in series**. The heat sink is prescribed to move at a user-selected rate and distance. Its travel is shared between compression of the pad and deflection of the PCB.

The governing relationships are:

$$
F_{\mathrm{pad}} = F_{\mathrm{PCB}}
$$

$$
x_{\mathrm{stack}} = x_{\mathrm{pad}} + x_{\mathrm{PCB}}
$$

$$
v_{\mathrm{stack}} = v_{\mathrm{pad}} + v_{\mathrm{PCB}}
$$

**Step 1 — Prepare the measured pad surface.** Each measured pad force–displacement curve is fitted using **PCHIP** (piecewise cubic Hermite interpolation). At any displacement within the common measured range, the solver estimates pad force between measured compression speeds using a PCHIP interpolation of force against the **logarithm of compression speed**. It therefore uses the distinct measured curves, rather than multiplying one reference curve by an arbitrary factor. The separate 3D visualization uses interpolation on the log-speed axis to display the surface.

**Step 2 — Prepare the PCB curve.** A force–deflection relationship is created from the measured PCB points using PCHIP. The PCB response is assumed rate-independent for this model.

**Step 3 — Move the heat sink incrementally.** Based on `STACK_SPEED_MM_MIN`, `TARGET_TOTAL_DISPLACEMENT_MM` and `TIME_STEP_SECONDS`, the code advances the total stack displacement over a series of time steps.

**Step 4 — Solve for how displacement is shared.** At each step, the code tries a pad compression. PCB deflection is the total displacement minus that trial pad compression. The pad's *actual compression speed* is calculated from the change in pad displacement during the time step, which can be different from the prescribed stack speed. The code compares pad force from the rate-dependent surface with PCB force from its deflection curve, then uses a **Brent root-finding solver** to find a force-balanced split.

**Step 5 — Report the loading history.** The calculated time history contains stack force, pad compression, PCB deflection, actual pad compression speed, and flags when the calculated pad speed falls outside the range of the measured curves. When the pad speed is outside that range, the force calculation uses the nearest measured speed and produces a warning. This is **clipping, not extrapolation**.

## 6. Outputs and plots

The notebook produces:

- A 3D pad **force–compression displacement–compression speed** visualization, with measured data points shown on the surface.
- A table of final results: loading time, total displacement, equilibrium force, pad compression displacement and percentage, final pad thickness, final pad compression rate, and PCB deflection.
- A four-panel graph:

  | Position | Plot | Interpretation |
  | --- | --- | --- |
  | Top left | Measured component responses | Input pad force–displacement curves at different speeds and the PCB force–deflection curve. |
  | Top right | Combined stack response | Calculated force versus total stack displacement, highlighting final equilibrium. |
  | Bottom left | Displacement sharing during loading | How total movement is divided between pad compression and PCB deflection over time. |
  | Bottom right | Actual pad compression speed | Smoothed pad compression speed versus time, compared with the prescribed overall stack speed. |

- An optional schematic animation showing the PCB, pad and heat sink during loading, alongside force-versus-displacement traces. The animation is **illustrative**, not a geometrically rigorous FEA deformation result. A GIF can also be saved.

## 7. Troubleshooting

| Issue | What to check |
| --- | --- |
| `FileNotFoundError` | The CSV files are in the working directory, or the paths in Section 2 point to their actual locations. |
| Missing-columns error | Exact CSV headers: `Rate_mm_min,Disp_mm,Force_N` for the pad and `Disp_mm,Force_N` for the PCB. |
| Fewer than two pad speeds | Supply separate measured force–displacement curves at two or more *positive* compression speeds. |
| Non-monotonic force error | Check units, sensor sign, sorting, and measurement noise. The current implementation requires nondecreasing loading force with increasing displacement. |
| No common displacement range / no force-balance solution | Check the pad-curve overlap, the PCB range, the imposed total travel, and whether the two input datasets are physically compatible. |
| Calculated pad rate outside measurement range | Add measured curves at more relevant speeds; the current solver clips to the nearest available speed. |
| Animation fails or runs slowly | Try `RUN_ANIMATION = False` for static results, or `SAVE_GIF = False` to skip exporting the GIF. |
| Notebook does not run | Install the dependencies and execute all cells from the beginning, rather than running later cells before their inputs are defined. |

## 8. Assumptions and limitations

- The pad and PCB are treated as mechanically **in series**: their forces are equal, and their displacements sum to total heat-sink motion.
- The pad input curves represent continuous, monotonic compression loading at their specified measured rates.
- Pad interpolation is limited to the common measured displacement range; calculated rates outside the measured range are clipped and flagged.
- The PCB may use a linear or nonlinear force–deflection curve, but is treated as rate-independent.
- **Relaxation, creep, unloading/reloading, compression set, permanent deformation and thermal cycling are not modeled.**
- This is a preliminary educational/engineering estimate. Results should be validated using representative pad tests, the actual PCB assembly and actual loading conditions before being used for design decisions.

## 9. Project use

Use this simulation to explore why a PCB and a gap pad do not necessarily deform by the same amount or at the same speed during heat-sink installation. The measured data supplied by the user, the assumed loading conditions and the boundary conditions determine whether its predictions are relevant to a specific assembly.
