import daqmx

PUMP, TAG = 1, 2

channeld = {
    PUMP:'pump shutter',
    TAG:'tag shutter'
}

OPEN, SHUT = 1, 0

stated = {
    OPEN:True,SHUT:False
}

statenamed = {
    OPEN:'open', SHUT:'shut'
}

def set_shutter(shutter,state):    
    with daqmx.LineHandler(channeld[shutter]) as line:
            daqmx.write_line(line,state)

if __name__ == '__main__':
    named = channeld

    print(
        '\n'.join(
            [
                '{:d}\t:\t{}'.format(
                    key,name
                ) for key, name in sorted(named.items())
            ]
        )
    )

    shutter = int(input('\t' + 'enter shutter number: '))

    print(
        '\n'.join(
            [
                '{:d}\t:\t{}'.format(
                    key,name
                ) for key, name in sorted(statenamed.items())
            ]
        )
    )

    state = stated[int(input('\t' + 'enter shutter state number: '))]

    set_shutter(shutter,state)