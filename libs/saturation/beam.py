import numpy as np

rtpi = np.sqrt(np.pi)
def get_side_length(diameter):
    return rtpi * diameter / 2

def get_intensity(power,diameter):
    return power / (np.pi * (diameter/2)**2)

def get_tau(diameter,velocity):
    side_length = get_side_length(diameter)
    return side_length / velocity