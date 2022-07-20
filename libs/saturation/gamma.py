vrmso = 30 # millivolts
gammao = 80e6 # radians per second

# vrms in millivolts
# returns gamma in radians per second
def get_gamma(vrms):
    return (vrms/vrmso)**2 * gammao