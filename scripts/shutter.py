import daqmx

PUMP, TAG = 1, 2

channeld = {
    PUMP:'pump shutter',
    TAG:'tag shutter'
}

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

channel = channeld[int(input('\t' + 'enter shutter number: '))]

ON, OFF = 1, 0

stated = {
    ON:True,OFF:False
}

statenamed = {
    ON:'open', OFF:'shut'
}

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

with daqmx.LineHandler(channel) as line:
    daqmx.write_line(line,state)