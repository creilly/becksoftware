import msvcrt, numpy, motorsync as ms

width = 210

ddacv = 0.01 # volts

coeffd = {'z':'phase','f':'freq'}
with ms.MotorSyncHandler() as msh:
    period = ms.get_period(msh)
    dacv = ms.get_dac_voltage(msh)
    d_index = 0
    sp_index = int(round(width/2))
    dac_index = 0
    display = [' '] * width
    M = 100
    while True:
        command = input('command (x for help): ')
        if not command:
            continue
        command = command[0]
        if command == 'x':
            print(
                '\n'.join(
                    ' '*4 + ' : '.join(
                        (k, desc)
                    ) for k, desc in (
                        ('q','quit'),
                        ('p','period'),
                        ('s','setpoint'),
                        ('D','plotter mode (w -> inc dac, s -> dec dac, q -> exit, l -> lock, u -> unlock, t -> toggle setpoint toggling)'),
                        ('d','set dac voltage'),
                        ('r','get dac voltage'),
                        ('h','phase shift forward'),
                        ('H','phase shift backward'),
                        ('Z','get phase gain'),
                        ('z','set phase gain'),
                        ('F','get freq gain'),
                        ('f','set freq gain')
                    )
                )
            )            
        if command == 'q':
            exit(0)
        if command == 'D':
            variance = 0
            mean = 0
            mudac = -1            
            while True:
                if msvcrt.kbhit():
                    c = msvcrt.getwch()
                    if c == 'q':
                        break
                    if c in ('w','s'):
                        dacv += {'w':+1,'s':-1}[c] * ddacv
                        ms.set_dac_voltage(msh,dacv)
                    if c == 'l':
                        ms.set_locking(msh)
                    if c == 'u':
                        ms.set_unlocking(msh)
                    if c == 't':
                        ms.toggle_setpoint_toggling(msh)
                delay = ms.get_delay(msh)
                display[d_index] = ' '
                display[sp_index] = ' '                
                display[dac_index] = ' '
                setpoint = ms.get_setpoint(msh)
                d_index = min(int(round(delay/period*width)),width-1)
                dac = ms.get_dac(msh)
                if mudac < 0:
                    mudac = dac
                mudac = mudac * (M - 1) / M + dac / M                
                dac_index = min(int(round(mudac * width / 2**16)),width-1)
                mean = mean * (M-1) / M + (delay-setpoint) / M
                variance = variance * (M-1) / M + (delay-setpoint)**2 / M
                sp_index = min(int(round(setpoint/period*width)),width-1)
                display[sp_index] = '|'
                display[dac_index] = 'o'                
                display[d_index] = '*'
                print(
                    '{} degs: {}'.format(
                        ' +- '.join(
                            '{:.2f}'.format(f).rjust(7) for f in (
                                mean * 360 / period,
                                numpy.sqrt(variance - mean**2) * 360 / period,
                            )
                        ),''.join(display)
                    )
                )
        if command == 'd':
            try:
                dacv = float(input('enter dac voltage: '))
            except ValueError:
                continue
            ms.set_dac_voltage(msh,dacv)
        if command == 'r':
            dacv = ms.get_dac_voltage(msh)
            print('dac voltage: {:.4f} volts'.format(dacv))
        if command in ('z','f'):
            try:
                gain = int(
                    input(
                        'enter {} gain: '.format(
                            coeffd[command]
                        )
                    )
                )
            except ValueError:
                continue
            {'z':ms.set_phase_gain,'f':ms.set_freq_gain}[command](msh,gain)
        if command in ('Z','F'):
            gain = {'Z':ms.get_phase_gain,'F':ms.get_freq_gain}[command](msh)            
            print('{} coeff: {:d}'.format(coeffd[command.lower()],gain))