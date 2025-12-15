import lockin

B0, B1 = 1, 3

bits = {0:B0,1:B1}

A, B, C, D = 0, 1, 2, 3

def set_output(lih,output):
    for bit, auxout in bits.items():
        lockin.set_aux_out(
            lih,auxout,{
                0:0.0,1:5.0
            }[output >> bit & 1]
        )

if __name__ == '__main__':
    import sys
    with lockin.LockinHandler() as lih:        
        cin = sys.argv[1] if len(sys.argv) > 1 else None        
        while True:
            try:     
                cin = input('enter output to enable (A, B, C, D): ') if cin is None else cin
                c = {'a':A,'b':B,'c':C,'d':D}[cin[0].lower()]
                print('setting mux to {}...'.format({A:'A',B:'B',C:'C',D:'D'}[c]))                        
                set_output(lih,c)
                print('mux set.')
                break
            except (IndexError, KeyError):
                print('invalid entry.')