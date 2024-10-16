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
    with lockin.LockinHandler() as lih:
        while True:
            try:                
                set_output(lih,{'a':A,'b':B,'c':C,'d':D}[input('enter output to enable (A, B, C, D): ')[0].lower()])
                break
            except (IndexError, KeyError):
                print('invalid entry.')