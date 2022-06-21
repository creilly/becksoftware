# based off of calculation from 15.06.2022

pi = 3.14159
vo = 1000 # m / s
deltafo = 4.2e6 # Hz
deltaomegao = deltafo * pi * 2 # rad / s

# v : velocity in m / s
# returns doppler spread (sigma) in rad / s
def get_deltaomega(v):
    return v/vo*deltaomegao