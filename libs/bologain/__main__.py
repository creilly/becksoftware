from bologain import BoloGainHandler, gains, set_gain

with BoloGainHandler() as bgh:
    while True:
        print('gains:')
        print(
            '\n'.join(
                map(
                    '\t{: 5d}X'.format,
                    sorted(gains)
                )
            )
        )
        response = input('select gain (enter to quit): ')
        if not response:
            print('quitting.')
            exit()
        rawgain = response.lower().split('x')[0]
        if not rawgain.isdigit():
            print('selection must be digit.')
            continue
        gain = int(rawgain)
        if gain not in gains:
            print('invalid gain value. select from above options.')
            continue
        print('setting gain...')
        set_gain(bgh,gain)
        print('gain of {:d}X set.'.format(gain))
        