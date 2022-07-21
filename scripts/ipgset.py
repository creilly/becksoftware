import ipg

with ipg.IPGHandler() as ipgh:
    power = float(input('enter ipg power setpoint (in watts): '))
    ipg.set_power_setpoint(ipgh,power)
