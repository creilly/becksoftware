import topo, time

ic = topo.InstructionClient()
topo_channel = topo.FINE2
input_impedance = 10e3 # ohms
deltat = 2.0 # seconds
dt = 0.2 # seconds

try:
    input('did you remove the 50 ohm terminator?: ')
    while True:
        to = time.time()
        vs = []
        while True:
            vs.append(ic.get_input(topo_channel))
            if time.time() - to > deltat:
                break
            time.sleep(dt)
        print('{:+.3f}'.format(sum(vs)/len(vs)/input_impedance*1e6,3).rjust(8),'microamps')
except KeyboardInterrupt:
    print('quitting.')