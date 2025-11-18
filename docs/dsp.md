# Digital Signal Processing Reference

This document explains the EMG processing chain implemented in the project,
with mathematical definitions and practical guidance.

## 1. Sampling and Discretization
Let the continuous EMG voltage be \(x_c(t)\). Sampling at frequency \(f_s\)
produces discrete samples:
\[ x[n] = x_c(n / f_s), \quad n = 0,1,2,\dots \]
Nyquist frequency: \(f_N = f_s / 2\). All digital cutoff frequencies are
normalized by dividing by \(f_N\).

## 2. Band-Pass Filtering
Purpose: retain energy in typical EMG bandwidth (approx 20–450 Hz) while
rejecting motion artifacts (< 20 Hz) and high-frequency noise (> 450 Hz).

Butterworth design (maximally flat magnitude). For analog prototype:
\[ |H(j\Omega)|^2 = \frac{1}{1 + (\Omega/\Omega_c)^{2N}} \]
Transformation to digital domain uses bilinear transform. In code we call
`scipy.signal.butter` with normalized edges \(\omega_{low} = f_{low}/f_N\), \(\omega_{high} = f_{high}/f_N\).

Edge Cases & Guardrails:
- Invalid ordering (low >= high) -> passthrough.
- Non-positive or extreme cutoff -> clamped into (0,1).
- Very short sequences (< 10 samples) -> passthrough (insufficient for stable `filtfilt`).

### Zero-Phase Filtering
`filtfilt` applies the IIR forward and backward, eliminating phase shift.
Effective magnitude response is squared: \(|H_{filtfilt}| = |H|^2\).
Use only offline (post-recording) because it requires future samples.

## 3. Notch Filtering (Power-Line Interference)
Target frequency (e.g., 60 Hz). Digital notch transfer function:
\[ H(z) = \frac{1 - 2\cos(\omega_0) z^{-1} + z^{-2}}{1 - 2 R \cos(\omega_0) z^{-1} + R^2 z^{-2}} \]
Quality factor \(Q\) controls bandwidth; higher \(Q\) -> narrower notch.
Guardrail: normalized frequency \(\omega_0\) clamped to (0,1).

## 4. Rectification
Full-wave rectification:
\[ r[n] = |x[n]| \]
Removes sign, making subsequent amplitude metrics non-negative and easier to smooth.

## 5. Envelope Extraction
Two methods provided:
1. RMS Envelope:
   \[ e_{RMS}[n] = \sqrt{\frac{1}{N} \sum_{k=n-N/2}^{n+N/2} r[k]^2 } \]
2. Low-Pass Envelope:
   \[ e_{LP}[n] = (r * h)[n] \] where \(h[n]\) is a low-pass filter kernel (e.g. 5 Hz Butterworth).

Window Selection: Smaller N (< 10 ms) tracks detail but resembles rectified curve.
Moderate N (~100 ms) balances smoothness and responsiveness.

## 6. Integrated EMG (iEMG)
Approximate area under envelope:
\[ \text{iEMG} = \sum_{n} e[n] \Delta t = \Delta t \sum_n e[n] \]
Correlates with overall activation intensity over a time window.

## 7. Frequency-Domain Metrics
Compute one-sided FFT (real input):
\[ X[k] = \text{FFT}\{ x[n] \}, \quad f_k = \frac{k f_s}{N} \]
Power spectral density (unnormalized): \(P[k] = |X[k]|^2\).

Mean Frequency (MNF):
\[ \text{MNF} = \frac{\sum_k f_k P[k]}{\sum_k P[k]} \]

Median Frequency (MDF): find smallest \(f_m\) s.t.
\[ \sum_{k: f_k \le f_m} P[k] \ge \tfrac{1}{2} \sum_k P[k] \]
Fatigue often manifests as a downward shift in MDF/MNF over sustained contraction.

## 8. Signal-to-Noise Ratio (Heuristic)
We estimate noise floor via lower quantile of rectified samples (e.g. 20th percentile).
\[ \text{SNR}_{dB} = 20 \log_{10} \frac{\text{RMS}_{signal}}{\text{RMS}_{noise}} \]
This is a pragmatic approximation; formal SNR would require baseline/rest recordings.

## 9. Clipping Detection
For ADC codes in [0, 1023], flag proportion of samples near extremes (>99% or <1%).
High clipping percentage indicates insufficient gain staging or saturation.

## 10. Spectrogram
Segment length \(L\), overlap 75%. Apply Hann window \(w[n]\), compute magnitude:
\[ S_k[f] = | \text{FFT}( w[n] x_k[n]) | \]
Convert to dB: \(10 \log_{10}(S + \epsilon)\). Visualizes nonstationary frequency evolution.

## 11. Resilience Patterns
All preprocessing functions return passthrough on invalid parameters (e.g. window too
short, reversed band edges) to avoid breaking real-time acquisition loops.

## 12. Recommended Defaults
- Fs: 1000 Hz (common for surface EMG)
- Band-pass: 20–450 Hz, order 4
- Notch: 60 Hz, Q=30
- Envelope: RMS window 100 ms OR low-pass 5 Hz

## 13. References
- De Luca CJ. "The use of surface electromyography in biomechanics." J Appl Biomech, 1997.
- Clancy EA & Hogan N. "Single-site electromyograph amplitude estimation." IEEE TBME, 1999.
- Kwatny E, Thomas D, & Kwatny HG. "An application of signal processing techniques to the study of myoelectric signals." IEEE TBME, 1970.

---
End of DSP reference.