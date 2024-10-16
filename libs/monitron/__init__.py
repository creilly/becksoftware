import pfeiffer

PORT = 8302

def get_input():
    with pfeiffer.PfeifferGaugeHandler(pfeiffer.visaids[pfeiffer.HV]) as ph:
        return pfeiffer.get_pressure(ph,3)