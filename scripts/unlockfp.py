import laselock as ll, argparse

A, B = 'a', 'b'
ap = argparse.ArgumentParser()
ap.add_argument('--regulator','-r',choices=(A,B),default=A,help='laselock regulator to unlock')

reg = {A:ll.A,B:ll.B}[ap.parse_args().regulator]

with ll.LaseLockHandler() as llh:
    ll.set_reg_on_off(llh,reg,False)