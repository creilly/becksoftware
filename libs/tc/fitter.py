from matplotlib import pyplot as plt
import numpy as np, time
from scipy.optimize import curve_fit
from tc import samplingrate

wavelength_hene = 0.6328 # um
wavelength_ir   = 3.3000 # um (nominal)

fsr = 300.0 # megahertz (nominal)

# sigmav / 2 is the voltage change required to go from 
# 100 % peak height to 100 x alpha % peak height
# i.e. if alpha = 1/2 then sigmav is FWHM
def signal_guess(vmax,vmin,deltav,sigmav,alpha):
    phi = np.pi * sigmav / deltav / 2
    b = (np.cos(phi)**2 - alpha) / (
        alpha * np.sin(phi)**2
    )
    a = (1 + b) * (vmax - vmin) / b
    c = vmax - a
    return a, b, c

def hene_calib(v,vtilde,vo,epsilon,delta,a,b,c):    
    eta = get_eta(v,vtilde,vo,epsilon,delta)
    return a / (
        1 + b * np.sin(
            np.pi * eta
        )**2
    ) + c

def get_hene_fit(a,b,c):
    def hene_fit(v,vtilde,vo,epsilon,delta):        
        return hene_calib(v,vtilde,vo,epsilon,delta,a,b,c)
    return hene_fit

def get_ir_calib(freqmod):
    if freqmod is None:
        return ir_calib
    else:
        return ir_calib_freqmod(freqmod)

# # 3f params
# deltafo = +8.98564159900431 # MHz
# phifo = +4.218448404825894
# 1f params (237 hz)
deltafo = 9.315 # 237 hz, 1.6 mod amp >> 8.25 # MHz
phifo = -0.007 # 237 hz >> 1.56 # rads
def ir_calib_freqmod(modfreq):
    def _ir_calib_freqmod(eta,f,beta,a,b,c,deltaf,phif):
        ts = np.arange(len(eta)) / samplingrate
        fs = f + deltaf * np.sin(
            2 * np.pi * modfreq * ts + phif
        )
        return ir_calib(
            eta,fs,beta,a,b,c
        )
    return _ir_calib_freqmod

def ir_calib(eta,f,beta,a,b,c):    
    return a / (
        1 + b * np.sin(
            np.pi * (
                f / fsr + beta * eta
            )
        )**2
    ) + c    

def get_eta(v,vtilde,vo,epsilon,delta):
    nu = (v-vtilde)/vo
    return nu + epsilon * nu**2 + delta * nu**3

def ir_calib_guess(
    mueta, Vmax, Vmin, deltaeta, sigmaeta, alpha
):
    beta = 1 / deltaeta 
    f = f_guess(mueta,beta)
    a, b, c = signal_guess(
        Vmax, Vmin, deltaeta, sigmaeta, alpha
    )
    return f, beta, a, b, c

def get_ir_fit(modfreq,beta,a,b,c,deltaf,phif):  
    if modfreq is None:  
        def ir_fit(eta,f):
            return ir_calib(eta,f,beta,a,b,c)
        return ir_fit
    _ir_calib_freqmod = ir_calib_freqmod(modfreq)
    def ir_fit_freqmod(eta,f):
        return _ir_calib_freqmod(
            eta,f,beta,a,b,c,deltaf,phif
        )
    return ir_fit_freqmod

def get_ir_fit_guess(beta):
    def ir_fit_guess(mueta):
        f = f_guess(mueta,beta)
        return f
    return ir_fit_guess

def f_guess(mueta,beta):
    return -fsr * mueta * beta

class Fitter:
    HENE = 0
    IR = 1
    def __init__(self,vs,modfreq):
        self.vs = vs
        self.modfreq = modfreq
        self.sigmas = 1 / np.diff(self.vs)**2
        self.sigmas = np.append(self.sigmas,self.sigmas[-1])        
        self.reset()

    def reset(self):
        self.henecalib = None        
        self.ircalib = None        
        self.etaparams = None
        self.f = None

    def get_etas(self):        
        return get_eta(self.vs,*self.etaparams)

    def update_hene(self,Vs):
        try:
            if self.henecalib is None:
                vtilde, vo, epsilon, delta, a, b, c = calibrate_hene(self.vs,Vs,self.sigmas)
                self.henecalib = (a,b,c)
                self.etaparams = (vtilde,vo,epsilon,delta)            
                self.henefit = get_hene_fit(a,b,c)            
            else:
                etaparams, cov = curve_fit(self.henefit,self.vs,Vs,self.etaparams,self.sigmas)
                self.etaparams = [*etaparams]
            return True
        except RuntimeError:
            return False

    def update_ir(self,Vs):
        try:
            if self.ircalib is None:
                f, *ps = calibrate_ir(
                    self.get_etas(),Vs,self.sigmas,modfreq=self.modfreq
                )
                self.ircalib = (self.modfreq,*ps)
                self.irfit = get_ir_fit(*self.ircalib)
                self.f = f
            else:
                (self.f,), cov = curve_fit(self.irfit,self.get_etas(),Vs,(self.f,),self.sigmas)            
            return True
        except RuntimeError:
            return False
    
def get_peaks(vs,Vs,alpha_low,alpha_high):
    Vmax = Vs.max()
    Vmin = Vs.min()

    # triggers peak start
    V_upper_thresh = alpha_high * (Vmax-Vmin) + Vmin
    # triggers peak end
    V_lower_thresh = alpha_low * (Vmax-Vmin) + Vmin

    # extract peaks
    peaks = []
    peak = ([],[])        
    peak_trigger = False
    valley_trigger = False
    sigmavs = []
    vpeaks = []
    Vpeak = Vmin        
    for v, V in zip(vs,Vs):            
        if valley_trigger:
            if V > V_upper_thresh:
                peak_trigger = True
                valley_trigger = False
        if peak_trigger:
            if V > V_upper_thresh:
                peak[0].append(v)
                peak[1].append(V)        
                if V > Vpeak:
                    Vpeak = V
                    vpeak = v
        if V < V_lower_thresh:
            if peak_trigger:
                sigmavs.append(
                    abs(peak[0][-1] - peak[0][0])
                )
                vpeaks.append(vpeak)
                Vpeak = Vmin
                peaks.append(peak)
                peak = [[],[]]            
                peak_trigger = False
            valley_trigger = True
    return peaks, vpeaks, sigmavs

def calibrate_hene(vs,Vs,sigmas,debug=False):    
    Vmax = Vs.max()
    Vmin = Vs.min()

    f_upper_thresh = 0.7    
    f_lower_thresh = 0.3    

    peaks, vpeaks, sigmavs = get_peaks(vs,Vs,f_lower_thresh,f_upper_thresh)

    # extract peak parameters
    voo = abs(np.average(np.diff(vpeaks)))
    def fit(v,vo,a,b):
        return a / (1 + b * (np.pi * (v-vo) / voo)**2) + Vmin
    vpos, bos = [], []    
    for (vps, Vps), sigmav, vpeak in zip(peaks,sigmavs,vpeaks):
        vps = np.array(vps)
        Vps = np.array(Vps)        
        
        # estimate fit parameters
        phi = np.pi * sigmav / voo / 2
        bo = (np.cos(phi)**2 - f_upper_thresh) / (
            f_upper_thresh * np.sin(phi)**2
        )        
        ao = Vmax - Vmin
        
        guess = (
            vpeak,ao,bo
        )

        fitvps = np.linspace(vps.min(),vps.max(),100)        
        try:            
            ps, _ = curve_fit(fit,vps,Vps,guess)
        except RuntimeError:
            plt.plot(vps,Vps,'.',color='black')
            plt.plot(fitvps,fit(fitvps,*guess),color='red')
            plt.show()
            raise

        vpo, ao, bo = ps 
        
        bos.append(bo)        
        vpos.append(vpo)    
        if debug:
            plt.plot(vps,Vps,'.',color='black')
            plt.plot(fitvps,fit(fitvps,*guess),color='red')
            plt.plot(fitvps,fit(fitvps,*ps),color='blue')
    if debug:
        plt.xlabel('piezo voltage (v)')
        plt.ylabel('hene detector voltage (v)')
        plt.plot([],[],color='red',label='guess')
        plt.plot([],[],color='blue',label='fit')
        plt.legend()
        plt.title('peak processing')
        plt.show()

    # get peak closest to v = 0
    vtilde = min(vpos,key=abs)

    # model the peak locations via the function
    #   eta = a * vp + b * vp**2 + c * vp**3
    # where
    #   vp = v - vtilde
    # and
    #   eta = n
    # for v = vn
    # where vn is the nth peak location
    # to use polyfit for parameter (i.e. a, b, c) estimation
    # we first derive the above equation:
    #   d eta / d vp = a + 2 * b * vp + 3 * c * vp**2
    # where halfway between the nth and (n+1)th peak, i.e. 
    # at vp = 1 / 2 * ( v_n + v_(n+1) ) - vtilde, we have
    #   d eta / d vp = 1 / (v_(n+1) - v_n)
    vpos -= vtilde
    vpos = np.array(sorted(vpos))
    dvdms = np.diff(vpos)    
    dmdVs = 1/dvdms
    vpps = vpos[:-1] + dvdms / 2
    cp, bp, ap = np.polyfit(vpps,dmdVs,2)
    c = cp / 3
    b = bp / 2
    a = ap
    # convert a, b, c poly parameters to
    #   eta = nu + epsilon * nu**2 + delta * nu**3
    # where:
    #   nu = (v - vtilde) / vo
    voop = 1 / a
    epsilono = b / a**2
    deltao = c / a**3
    
    if debug:
        # sanity check:
        # if fit was successful, then the different 
        # between best fit eta values at adjacent peaks 
        # should be close to one:
        nus = vpos / voop
        etas = nus + epsilono * nus**2 + deltao * nus**3  
        detas = np.diff(etas)
        print(
            'delta etas:',', '.join(map('{:.6f}'.format,detas)),
            
        )
        print(
            'mean:',
            '{:.6f}'.format(np.average(detas)),
            ',',
            'std:',
            '{:.6f}'.format(np.std(detas))
        )
    
    # global fit (see hene_calib)
    # correct b estimation for improved vo estimation
    bo = np.average(bos) * (voop/voo)**2    
    ao = (1 + bo) / bo * (Vmax - Vmin)    
    co = Vmax - ao

    guess = (
        vtilde, voop, epsilono, deltao, ao, bo, co
    )    

    ps, covs = curve_fit(hene_calib,vs,Vs,guess,sigmas)

    if debug:
        fitvs = np.linspace(vs.min(),vs.max(),500)        
        plt.plot(vs,Vs,'.',color='black',label='data')
        plt.plot(fitvs,hene_calib(fitvs,*guess),color='red',label='guess')    
        plt.plot(fitvs,hene_calib(fitvs,*ps),color='blue',label='fit')
        plt.legend()
        plt.xlabel('piezo voltage (v)')
        plt.ylabel('hene detector voltage (v)')
        plt.title('global hene calibration')
        plt.show()

    return ps

dt = 5.0
td = {
    't':time.time()
}
def calibrate_ir(etas,Vs,sigmas,modfreq,debug=False):

    Vmax = Vs.max()
    Vmin = Vs.min()

    f_upper_thresh = 0.9
    f_lower_thresh = 0.7    

    # 2024-11-05 - commented out to tailor to low-finesse nh3 data
    # vvvv start of old code optimized for ch4
    # peaks, etaos, sigmaetas = get_peaks(etas,Vs,f_lower_thresh,f_upper_thresh)
    # guess = ir_calib_guess(
    #     min(etaos,key=abs),Vmax,Vmin,
    #     np.average(
    #         np.diff(
    #             sorted(etaos)
    #         )
    #     ),np.average(sigmaetas),f_upper_thresh
    # )
    # ^^^^ end of old code optimized for ch4
    # vvvv start of new code for nh3
    def cosine_fit(etas,etao,deltaeta,amp,offset):
        return offset + amp * np.cos(
            2 * np.pi * (etas-etao) / deltaeta
        )
    
    etaoo = etas[Vs.argmax()]    
    deltaetao = 4.5
    ampo = (Vmax-Vmin)/2
    offseto = np.average(Vs)
    guess = (etaoo,deltaetao,ampo,offseto)
    tp = time.time()
    printing = tp > td['t'] + dt
    if printing:
        td['t']= tp
    cf_ps, cf_cov = curve_fit(cosine_fit,etas,Vs,guess,sigmas)    
    etao, deltaeta, amp, offset = cf_ps
    if debug:
        pass
        # plt.plot(etas,Vs,'.')
        # plt.plot(etas,cosine_fit(etas,*cf_ps))
        # plt.show()
    
    etal, etar = etas[0], etas[-1]
    etamin, etamax = (etal, etar) if etal < etar else (etar,etal)
    etaos = [etao]
    eta = etao
    while True:
        eta -= deltaeta
        if eta < etamin:
            break
        etaos.append(eta)
    eta = etao
    while True:
        eta += deltaeta
        if eta > etamax:
            break
        etaos.append(eta)
    alpha = 1/2
    guess = ir_calib_guess(
        min(etaos,key=abs),Vmax,Vmin,
        deltaeta,deltaeta/2,3*alpha/4
    )
    # ^^^^ end of new code for nh3
    # 2024-11-05 end of nh3 hacks    
    
    # else:
    #     guess = (
    #         min(etaos,key=abs),
    #         0.19239455149064008,
    #         0.5462827457521472,
    #         12.095687755849534,
    #         -0.0036259765403136696,
    #     )
    if modfreq is None:
        if debug:
            print(guess)
            plt.plot(etas,Vs,'.')
            plt.plot(etas,ir_calib(etas,*guess),'.')
            plt.show()
            return
        ps, cov = curve_fit(
            ir_calib,etas,Vs,guess,sigmas
        )
        ps = (*ps,None,None)        
    else:
        guess = (*guess,deltafo,phifo)
        # guess = (*guess,8.890269050976588,+2.48449)        
        # vvv commented out 2024-11-08
        # ps, cov = curve_fit(
        #     ir_calib_freqmod(modfreq),etas,Vs,guess,sigmas            
        # )
        # if printing:
        #     print(', '.join(map('{:.3e}'.format,ps)))
        # ^^^ commented out 2024-11-08
        # vvv added 2024-11-08
        # deltaf, phif = 22.3 / 2.5, 2.169 # at 244.75 hz
        deltaf, phif = 19.55 / 2, 1.00 # at 734.25 hz
        fitf = ir_calib_freqmod(modfreq)
        def fitfp(*args):
            return fitf(*args,deltaf,phif)
        ps, cov, infod, *_ = curve_fit(
            fitfp,etas,Vs,guess[:-2],sigmas,
            maxfev=500000,full_output=True
        )        
        ps = [*ps,deltaf,phif]
        # ^^^ added 2024-11-08

    if debug:        
        pass
        # raise NotImplementedError()
        # fitetas = np.linspace(etas.min(),etas.max(),1000)
        # print('ir ps',ps)
        # plt.plot(etas,Vs,'.',color='black',ms=1,label='data')
        # plt.plot(fitetas,ir_calib(fitetas,*guess),color='red',label='guess')
        # plt.plot(fitetas,ir_calib(fitetas,*ps),color='blue',label='fit')
        # plt.xlabel('etas (unitless)')
        # plt.ylabel('ir detector (v)')
        # plt.title('ir calibration')
        # plt.legend()
        # plt.show()

    return ps