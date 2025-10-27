import numpy as np
from emg.preprocessing.filters import apply_bandpass, apply_notch
from emg.preprocessing.envelope import sliding_rms

def test_bandpass_shape():
    fs = 1000
    t = np.linspace(0, 1, fs, endpoint=False)
    sig = np.sin(2*np.pi*50*t) + 0.1*np.random.randn(len(t))
    out = apply_bandpass(sig, lowcut=20, highcut=450, fs=fs)
    assert out.shape == sig.shape

def test_sliding_rms_nonnegative():
    sig = np.zeros(100)
    sig[10:20] = 1.0
    rms = sliding_rms(sig, window_size=11)
    assert len(rms) == len(sig)
    assert (rms >= 0).all()