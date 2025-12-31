"""Reusable Plotly figure builders for EMG dashboard.

Purpose
-------
Encapsulate visualization primitives (time series, PSD, spectrogram) used by
the Streamlit dashboard. Separation simplifies testing and future UI reuse.

Spectrogram Computation
-----------------------
Uses overlapping Hann‑windowed segments of length ``win_len`` with 75% overlap
(``step = win_len/4``). For each segment:

.. math:: S_k[f] = | \text{FFT}( w[n] x_k[n] ) |

Magnitudes are stacked to form a time‑frequency matrix converted to dB
(:math:`10 \log_{10}(S + \epsilon)`). This is a quick diagnostic; for formal
analysis one might apply Welch's method or multitaper approaches.
"""
from __future__ import annotations
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def plot_time_series(
    times: np.ndarray,
    raw: np.ndarray,
    rectified: np.ndarray,
    envelope: np.ndarray,
    markers: list[dict] | None,
    amp_units: str,
    env_method: str,
    max_points: int = 1200,
) -> go.Figure:
    """Return a 3-row time series figure (raw, rectified, envelope).
    Args:
        times: 1D time array (s).
        raw: raw EMG samples (scaled per amp_units).
        rectified: rectified EMG.
        envelope: smoothed envelope.
        markers: optional [{'time': float, 'label': str}, ...]
        amp_units: 'ADC code' or 'Voltage (V)'.
        env_method: label for envelope (RMS / Low-pass).
        max_points: downsample threshold.
    """
    def _downsample(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        if x.size <= max_points:
            return x, y
        idx = np.linspace(0, x.size - 1, max_points).astype(int)
        return x[idx], y[idx]

    t_raw, y_raw = _downsample(times, raw)
    t_rect, y_rect = _downsample(times, rectified)
    t_env, y_env = _downsample(times, envelope)
    y_label = "Amplitude (V)" if amp_units == "Voltage (V)" else "ADC code"

    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        subplot_titles=(
            f"Raw EMG ({'V' if amp_units=='Voltage (V)' else 'ADC'})",
            "Rectified",
            f"Envelope ({env_method})",
        ),
    )
    fig.add_trace(go.Scatter(x=t_raw, y=y_raw, line=dict(color="blue", width=1)), row=1, col=1)
    fig.add_trace(go.Scatter(x=t_rect, y=y_rect, line=dict(color="orange", width=1)), row=2, col=1)
    fig.add_trace(go.Scatter(x=t_env, y=y_env, line=dict(color="green", width=2)), row=3, col=1)

    if markers:
        if times.size:
            t0 = times[0]
            t1 = times[-1]
        else:
            t0, t1 = 0.0, 0.0
        for m in markers[-20:]:
            mt = m.get("time")
            if mt is not None and t0 <= mt <= t1:
                for r in (1, 2, 3):
                    fig.add_vline(x=mt, line=dict(color="red", width=1, dash="dash"), row=r, col=1)

    fig.update_layout(height=600, showlegend=False)
    fig.update_xaxes(title_text="Time (s)", row=3, col=1)
    for r in (1, 2, 3):
        fig.update_yaxes(title_text=y_label, row=r, col=1)
    return fig


def plot_psd(freqs: np.ndarray, psd: np.ndarray, mnf: float, mdf: float, fs_est: float) -> go.Figure:
    """ Returns a Power Spectral Density plot with MNF(Mean Frequency) and MDF(Median Frequency) annotations."""
    """
    Args:
        freqs: Frequency bins (Hz).
        psd: Power spectral density values.
        mnf: Mean frequency (Hz).
        mdf: Median frequency (Hz).
        fs_est: Estimated sampling frequency (Hz).
    """
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=freqs, y=psd, mode="lines", name="PSD"))
    fig.update_layout(height=280, title=f"PSD | MNF {mnf:.1f} Hz, MDF {mdf:.1f} Hz")
    fig.update_xaxes(title="Frequency (Hz)", range=[0, min(250, fs_est/2)])
    fig.update_yaxes(title="Power")
    return fig


def plot_spectrogram(sig: np.ndarray, fs: float) -> go.Figure | None:
    """Compute and return a spectrogram figure or None if not enough data."""
    if sig.size < 128 or fs <= 0:
        return None
    win_len = int(min(512, max(128, fs * 0.25)))
    step = win_len // 4
    windows = []
    freqs_spec = np.fft.rfftfreq(win_len, d=1.0 / fs)
    for start in range(0, sig.size - win_len, step):
        seg = sig[start : start + win_len] * np.hanning(win_len)
        S = np.abs(np.fft.rfft(seg))
        windows.append(S)
    if not windows:
        return None
    spec_arr = np.array(windows).T
    spec_db = 10.0 * np.log10(spec_arr + 1e-9)
    time_axis = np.arange(spec_db.shape[1]) * (step / fs)
    fig = go.Figure(
        data=go.Heatmap(z=spec_db, x=time_axis, y=freqs_spec, colorscale="Viridis")
    )
    fig.update_layout(height=300, title="Spectrogram (dB)")
    fig.update_yaxes(title="Frequency (Hz)", range=[0, min(250, fs / 2)])
    fig.update_xaxes(title="Time (s)")
    return fig
