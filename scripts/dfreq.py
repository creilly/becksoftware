import chopper, maxon, shutter, lockin, \
    time, numpy, bologain, opo, hitran, \
    topo, os, wavemeter, topolock, oscilloscope, \
    piezo, laselock, tclock, linescan, \
    pi, mirrormotion, rotationstage, fit, \
    datetime, config
from lid import lidclient
from bilt.experiment import hwp
from bologain import bologainclient
from beckasync import sleep, wait_time, event_loop, event_loop_logging, unwind_generator
from beckutil import print_color
from transfercavity import transfercavityclient as tcc
from grapher import graphclient

# main params
debug = False
hwp_installed = False
line_searching = False
hwp_reference = 16.0 # degrees
lid_reference = 80.0 # degrees
g_folder = ['2023','04','29']

# metadata params (be sure to review these)
md_description = 'aligned o-ch4 F1 <-> F2, P(3) F2 pump, full pump power'
md_wm_measured = 3028.74545 # cm-1
md_wm_reference = 3028.752260 # cm-1
md_wm_line = 'R(0) v3'
md_incident_angle = 35.0 # degrees
md_specular_angle = 70.0 # degrees
md_lid_angle = 90.0 # degrees
md_mirror_angle = 98.5 # degrees
md_direct_angle = 183.0 # degrees
md_mixture = 'pure methane, 2023-04 carbagas A1YGAYN'

# debug params
debug_amp = 10.0e-3 # v
debug_delta_mu = 50.0 # MHz
debug_sigma = 8.0 # MHz
debug_spec = 70.0 # degs
debug_exp = 20
debug_dphi = 5 # degs

# line setting
linefile = r'Z:\Surface\chris\scripts-data\2023\04\29\v3lines\lines.txt'
lineset_settle = 2.0 # seconds
dw = -0.007 # cm-1 ( wavemeter offset )

# sensitivity measurement
chopping_frequency = 243 # Hz
tag_phase = 144.92 # degs, TL/pump/4th phase: 24, NL/tag/3rd phase: 110
chop_phase = -8.88 # measured 2023-04-25
tag_chop_phase_shift = tag_phase-chop_phase 
chopping_gain = bologain.X200
chopping_tau = 0.5 # seconds
chopping_sens = 10.e-3 # v

# lid parameter
mirror_bolo_offset = md_mirror_angle - md_lid_angle # degrees

# transfer cavity accuracy
tc_df = 0.5 # MHz

# line search
ls_df = 7.5 # MHz
ls_deltaf = 100.0 # MHz
ls_deltat = 5.0 # seconds
ls_deltaz_thresh = 0.033 # volts tagging / volts shopped
ls_sens = 1e-3 # v, initial sensitivity

# frequency scan
fs_df = 1.5 # MHz
fs_deltaf = 90.0 # MHz
fs_deltat = 10.0 # seconds
fs_sens = 1e-3 # volts
fs_fit_sigma = 9.0 # MHz, guess std dev of peak

# hwp scan
HWP_POL, HWP_POW = 0, 1 # POL : scan polarization, POW : scan power (fluence curve)
hwp_mode = HWP_POL
hwp_min = 16 # degs
hwp_max = 107 # degs
hwp_steps = 30 # degs
hwp_deltat = 2.0 # seconds
hwp_sens = 1e-3 # volts

# angular scan
as_min = 50 # degs
as_max = 91 # degs
as_step = 2 # degs
as_deltat = 10.0 # seconds
as_sens = 1e-3 # volts

# pump hwp
pump_phi_hor = 67.5 # degs

# mode hop
dw_mode_hop = 0.020 # cm-1

# lockin configuration
auxchannels = (1,3)
HIGH = 4.0
LOW  = 0.0
ref_funcgen = ( LOW ,   HIGH )
ref_chopper = ( HIGH,   LOW  )
taus = 10 # lockin settle time (in lockin time constants)

def name_root(md):
    return ' '.join(
        [
            line_shorthand(md['hitran line']),
            str(md['trial']).rjust(3)
        ]
    )        

def line_shorthand(htline):
    j, sym, ll = hitran.parse_lq(htline[hitran.LLQ])
    return 'j {:d} l {:d}'.format(j,ll)

def start_line(
        htline : list,
        rsh : rotationstage.RotationStageHandler,
        wmh : wavemeter.WavemeterHandler
    ):
    print('starting line {}'.format(hitran.fmt_line(htline)))
    with pi.PIHandler() as pih:
        (f, w), sense_d, _ = event_loop_logging(
            (
                set_line(htline,wmh),
                measure_sensitivity(),
                move_detector(lid_reference,hwp_reference,pih,rsh)
            )
        )
    print('line start complete.')
    return f, w, sense_d

def get_metadata(htline,sense_d, trial):
    # identifier for measurement block
    timestamp = sense_d['timestamp']
    metadata = {
        'timestamp'     :   timestamp,
        'trial'         :   trial,
        'sensed'        :   sense_d,
        'hitran line'   :   htline,
        'wavemeter'     :   {
            'measured value'    :   (md_wm_measured,'cm-1'),
            'reference value'   :   (md_wm_reference,'cm-1'),
            'wavemeter offset'  :   (md_wm_measured-md_wm_reference,'cm-1'),
            'reference line'    :   md_wm_line
        } ,        
        'experiment'   :   md_description,
        'scattering'    :   {
            'incident angle'    :   (md_incident_angle, 'degrees'),
            'direct angle'      :   (md_direct_angle, 'degrees'),
            'lid angle'         :   (md_lid_angle, 'degrees'),
            'mirror angle'      :   (md_mirror_angle, 'degrees'),
            'specular angle'    :   (md_specular_angle, 'degrees'),
            'reference angle'   :   (lid_reference, 'degrees'),
            'mixture'           :   md_mixture,
        }
    }
    return metadata

def update_metadata(
    md, lih : lockin.LockinHandler,
):    
    configd = config.get_metadata(lia=lih)
    configd[config.MD_KEYS[config.LOCKIN]]['sensitivity'] = 'variable'
    md['config'] = configd
    return md

def move_lid(theta_lid):
    lidclient.set_lid(theta_lid,wait = False)
    while lidclient.get_moving():
        yield

def get_mirror_zs(theta_mirror,phi_hwp):
    zs = {}
    for add in (pi.X,pi.Y):
        zo = {
            pi.X:mirrormotion.get_xmirr,
            pi.Y:mirrormotion.get_ymirr
        }[add](theta_mirror)
        if hwp_installed:
            dz = {
                pi.X:hwp.deltax,
                pi.Y:hwp.deltay
            }[add](phi_hwp,hwp_reference)
        else:
            dz = 0
        zs[add] = (zo,dz)
    return zs

def move_laser(theta_mirror,phi_hwp,pih,rsh):
    if hwp_installed:
        rs_gen = rotationstage.set_angle_async(rsh,phi_hwp)
        # starts the hwp rotation
        next(rs_gen)    
    zs = get_mirror_zs(theta_mirror,phi_hwp)
    for add, (zo, dz) in zs.items():        
        z = zo + dz
        pi.set_position(pih,add,z)
    for add in (pi.X, pi.Y):
        while not pi.get_on_target_state(pih,add):
            yield    
    if hwp_installed:
        yield from rs_gen
    
def move_detector(theta_lid,phi_hwp,pih,rsh):        
    theta_mirror = theta_lid + mirror_bolo_offset
    yield from event_loop(
        (
            move_lid(theta_lid),
            move_laser(theta_mirror,phi_hwp,pih,rsh)
        )
    )
    zs = get_mirror_zs(theta_mirror,phi_hwp)
    print_color(
        'grey',
        ', '.join(
            '{}: {} {}'.format(
                label, 
                '{{:+.{}f}}'.format(precision).format(value),
                unit
            ) for label, value, precision, unit in 
            sum(
                [
                    [
                        (name,angle,1,'degs')
                        for name, angle in (
                            ('tl',theta_lid),
                            ('tm',theta_mirror)
                        )
                    ],[
                        ('ph',phi_hwp,1,'degs')
                    ],*[
                        [
                            (
                                fs.format({pi.X:'x',pi.Y:'y'}[add]),
                                zs[add][index],
                                3,
                                'mm'                            
                            ) for index, fs in enumerate(
                                ('{}o','d{}')
                            ) # field                                
                        ] for add in (pi.X,pi.Y) # add
                    ]
                ], start = []
            )
        )
    )

def set_lockin_input(lih,ref_source):
    for auxchannel, voltage in zip(auxchannels,ref_source):
        lockin.set_aux_out(lih, auxchannel, voltage)

def wait_topo(parameter,mode,value):
    mc = topo.MonitoringClient(parameter,mode)
    yield from mc.wait_async(value) 

def set_line(htline,wmh):   
    print('unlocking transfer cavity and fabry perot.') 
    tclock.unlocktc()    
    entry_code = opo.get_latest(htline)
    assert entry_code is not None
    entryd = opo.open_entry(htline,entry_code)    
    dw = md_wm_measured - md_wm_reference
    wo = hitran.lookup_line(htline)[hitran.WNUMBECK] + dw
    etalon, motor, piezo_voltage, temperature = (
        entryd[key] for key in (
            opo.ETALON, opo.MOTOR, opo.PIEZO, opo.TEMPERATURE
        )
    )
    print(
        'looking up line in opo db.',
         ', '.join(
            '{}: {}{}'.format(
                name, value, ' {}'.format(unit) if unit is not None else ''
            ) for name, value, unit in (
                ('ec', '{: 4d}'.format(entry_code), None),
                ('et', '{: 4d}'.format(etalon), 'steps'),
                ('mo', '{:.3f}'.format(motor), 'mm'),
                ('pz', '{:.2f}'.format(piezo_voltage), 'v'),
                ('dt', '{:.3f}'.format(temperature), 'deg c')
            )
        )
    )
    ic = topo.InstructionClient()
    print('setting etalon, motor, cavity piezo, and diode temp')
    ic.set_diode_temperature(temperature)
    to = time.time()
    ic.set_motor_pos(motor)    
    ic.set_etalon_pos(etalon)
    ic.set_piezo(piezo_voltage)    
    print('waiting for diode temperature to settle')
    yield from wait_topo('laser1:dl:tc:ready',topo.BOOL,True)    
    print('waiting for remainder of settle time')
    yield from wait_time(to,lineset_settle)
    w = yield from linescan.get_stable_wavenumber_with_dither_async(wmh,ic)
    if w is linescan.W_NOSIGNAL:
        raise Exception('no signal')        
    deltaw = w-wo
    deltawthresh = 1.0 # cm-1
    if abs(dw) > deltawthresh:
        raise Exception(
            'wavenumber deviation of {:.2f} cm-1 exceeds threshold of {:.2f} cm-1'.format(
                deltaw, deltawthresh
            )
        )
    print(
        'coarse tuning stage complete.',
        ', '.join(
            '{}: {:.4f} cm-1'.format(label, value) 
            for label, value in (
                ('wo', wo), ('w', w), ('dw', w-wo)
            )
        )
    )
    print('starting diode temperature fine tuning.')
    w = yield from linescan.tune_diode_temperature_async(ic,wmh,wo,w)
    print('scanning tc scanning')
    tclock.setup_lock()
    with (
        oscilloscope.ScopeHandler() as sh,
        piezo.PiezoDriverHandler() as pdh,
        laselock.LaseLockHandler() as llh
    ):
        print('starting fp lock')
        yield from topolock.lock_topo_async(ic,sh,pdh,llh)
    print('starting tc lock')
    yield from tclock.start_lock()
    print('starting tc relock')
    success, result = yield from tclock.finish_lock(wmh,wo)
    if success:
        print('line set succesful.')
        f, w = result
        return f, w
    else:
        print('tc relock failed. redoing line set again.')
        f, w = yield from set_line(htline,wmh)
        return f, w

def check_fault(mh,t):
    f = maxon.get_fault(mh)
    print('fault {}:'.format(t),f)
    maxon.clear_fault(mh)
    maxon.set_enabled_state(mh,True)
    
def block_beam_blocking(mh):        
    chopper.start_halt(mh)    
    chopper.wait_halt(mh,1.0)    
    chopper.start_home(mh)    
    chopper.wait_home(mh,1.0)    
    chopper.set_blocking(mh,True)    

def wait_chopper(mh,target_vel):
    to = time.time()
    while not maxon.get_movement_state(mh):
        units = maxon.get_velocity_units(mh)
        if time.time() - to > 1.0:
            print(
                ' / '.join(
                    [
                        '{:.0f}'.format(vel).rjust(8)
                        for vel in (
                            maxon.get_velocity_act(mh,units),
                            target_vel
                        )                        
                    ]
                ) + ' rpm'
            )
            to = time.time()
        yield

# waits until test returns * false *!
def wait_and_update(message,period,test,*args,**kwargs):
    to = time.time()
    while test(*args,**kwargs):
        if time.time() > to:
            print(message)
            to = time.time() + period
        yield

def measure_sensitivity():
    with (
        maxon.MaxonHandler() as mh,
        lockin.LockinHandler() as lih
    ):
        vchop = chopper.freq_to_vel(chopping_frequency)
        chopper.start_spin(mh,vchop)
        print('shutting laser shutters.')
        set_shutters(shutter.SHUT)
        print('configuring bolo gain to {:d} x.'.format(chopping_gain))
        bologainclient.set_gain(chopping_gain)
        print('setting lockin reference to mb chopper.')
        set_lockin_input(lih,ref_chopper)
        print('setting lockin sensivity to {:.0e} v'.format(chopping_sens))
        lockin.set_sensitivity(lih,chopping_sens)
        print(
            'setting lockin time constant to {:.0e} s'.format(
                chopping_tau
            )
        )
        lockin.set_time_constant(lih,chopping_tau)
        print('waiting for chopper to spin up...')
        yield from wait_chopper(mh,vchop)
        print('chopper at speed.')        
        print('waiting extra settle time:')        
        yield from lockin_settle(lih)
        print('getting lockin measurement...')
        x, y = yield from get_lockin_measurement(lih)
        timestamp = datetime.datetime.now().isoformat()        
        r, t = get_rt(x,y)        
        print('chopped beam reference measurement complete. r: {:.2e} v, t: {:.2f} degs'.format(r,t))
        phio = lockin.get_phase(lih)
        phichopped = phio + t
        phitagged = unwind(phichopped + tag_chop_phase_shift)
        print('setting tagging phase to {:.2f} degs'.format(phitagged))
        lockin.set_phase(lih,phitagged)
        print('setting lockin reference to function generator.')
        set_lockin_input(lih,ref_funcgen)
        print('opening shutters')
        set_shutters(shutter.OPEN)
        print('halting chopper...')
        chopper.start_halt(mh)
        yield from sleep(1.0)
        yield from wait_chopper(mh,0)
        print('chopped halted')
        chopper.start_home(mh)
        print('homing chopper...')
        while not chopper.is_homed(mh):
            yield
        print('chopper homed.')
        print('blocking molecular beam.')
        chopper.set_blocking(mh,True)
        bologainclient.set_gain(bologain.X1000)
        sense_d = {
            'bolo gain':(chopping_gain,'x'),
            'chopping frequency':(chopping_frequency,'hz'),
            'measurement':{
                'r':(r,'volts'),
                't':(t,'degrees')
            },
            'lockin phase before':(phio,'degrees'),
            'lockin phase after':(phitagged,'degrees'),
            'timestamp':timestamp,
            'time constant':chopping_tau
        }
        return sense_d

def lockin_settle(lih):
    tau = lockin.get_time_constant(lih)
    to = time.time()
    while time.time() - to < 10 * tau:
        yield

def unwind(angle):
    while angle > 360:
        angle -= 360
    while angle < 0:
        angle += 360
    return angle

def get_rt(x,y):
    return numpy.sqrt(
        x**2 + y**2
    ), numpy.rad2deg(numpy.arctan2(y,x))

def lock_lockin(lih):
    if lockin.get_unlocked(lih):
        if lockin.get_overloaded(lih):
            print('lockin unlocked and overloaded.')
            print('attempting to increase sensitivity')
            si = lockin.get_sensitivity_index(lih)
            sip = si + 1
            if sip == len(lockin.sensitivities):
                raise Exception('lockin overloaded at upper range')
            lockin.set_sensitivity_index(lih,sip)
        return True
    return False

def get_lockin_measurement(lih, settle = True):    
    yield from wait_and_update(
        'lockin locking...',1.0,
        lock_lockin, lih
    )            
    if settle:
        yield from lockin_settle(lih)    
    sens_threshold = 0.1
    si = lockin.get_sensitivity_index(lih)
    if lockin.get_overloaded(lih):
        while lockin.get_overloaded(lih):               
            si += 1
            if si == len(lockin.sensitivities):
                raise Exception('lockin input overload.')
            print('lockin overloaded.')
            print(
                'increasing range from {:.0e} v to {:.0e} v'.format(
                    *[
                        lockin.sensitivities[sensindex] 
                        for sensindex in (si-1,si)
                    ]
                )
            )
            lockin.set_sensitivity_index(lih,si)
            yield from lockin_settle(lih)        
    while True:
        x, y = lockin.get_xy(lih)
        r, t = get_rt(x,y)
        if r / lockin.sensitivities[si] < sens_threshold and si > 0:
            print('signal too weak.')            
            print(
                'decreasing range from {:.0e} v to {:.0e} v'.format(
                    *[
                        lockin.sensitivities[sensindex] 
                        for sensindex in (si+1,si)
                    ]
                )
            )
            si -= 1
            lockin.set_sensitivity_index(lih,si)
            yield from lockin_settle(lih)
        else:
            break
    return x, y
    
def set_shutters(state):
    for s in (shutter.PUMP,shutter.TAG):
        shutter.set_shutter(s,state)

def read_lines(linefile):
    with open(linefile,'r') as f:
        return [
            rawline.split('\t') 
            for rawline in 
            f.read().split('#')[0].split('\n')
            if rawline.strip()
        ]

def write_lines(linefile,lines):    
    with open(linefile,'w') as f:
        f.write(
            '\n'.join(
                map('\t'.join,lines)
            )
        )

dwdf = 1 / 30e3 # cm-1 per MHz
def set_and_measure(
        f : float,fo : float,wo : float,
        wmh : wavemeter.WavemeterHandler,
        lih : lockin.LockinHandler, 
        ic : topo.InstructionClient
    ):    
    w = wo + (f-fo) * dwdf
    tcc.set_setpoint(f)    
    awm = wavemeter.AsyncWavenumber(wmh,sync=wavemeter.NEW)    
    li_gen = get_lockin_measurement(lih)
    pds = []
    wps = []   
    def check_awm(get_new):
        ready, result = awm.get_wavenumber()
        if ready:
            wps.append(result)
            if get_new:
                return wavemeter.AsyncWavenumber(
                    wmh,sync=wavemeter.OLD                    
                )
            else:
                return True
        else:
            return None
    try:
        while True:
            pds.append(ic.get_input(topo.FAST4))
            result = check_awm(True)
            if result:
                awm = result
            next(li_gen)
    except StopIteration as si:
        x, y = si.value        
    while check_awm(False) is None:
        continue
    pd = numpy.average(pds)
    wp = numpy.average(wps)    
    dw = wp - w
    print_data(
        'mode hop log',
        (
            ('f', f, 1, 'mhz'),
            ('fo', fo, 1, 'mhz'),
            ('wo', w, 4, 'cm-1'),
            ('w', wp, 4, 'cm-1'),
            ('dw', abs(wp-w), 4, 'cm-1'),
            ('nw', len(wps), 0, 'samps')
        ), color = 'grey', tabs = 0, width = 20        
    )
    if abs(dw) > dw_mode_hop:
        raise ModeHopException()
    return x, y, pd, wp

class ModeHopException(Exception): pass

def print_freq(f,x,y,p,intro,color):
    print_data(
        intro,
        (
            ('f',   f,      1,  'mhz'),
            ('x',   1e3*x,  3,  'mv'),
            ('y',   1e3*y,  3,  'mv'),
            ('p',   1e3*p,  3,  'mv'),                
        ), color = color, tabs = 1
    )

def line_search(        
    md : dict, r_sens : float, fo : float, wo : float, 
    wmh : wavemeter.WavemeterHandler, 
    lih : lockin.LockinHandler,
    ic : topo.InstructionClient
):
    configure_lockin(lih,ls_sens,ls_deltat)
    update_metadata(md, lih)
    path = graphclient.add_dataset(
        [*g_folder,'line searches'],
        name_root(md),
        (
            'tc freq (mhz)',
            'lockin x (v)',
            'lockin y (v)',
            'photodiode (v)',
            'wavemeter (cm-1)'
        ),md
    )
    def get_f(jump_index):
        return fo + ls_df * jump_index
    def get_sign(index):
        return (-1) ** (index // 2)
    def get_jump(index):
        return (index + 1) // 2
    def get_jump_index(index):
        return get_sign(index), get_jump(index)    
    index = 0    
    xs = {}
    dx_thresh = r_sens * ls_deltaz_thresh
    print('starting gradient detection. dx thresh {:.2e} v'.format(dx_thresh))
    while True:        
        sign, jump = get_jump_index(index)
        jump_index = sign * jump
        f = get_f(jump_index)        
        if abs(f-fo) > ls_deltaf:
            print('gradient detection unsuccessful.')
            return None        
        x, y, p, w = set_and_measure(f,fo,wo,wmh,lih,ic)
        if debug:
            x = debug_amp * numpy.exp(
                -1 / 2 * (
                    ( f - ( fo + debug_delta_mu ) ) /
                    debug_sigma
                )**2
            )    
        graphclient.add_data(
            path,
            (f,x,y,p,w)
        )    
        print_freq(f,x,y,p,'ls gradient'.ljust(12),'purple')    
        xs[jump_index] = x    
        if index:            
            xo = xs[jump_index - sign] 
            dx = x - xo
            if abs(dx) > dx_thresh:
                print('gradient detection successful.')
                break
        index += 1
    print('starting threshold detection.')
    increasing = dx > 0    
    x_thresh = min(x,xo)    
    direction = {
        True:+1,False:-1
    }[
        increasing == (sign > 0)
    ]    
    while True:
        jump_index += direction
        if jump_index in xs:
            x = xs[jump_index]
        else:
            df = ls_df * jump_index
            f = fo + df
            x, y, p, w = set_and_measure(f,fo,wo,wmh,lih,ic)
            if debug:
                x = debug_amp * numpy.exp(
                    -1 / 2 * (
                        ( f - ( fo + debug_delta_mu ) ) /
                        debug_sigma
                    )**2
                )    
            graphclient.add_data(
                path,
                (f,x,y,p,w)
            )              
            print_freq(f,x,y,p,'ls threshold'.rjust(12),'yellow')
            xs[jump_index] = x            
        if x < x_thresh:
            print('threshold detection successful.')
            break    
    xmax = None
    for jump_index, x in xs.items():
        if xmax is None or x > xmax:
            xmax = x
            jimax = jump_index
    fmax = get_f(jimax)
    md['line search'] = (fmax,'mhz')
    return fmax

def frequency_scan(
    md : dict,
    f_ls : float, fo : float, wo : float, 
    wmh : wavemeter.WavemeterHandler, 
    lih : lockin.LockinHandler,
    ic : topo.InstructionClient
):
    print('initializing lockin for frequency scan')
    configure_lockin(lih,fs_sens,fs_deltat)
    update_metadata(md,lih)    
    path = graphclient.add_dataset(
        [*g_folder,'frequency scans'],
        name_root(md),
        (
            'tc freq (mhz)',
            'lockin x (v)',
            'lockin y (v)',
            'photodiode (v)',
            'wavemeter (cm-1)'
        ),md
    )
    deltaf = fs_deltaf
    df = fs_df
    fs = f_ls + numpy.arange(-deltaf/2,+deltaf/2,df)
    print('starting scan')
    xs = []
    for f in fs:
        x, y, p, w = set_and_measure(
            f, fo, wo, wmh, lih, ic
        )        
        if debug:
            x = debug_amp * numpy.exp(
                -1 / 2 * (
                    ( f - ( fo + debug_delta_mu ) ) /
                    debug_sigma
                )**2
            )
        graphclient.add_data(
            path,
            (f,x,y,p,w)
        )
        xs.append(x)
        print_freq(f,x,y,p,'freq scan data','blue')
    print('scan complete.')    
    xs = numpy.array(xs)
    max_index = xs.argmax()
    mu_guess = fs[max_index]
    sigma_guess = fs_fit_sigma
    offset_guess = numpy.average(xs)
    amp_guess = xs[max_index] - offset_guess
    try:
        parameters, covariances = fit.gaussian_fit(
            fs,xs,
            mu_guess,sigma_guess,amp_guess,offset_guess
        )        
        print(
            'fit successful. params:',
            ', '.join(
                [
                    '{} : {} {}'.format(
                        label,'{:.2e}'.format(val).rjust(10),unit
                    ) for label, val, unit in zip(
                        ('mu','sigma','amp','offset'),
                        parameters,
                        ('mhz','mhz','v','v')
                    )
                ]
            )
        )
        f_mean, f_sigma, x_amp, x_off = parameters
        f_sigma = abs(f_sigma)
        f_margin = 5.0 # MHz
        if f_mean < fs[0] + f_margin or f_mean > fs[-1] - f_margin:            
            print('fs error: peak center outside scan bounds.')
            return None
        f_sigma_min, f_sigma_max = 4, 16
        if f_sigma < f_sigma_min or f_sigma > f_sigma_max:
            print(
                'fs error: peak width outside bounds [{}] mhz'.format(
                    ', '.join(
                        '{:.1f}'.format(sigma) 
                        for sigma in 
                        (f_sigma_min,f_sigma_max)
                    )
                )
            )
            return None
        if x_amp < 0:
            print(
                'fs error: amplitude negative'
            )
            return None
        print('frequency scan successful.')        
        md['frequency scan'] = {
            'mean': (f_mean,'mhz'),
            'standard deviation': (f_sigma,'mhz'),
            'amplitude': (x_amp, 'v'),
            'offset': (x_off, 'v')
        }
        tcc.set_setpoint(f_mean)        
        return f_mean
    except RuntimeError:
        print('fs error: fit failed.')
        return None
    
def configure_lockin(lih,sens,deltat):
    lockin.set_time_constant(lih, deltat / taus)
    lockin.set_sensitivity(lih,sens)

def hwp_scan(
    md : dict, 
    f : float, fo : float, wo : float, 
    pih : pi.PIHandler,
    rsh : rotationstage.RotationStageHandler,
    wmh : wavemeter.WavemeterHandler,
    lih : lockin.LockinHandler,
    ic : topo.InstructionClient
):
    configure_lockin(lih,hwp_sens,hwp_deltat)
    update_metadata(md,lih)
    path = graphclient.add_dataset(
        [*g_folder,'hwp scans'],
        name_root(md),
        (
            'hwp angle (degs)',
            'lockin x (v)',
            'lockin y (v)',
            'photodiode (v)',
            'wavemeter (cm-1)'
        ),md
    )
    if hwp_mode is HWP_POL:
        phis = numpy.linspace(hwp_max,hwp_min,hwp_steps)
    else:
        raise Exception('other hwp modes not yet implemented!')
    for phi in phis:        
        for _ in move_laser(
            lid_reference + mirror_bolo_offset,
            phi, pih, rsh
        ): continue
        x, y, p, w = set_and_measure(
            f, fo, wo, wmh, lih, ic                
        )
        if debug:
            if hwp_mode is HWP_POL:
                x = debug_amp * 1 / 2 * (
                    1 + numpy.cos(
                        2 * numpy.pi * (
                            phi - phis.min()
                        ) / (phis.max() - phis.min())
                    )
                )
        graphclient.add_data(
            path,
            (phi,x,y,p,w)
        )
        print_data(
            'hwp scan data',
            (
                ('a',   phi,    1,  'degs'),
                ('x',   1e3*x,  3,  'mv'),
                ('y',   1e3*y,  3,  'mv'),
                ('p',   1e3*p,  3,  'mv'),                
            ), 'green'
        )

def angular_scan(
    md : dict,
    f : float, fo : float, wo : float, 
    pih : pi.PIHandler,
    rsh : rotationstage.RotationStageHandler,
    wmh : wavemeter.WavemeterHandler,
    lih : lockin.LockinHandler,
    ic : topo.InstructionClient, 
    rsh_t : rotationstage.RotationStageHandler
):
    configure_lockin(lih,as_sens,as_deltat)
    update_metadata(md,lih)
    lid_angles = numpy.arange(as_min,as_max,as_step).astype('float64')
    index = 0
    while index < len(lid_angles):
        if lid_angles[index] > lid_reference:
            break
        index += 1
    lid_angles = [
        *lid_angles[index:],
        *lid_angles[:index]
    ]    
    POL_HOR, POL_VER = 0, 1
    pols = (POL_HOR,POL_VER)
    pump_phis = {
        POL_HOR: pump_phi_hor,
        POL_VER: pump_phi_hor + (
            debug_dphi if debug else 45.0
        )
    }
    to = time.time()
    path = graphclient.add_dataset(
        [*g_folder, 'angular scans'],
        name_root(md),
        [
            'lid angle (degs)',
            *[
                '{} {}'.format(field,{POL_HOR:'hor',POL_VER:'ver'}[pol])
                for pol in pols for field in (
                    'lockin x (v)',
                    'lockin y (v)',
                    'photodiode (v)',
                    'wavemeter (cm-1)'
                )
            ], 'time elapsed (s)'                
        ],{
            'pump polarizations': {
                {
                    POL_HOR:'horizontal',
                    POL_VER:'vertical',
                }[pol]:(pump_phis[pol],'degs')
                for pol in pols
            },'start time':to,**md            
        }
    )   
    for lid_angle in lid_angles:
        data = [] 
        move_detector_gen = move_detector(
            lid_angle, hwp_reference, pih, rsh            
        )
        data.append(lid_angle)
        for pol in pols:
            pump_phi = pump_phis[pol]            
            unwind_generator(
                event_loop(
                    (
                        move_detector_gen,
                        rotationstage.set_angle_async(rsh_t,pump_phi)
                    )
                )
            )
            x, y, p, w = set_and_measure(
                f, fo, wo, 
                wmh, lih, ic
            )            
            if debug:
                x = {POL_HOR:1.0,POL_VER:1.5}[pol] * debug_amp * numpy.cos(
                    numpy.deg2rad(
                        lid_angle - debug_spec
                    )
                ) ** debug_exp
            data.extend([x,y,p,w])
            print_data(
                'as data (pol {})'.format(
                    {
                        POL_HOR:'h',POL_VER:'v'
                    }[pol]
                ),
                (
                    ('a',   lid_angle,      1,  'degs'  ),
                    ('x',   1e3*x,          3,  'mv'    ),
                    ('y',   1e3*y,          3,  'mv'    ),
                    ('p',   1e3*p,          3,  'mv'    ),                
                ), 'cyan'
            ) 
        data.append(time.time() - to)        
        graphclient.add_data(path,data)

def print_data(intro,clusters,color,width=15,tabs=0):
    print_color(        
        color,
        '{}{}. {}'.format(
            '\t' * tabs,
            intro, ''.join(
                '| {}: {} '.format(
                    label,
                    '{}{}'.format(
                        '{{:+.{:d}f}}'.format(
                            precision
                        ).format(
                            value
                        ), (
                            ' {}'.format(units) 
                            if units is not None else ''
                        )
                    ).rjust(width)
                ) for label, value, precision, units in 
                clusters
            )   
        )
    )

def main():    
    with (
        rotationstage.RotationStageHandler() as rsh,
        rotationstage.RotationStageHandler(
            typeid=rotationstage.TCUBE_DC_SERVO
        ) as rsh_t,
        wavemeter.WavemeterHandler() as wmh,
        lockin.LockinHandler() as lih,
        pi.PIHandler() as pih
    ): 
        try:
            ic = topo.InstructionClient()
            lines = read_lines(linefile)        
            for line in lines:
                trial = 0
                try:
                    while True:
                        try:                
                            # tune topo, get sensitivity measurement
                            fo, wo, sense_d = start_line(line,rsh,wmh)
                            with maxon.MaxonHandler() as mh:
                                chopper.set_blocking(mh,False) 
                            
                            # create metadata
                            md = get_metadata(line, sense_d, trial)

                            # line search
                            r = sense_d['measurement']['r'][0]            
                            if line_searching:
                                f_ls = line_search(md, r, fo, wo, wmh, lih, ic)    
                                if f_ls is None:
                                    print('line search failed. retrying.')
                                    trial += 1
                                    continue                               
                            else:
                                f_ls = 0.0
                            f = frequency_scan(md, f_ls, fo, wo, wmh, lih, ic)
                            if f is None:
                                print('frequency scan failed. retrying.')
                                trial += 1
                                continue                            
                            if hwp_installed:
                                hwp_scan(md, f, fo, wo, pih, rsh, wmh, lih, ic)
                            md['pump hwp'] = (
                                rotationstage.get_angle(rsh_t),'degrees'
                            )
                            angular_scan(md, f, fo, wo, pih, rsh, wmh, lih, ic, rsh_t)
                            break
                        except ModeHopException:
                            trial += 1
                            continue
                        except KeyboardInterrupt:
                            while True:   
                                response = input(
                                    '(n)ext line, (r)epeat, or (q)uit? : '
                                )
                                if response:
                                    code = response[0].lower()
                                    if code == 'q':
                                        raise QuitProgram()
                                    elif code == 'n':
                                        raise NextLine()
                                    elif code == 'r':
                                        print('restarting line.')
                                        trial += 1
                                        break
                                else:
                                    print('invalid response.')
                except NextLine:
                    print('continuing to next line.')
        except QuitProgram:
            print('program quit request received.')
        finally:
            print('quit sequence initiated. blocking beam.')
            with maxon.MaxonHandler() as mh:
                block_beam_blocking(mh)
            print('quitting.')

class QuitProgram(Exception): pass
class NextLine(Exception): pass

if __name__ == '__main__':
    main()