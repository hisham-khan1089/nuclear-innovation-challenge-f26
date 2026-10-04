"""Diagnostic plots for a completed simulation.

Each view opens separately. Legend entries toggle their corresponding lines.
"""

import numpy as np
import matplotlib.pyplot as plt


def _new_axes(height=4.5):
    _, ax = plt.subplots(figsize=(10, height), constrained_layout=True)
    return ax


def _clickable_legend(ax, **legend_kwargs):
    """Draws the legend and makes each entry a toggle for its line.

    Clicking the swatch or the label hides that series and greys the entry
    out; clicking again brings it back.
    """

    artists, _ = ax.get_legend_handles_labels()
    legend = ax.legend(**legend_kwargs)

    # legend entries are copies, so map each one back to the real artist
    toggles = {}
    entries = zip(legend.legend_handles, legend.get_texts(), artists)
    for handle, text, artist in entries:
        for clickable in (handle, text):
            if clickable is not None:
                clickable.set_picker(6)  # 6-pixel click radius
                toggles[clickable] = (artist, handle, text)

    def on_pick(event):
        entry = toggles.get(event.artist)
        if entry is None:
            return
        artist, handle, text = entry

        visible = not artist.get_visible()
        artist.set_visible(visible)
        text.set_alpha(1.0 if visible else 0.35)
        if handle is not None:
            handle.set_alpha(1.0 if visible else 0.35)
        ax.figure.canvas.draw_idle()

    ax.figure.canvas.mpl_connect("pick_event", on_pick)

    # Keep the interaction discoverable in the figure itself.
    ax.figure.text(0.995, 0.005, "click legend entries to show/hide lines",
                   ha="right", va="bottom", fontsize=7, color="gray", alpha=0.8)

    return legend


def _plot_power(simulator):
    ax = _new_axes()

    ax.plot(simulator.time_steps, simulator.n_current_values,
            label="True neutron population", color="black")
    ax.scatter(simulator.time_steps, simulator.n_measured_values,
               label="Raw noisy reading", color="gray", s=6, alpha=0.4)
    ax.plot(simulator.time_steps, simulator.n_estimated_values,
            label="EKF estimate", color="tab:blue")
    ax.plot(simulator.time_steps, simulator.n_desired_values, "--",
            label="Desired neutron population")

    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Normalized power")
    ax.set_title("Closed-Loop Reactor Power: true vs. measured vs. filtered")
    _clickable_legend(ax, loc="upper right", fontsize=8, framealpha=0.9)
    ax.grid()


def _plot_rod_command(simulator):
    ax = _new_axes()

    # These two only differ when the safety supervisor overrides the
    # controller, or an actuator fault is in play.
    ax.plot(simulator.control_times, simulator.commanded_rho_values,
            label="Controller-commanded rho", color="tab:red",
            linestyle="--", alpha=0.7)
    ax.plot(simulator.control_times, simulator.control_values,
            label="Actually-applied rho", color="orange")

    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Reactivity, rho (dk/k)")
    ax.set_title("Control-Rod Command: requested vs. applied")
    _clickable_legend(ax, loc="upper right", fontsize=8, framealpha=0.9)
    ax.grid()


def _plot_thermal_feedback(simulator):
    ax = _new_axes()

    ax.plot(simulator.time_steps, simulator.feedback_rho_values,
            label="Thermal reactivity", color="green")

    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Reactivity, rho (dk/k)")
    ax.set_title("Thermal Reactivity Feedback")
    _clickable_legend(ax, loc="upper right", fontsize=8, framealpha=0.9)
    ax.grid()


def _plot_estimation_error(simulator):
    ax = _new_axes()

    truth = np.array(simulator.n_current_values)
    measured_err = np.abs(np.array(simulator.n_measured_values) - truth)
    estimated_err = np.abs(np.array(simulator.n_estimated_values) - truth)

    ax.plot(
        simulator.time_steps,
        measured_err,
        label="Raw measurement error",
        color="gray",
    )
    ax.plot(
        simulator.time_steps,
        estimated_err,
        label="EKF estimate error",
        color="tab:blue",
    )

    ax.set_xlabel("Time (s)")
    ax.set_ylabel("|error|")
    ax.set_title("Power Estimation Error: raw vs. filtered")
    _clickable_legend(ax, loc="upper right", fontsize=8, framealpha=0.9)
    ax.grid()


def _plot_safety_state(simulator):
    ax = _new_axes(height=3.5)

    levels = {"NORMAL": 0, "WARNING": 1, "LIMITING": 2, "SCRAM": 3, "SHUTDOWN": 4}
    ax.step(simulator.control_times, [levels[s] for s in simulator.safety_states],
            where="post", color="crimson")

    ax.set_yticks(list(levels.values()), list(levels.keys()))
    ax.set_ylim(-0.5, 4.5)
    ax.set_xlabel("Time (s)")
    ax.set_title("Safety Supervisor State")
    ax.grid()


def _plot_temperatures(simulator):
    ax = _new_axes()

    ax.plot(simulator.time_steps, simulator.fuel_temp_values,
            label="Fuel temp (K)", color="firebrick")
    ax.plot(simulator.time_steps, simulator.coolant_temp_avg_values,
            label="Coolant temp avg (K)", color="teal")
    ax.axhline(simulator.safety.limits["fuel_temp"]["scram"], color="firebrick",
               linestyle=":", alpha=0.6, label="Fuel SCRAM limit")
    ax.axhline(simulator.safety.limits["coolant_temp"]["scram"], color="teal",
               linestyle=":", alpha=0.6, label="Coolant SCRAM limit")

    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Temperature (K)")
    ax.set_title("True Temperatures vs. Safety Limits")
    _clickable_legend(ax, fontsize=8, framealpha=0.9)
    ax.grid()


def plot_simulation(simulator):
    """Opens every diagnostic view for a finished run."""

    _plot_power(simulator)
    _plot_rod_command(simulator)
    _plot_thermal_feedback(simulator)
    _plot_estimation_error(simulator)
    _plot_safety_state(simulator)
    _plot_temperatures(simulator)
    plt.show()


class LivePlot:
    """Live-updating diagnostic plot during the simulation."""

    def __init__(self, simulator):
        self.simulator = simulator

        # Interactive mode is required so plt.show() does not block simulate().
        plt.ion()

        self.fig, axes_2d = plt.subplots(
            2, 3, figsize=(15, 9), constrained_layout=True
        )
        # Store a normal array rather than a numpy.flatiter.
        self.axes = axes_2d.ravel()

        # 0: POWER
        ax = self.axes[0]
        self.true_power_line, = ax.plot(
            [], [], label="True neutron population", color="black"
        )
        self.measured_power_scatter = ax.scatter(
            [], [], label="Raw noisy reading", color="gray", s=6, alpha=0.4
        )
        self.estimated_power_line, = ax.plot(
            [], [], label="EKF estimate", color="tab:blue"
        )
        self.desired_power_line, = ax.plot(
            [], [], "--", label="Desired neutron population"
        )
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Normalized power")
        ax.set_title("Reactor Power: true vs. measured vs. filtered")
        ax.legend(fontsize=8, loc="upper right")
        ax.grid(True)

        # 1: CONTROL ROD COMMAND
        ax = self.axes[1]
        self.commanded_rod_line, = ax.plot(
            [], [], "--", label="Commanded rho", color="tab:red", alpha=0.7
        )
        self.applied_rod_line, = ax.plot(
            [], [], label="Applied rho", color="orange"
        )
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Reactivity, rho (dk/k)")
        ax.set_title("Control Rod: commanded vs. applied")
        ax.legend(fontsize=8, loc="upper right")
        ax.grid(True)

        # 2: THERMAL FEEDBACK
        ax = self.axes[2]
        self.feedback_line, = ax.plot(
            [], [], label="Thermal reactivity", color="green"
        )
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Reactivity, rho (dk/k)")
        ax.set_title("Thermal Reactivity Feedback")
        ax.legend(fontsize=8, loc="upper right")
        ax.grid(True)

        # 3: ESTIMATION ERROR
        ax = self.axes[3]
        self.measured_err_line, = ax.plot(
            [], [], label="Raw error", color="gray"
        )
        self.estimated_err_line, = ax.plot(
            [], [], label="EKF error", color="tab:blue"
        )
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("|error|")
        ax.set_title("Power Estimation Error")
        ax.legend(fontsize=8, loc="upper right")
        ax.grid(True)

        # 4: SAFETY STATE
        ax = self.axes[4]
        self.safety_levels = {
            "NORMAL": 0,
            "WARNING": 1,
            "LIMITING": 2,
            "SCRAM": 3,
            "SHUTDOWN": 4,
        }
        self.safety_line, = ax.step([], [], where="post", color="crimson")
        ax.set_yticks(
            list(self.safety_levels.values()),
            list(self.safety_levels.keys()),
        )
        ax.set_ylim(-0.5, 4.5)
        ax.set_xlabel("Time (s)")
        ax.set_title("Safety Supervisor State")
        ax.grid(True)

        # 5: TEMPERATURES & LIMITS
        ax = self.axes[5]
        self.fuel_temp_line, = ax.plot(
            [], [], label="Fuel temp (K)", color="firebrick"
        )
        self.coolant_temp_line, = ax.plot(
            [], [], label="Coolant temp avg (K)", color="teal"
        )

        if hasattr(simulator, "safety") and hasattr(simulator.safety, "limits"):
            ax.axhline(
                simulator.safety.limits["fuel_temp"]["scram"],
                color="firebrick", linestyle=":", alpha=0.6,
                label="Fuel SCRAM limit",
            )
            ax.axhline(
                simulator.safety.limits["coolant_temp"]["scram"],
                color="teal", linestyle=":", alpha=0.6,
                label="Coolant SCRAM limit",
            )

        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Temperature (K)")
        ax.set_title("True Temperatures vs. Limits")
        ax.legend(fontsize=8, loc="upper left")
        ax.grid(True)

        # Actually create/show the GUI window without blocking the simulation.
        plt.show(block=False)

        # Draw the initial t=0 state immediately.
        self.update()

    def update(self):
        """Redraw all six plots from the simulation history accumulated so far."""
        sim = self.simulator

        if not sim.time_steps or not plt.fignum_exists(self.fig.number):
            return

        t = np.asarray(sim.time_steps, dtype=float)
        true_n = np.asarray(sim.n_current_values, dtype=float)

        # 1. Power
        self.true_power_line.set_data(t, true_n)
        self.estimated_power_line.set_data(t, sim.n_estimated_values)
        self.desired_power_line.set_data(t, sim.n_desired_values)

        measured = np.asarray(sim.n_measured_values, dtype=float)
        if len(measured) == len(t):
            self.measured_power_scatter.set_offsets(
                np.column_stack((t, measured))
            )

        # 2. Rod commands
        if sim.control_times:
            self.commanded_rod_line.set_data(
                sim.control_times, sim.commanded_rho_values
            )
            self.applied_rod_line.set_data(
                sim.control_times, sim.control_values
            )

        # 3. Thermal feedback
        self.feedback_line.set_data(t, sim.feedback_rho_values)

        # 4. Estimation error
        if len(measured) == len(true_n):
            self.measured_err_line.set_data(t, np.abs(measured - true_n))

        estimated = np.asarray(sim.n_estimated_values, dtype=float)
        if len(estimated) == len(true_n):
            self.estimated_err_line.set_data(t, np.abs(estimated - true_n))

        # 5. Safety state
        if sim.control_times and sim.safety_states:
            states = [self.safety_levels[s] for s in sim.safety_states]
            self.safety_line.set_data(sim.control_times, states)

        # 6. Temperatures
        self.fuel_temp_line.set_data(t, sim.fuel_temp_values)
        self.coolant_temp_line.set_data(t, sim.coolant_temp_avg_values)

        # Recalculate limits after changing line data.  Keep the categorical
        # safety-state y-axis fixed instead of autoscaling it.
        for i, ax in enumerate(self.axes):
            ax.relim()
            if i == 4:
                ax.autoscale_view(scalex=True, scaley=False)
                ax.set_ylim(-0.5, 4.5)
            else:
                ax.autoscale_view()

        # draw_idle() only schedules a future draw.  In this project the Python
        # simulation loop owns the main thread, so that scheduled draw may not
        # happen until the loop ends.  draw() performs the render now, and
        # plt.pause() briefly yields to the GUI event loop so the window can
        # paint it before the next simulation timestep starts.
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()
        plt.pause(0.01)

    def close(self):
        """Return Matplotlib to normal non-interactive mode."""
        plt.ioff()