import numpy as np
from matplotlib import pyplot as plt
import numpy.linalg as la
from timeit import default_timer as clock
import numba

dt = 1e-3
Cmin = 5
Cmax = 6
Tmin = Cmin * 2 * np.pi
Tmax = Cmax * 2 * np.pi
delta = 4
omegao = 1
T2 = 1
tau = 1
# domegao = 1 / np.sqrt(tau * T2)
domegao = 10
M = 1000

np.random.seed()

@numba.jit(nopython=True)
def numba_inv(A):
    return np.linalg.inv(A)

@numba.jit(nopython=True)
def numba_eig(A):
    return np.linalg.eig(A)

def get_trajectory_eff(T,omegao,delta,domegao,tau):

    T2 = 1/(domegao**2 * tau)

    H = np.array(
        [
            [
                0, 0, -omegao
            ],[
                0, -1/T2, +delta
            ],[
                +omegao, -delta, -1/T2
            ]
        ],
        dtype='complex128'
    )

    evals, p = np.linalg.eig(H)
    
    # evals, p = np.linalg.eig(
    #     (
    #         (
    #             0, 0, -omegao
    #         ),
    #         (
    #             0, -1/T2, +delta
    #         ),
    #         (
    #             +omegao, -delta, -1/T2
    #         )
    #     )
    # )
    pinv = np.linalg.inv(p)

    ro = (-1,0,0)
    
    ts = np.linspace(0,T,100)

    return ts, np.real(
        np.einsum(
            'ij,mj,jl,l->im',
            p,np.exp(
                np.einsum(
                    'm,j->mj',
                    ts,evals
                )
            ),pinv,ro
        )[0]
    )

def get_energy_eff(T,omegao,delta,domegao,tau):
    T2 = 1/(domegao**2 * tau)

    evals, p = numba_eig(
        np.array(
            (
                (
                    0, 0, -omegao
                ),
                (
                    0, -1/T2, +delta
                ),
                (
                    +omegao, -delta, -1/T2
                )
            ),
            dtype='complex128'
        )
    )
    pinv = numba_inv(p)

    ro = (-1,0,0)
    
    return (
        1 + np.real(
            np.einsum(
                'ij,j,jl,l',
                p,np.exp(
                    T*evals
                ),pinv,ro
            )[0]
        )
    ) / 2

def get_trajectory_eff_slow(dt,T,omegao,delta,domegao,tau):
    T2 = 1/(domegao**2 * tau)

    tmarker = 0
    t = 0
    
    z = -1
    y = 0
    x = 0

    ts = []
    zs = []

    while t < T:

        if t >= tmarker:
            ts.append(t)
            zs.append(z)
            tmarker += T / 200
        
        z += -omegao * y * dt
        x += ( delta * y - 1 / T2 * x ) * dt
        y += ( omegao * z - delta * x - 1 / T2 * y ) * dt
        t += dt

    return np.array(ts), np.array(zs)

def get_trajectory(dt,T,omegao,delta,domegao,tau):
    N = tau / dt
    stdomega = domegao * np.sqrt(2 * N)

    tmarker = 0
    t = 0
    
    z = -1
    y = 0
    x = 0
    
    domega = np.random.normal(0,stdomega)

    ts = []
    zs = []

    while t < T:

        if t >= tmarker:
            ts.append(t)
            zs.append(z)
            tmarker += T / 100

        z += -omegao * y * dt
        x += ( delta + domega ) * y * dt
        y += ( omegao * z - ( delta + domega) * x ) * dt

        domega += (np.random.normal(0,stdomega)-domega) / N
        
        t += dt

    return np.array(ts), np.array(zs)

def get_trajectory_uni(dt,T,omegao,delta,domegao,tau):
    N = tau / dt
    omegabdy = domegao * np.sqrt(6 * N)

    tmarker = 0
    t = 0
    
    z = -1
    y = 0
    x = 0
    
    domega = np.random.uniform(-omegabdy,+omegabdy)

    ts = []
    zs = []

    while t < T:

        if t >= tmarker:
            ts.append(t)
            zs.append(z)
            tmarker += T / 100

        z += -omegao * y * dt
        x += ( delta + domega ) * y * dt
        y += ( omegao * z - ( delta + domega) * x ) * dt

        domega += (np.random.uniform(-omegabdy,+omegabdy)-domega) / N
        
        t += dt

    return np.array(ts), np.array(zs)

def get_trajectory_rk(dt,T,wo,delta,dwo,tau):

    N = tau / dt
    stdw = dwo * np.sqrt(2 * N)

    def drdt(r,f,dwp):
        z,x,y,dw = r

        ddwdt = (dwp-dw)/N
        dwpp = dw + f * ddwdt

        dzdt = -wo * y
        dxdt = ( delta + dwppp ) * y
        dydt = wo * z - ( delta + dwppp ) * x

        return np.array([dzdt,dxdt,dydt,ddwdt])
    
    t = 0
    tmarker = 0
    
    z = -1.0
    y = 0.0
    x = 0.0
    dw = np.random.normal(0,stdomega)

    r = np.array([z,y,x,dw])

    ts = []
    zs = []
    
    while t < T:

        if t >= tmarker:            
            ts.append(t)
            zs.append(r[0])
            t += T / 100
            
        dwp = np.random.normal(0,stdw)
        
        k1 = drdt(r,0,dwp)
        k2 = drdt(r+k1/2*dt,1/2,dwp)
        k3 = drdt(r+k2/2*dt,1/2,dwp)
        k4 = drdt(r+k3*dt,1,dwp)

        r += (k1+2*k2+2*k3+k4)/6*dt        
        t += dt

    return np.array(ts), np.array(zs)

def get_trajectory_both(dto,factors,T,wo,delta,dwo,tau):
    
    def drdt(r,n):
        z,x,y = r

        dw = dws[n]

        dzdt = -wo * y
        dxdt = ( delta + dw ) * y
        dydt = wo * z - ( delta + dw ) * x

        return np.array([dzdt,dxdt,dydt])
    
    trajs = {}

    dt = dto / 2
    N = tau / dt
    stdw = dwo * np.sqrt(2 * N)
    dw = np.random.normal(0,stdw)
    dws = []

    t = 0
    while t < 2*T:
        dws.append(dw)
        dw += (np.random.normal(0,stdw) - dw)/N
        t += dt
        
    for factor in factors:
        dt = dto * factor
        n = 0
        t = 0
        tmarker = 0

        z = -1.0
        y = 0.0
        x = 0.0

        r = np.array([z,x,y])
        rrot = np.array([z,x,y])

        ts = []
        
        zs = []
        zrks = []
        zrots = []

        clockz = 0
        clockzrk = 0
        clockzrot = 0

        while t < T:

            if t >= tmarker:            
                ts.append(t)
                zs.append(z)
                zrks.append(r[0])
                zrots.append(rrot[0])
                tmarker += T / 100

            dw = dws[factor * 2*n]

            tstart = clock()

            z += -wo * y * dt
            x += ( delta + dw ) * y * dt
            y += ( wo * z - ( delta + dw) * x ) * dt

            clockz += clock() - tstart

            tstart = clock()            

            w = np.array([delta+dw,omegao,0])
            w2 = w.dot(w)
            modw = np.sqrt(w2)
            phi = modw*dt
            rrot += (rrot-w.dot(rrot)/w2*w)*(np.cos(phi)-1) + np.cross(w,rrot)/modw*np.sin(phi)

            clockzrot += clock() - tstart

            tstart = clock()

            k1 = drdt(r,factor * 2*n)
            k2 = drdt(r+k1/2*dt,factor * (2*n + 1))
            k3 = drdt(r+k2/2*dt,factor * (2*n + 1))
            k4 = drdt(r+k3*dt,factor * (2*n + 2))

            r += (k1+2*k2+2*k3+k4)/6*dt

            clockzrk += clock() - tstart
            
            t += dt
            n += 1

        trajs[dt] = [np.array(ts), np.array(zs), np.array(zrks), np.array(zrots), (clockz,clockzrk,clockzrot)]
    return trajs

def get_energy(dt,T,omegao,delta,domegao,tau):
    
    N = tau / dt

    stdomega = domegao * np.sqrt(2 * N)
    
    t = 0
    
    z = -1
    y = 0
    x = 0
    
    domega = np.random.normal(0,stdomega)

    while t < T:
        
        z += -omegao * y * dt
        x += ( delta + domega ) * y * dt
        y += ( omegao * z - ( delta + domega) * x ) * dt

        domega += ( np.random.normal(0,stdomega) - domega ) / N
        
        t += dt

    return (z+1)/2

def get_energy_uni(dt,T,omegao,delta,domegao,tau):
    
    N = tau / dt

    omegabdy = domegao * np.sqrt(6 * N)
    
    t = 0
    
    z = -1
    y = 0
    x = 0
    
    domega = np.random.uniform(-omegabdy,+omegabdy)

    while t < T:
        
        z += -omegao * y * dt
        x += ( delta + domega ) * y * dt
        y += ( omegao * z - ( delta + domega) * x ) * dt

        domega += ( np.random.uniform(-omegabdy,+omegabdy) - domega ) / N
        
        t += dt

    return (z+1)/2

def get_energy_rk(dt,T,wo,delta,dwo,tau):

    N = tau / dt

    stdw = dwo * np.sqrt(2 * N)

    def drdt(r,t,dwp):
        z,x,y,dw = r

        dzdt = -wo * y
        dxdt = ( delta + dw ) * y
        dydt = wo * z - ( delta + dw ) * x
        ddwdt = (dwp-dw)/N

        return np.array([dzdt,dxdt,dydt,ddwdt])
    
    t = 0
    
    z = -1.0
    y = 0.0
    x = 0.0
    dw = np.random.normal(0,stdomega)

    r = np.array([z,y,x,dw])
    
    while t < T:
        dwp = np.random.normal(0,stdw)
        
        k1 = drdt(r,t,dwp)
        k2 = drdt(r+k1/2*dt,t+dt/2,dwp)
        k3 = drdt(r+k2/2*dt,t+dt/2,dwp)
        k4 = drdt(r+k3*dt,t+dt,dwp)

        r += (k1+2*k2+2*k3+k4)/6*dt        
        t += dt

    return (r[0]+1)/2
Id = np.array(
    (
        (
            1.0,0,0
        ),(
            0,1.0,0
        ),(
            0,0,1.0
        )
    )
)

dAt = np.array(
    (
        (
            0,0,0
        ),(
            0,0,+1.0
        ),(
            0,-1.0,0
        )
    )
)

@numba.jit(nopython=True)
def get_avg_trajectory_uni_imp(M,dt,T,wo,delta,dwo,tau):
    N = tau / dt

    Ao = np.array(
        (
            (
                0,0,-wo
            ),(
                0,0,+delta
            ),(
                +wo,-delta,0
            )
        )
    )

    wbdy = dwo * np.sqrt(6 * N)

    ts = np.arange(100)*T/100
    zs = np.zeros(100)
    for _ in range(M):
        t = 0
        tmarker = 0

        z = -1.0
        y = 0.0
        x = 0.0

        r = np.array((z,x,y),dtype='float64')
        dw = np.random.uniform(-wbdy,+wbdy)
        dAo = dw * dAt

        n = 0
        while t < T:
            if t >= tmarker:
                zs[n] += r[0] / M
                tmarker+=T/100
                n += 1

            dw += ( np.random.uniform(-wbdy,+wbdy) - dw ) / N

            dAp = dw * dAt

            Bmin = Id - dt/2 * (Ao+dAp)

            Bplus = Id + dt/2 * (Ao+dAo)

            Bmininv = np.linalg.inv(Bmin)

            Bprod = Bmininv.dot(Bplus)

            r = Bprod.dot(r)

            dAo = dAp

            t += dt
        
    return ts, zs

@numba.jit(nopython=True)
def get_trajectory_imp_rap(dt,T,wo,delta,dwo):
    Ao = np.array(
        (
            (
                0,0,-wo
            ),(
                0,0,+delta
            ),(
                +wo,-delta,0
            )
        )
    )

    ts = np.arange(100)*T/100
    zs = np.zeros(100)

    t = 0
    tmarker = 0

    z = -1.0
    y = 0.0
    x = 0.0

    r = np.array((z,x,y),dtype='float64')
    dw = -dwo/2
    dAo = dw * dAt

    n = 0
    while t < T:
        if t >= tmarker:
            zs[n] += r[0]
            tmarker+=T/100
            n += 1

        dw += dwo*dt/T

        dAp = dw * dAt

        Bmin = Id - dt/2 * (Ao+dAp)

        Bplus = Id + dt/2 * (Ao+dAo)

        Bmininv = np.linalg.inv(Bmin)

        Bprod = Bmininv.dot(Bplus)

        r = Bprod.dot(r)

        dAo = dAp

        t += dt
        
    return ts, zs

@numba.jit(nopython=True)
def get_energy_imp_rap(dt,T,wo,delta,dwo):
    Ao = np.array(
        (
            (
                0,0,-wo
            ),(
                0,0,+delta
            ),(
                +wo,-delta,0
            )
        )
    )

    t = 0

    z = -1.0
    y = 0.0
    x = 0.0

    r = np.array((z,x,y),dtype='float64')
    dw = -dwo/2
    dAo = dw * dAt

    while t < T:

        dw += dwo*dt/T

        dAp = dw * dAt

        Bmin = Id - dt/2 * (Ao+dAp)

        Bplus = Id + dt/2 * (Ao+dAo)

        Bmininv = np.linalg.inv(Bmin)

        Bprod = Bmininv.dot(Bplus)

        r = Bprod.dot(r)

        dAo = dAp

        t += dt
        
    return ( r[0] + 1 ) / 2

def get_trajectory_uni_imp_both(dt,T,wo,delta,dwo,tau):
    N = tau / dt

    Ao = np.array(
        (
            (
                0,0,-wo
            ),(
                0,0,+delta
            ),(
                +wo,-delta,0
            )
        )
    )

    wbdy = dwo * np.sqrt(6 * N)
    
    t = 0
    tmarker = 0
    
    z = -1
    y = 0
    x = 0

    r = np.array((z,x,y))
    dw = np.random.uniform(-wbdy,+wbdy)
    dAo = np.array(
        (
            (
                0,0,0
            ),(
                0,0,+dw
            ),(
                0,-dw,0
            )
        )
    )
    ts = []
    zexps = []
    zimps = []

    texp = 0
    timp = 0
    while t < T:
        if t >= tmarker:
            ts.append(t)
            zexps.append(z)
            zimps.append(r[0])
            tmarker+=T/100

        start = clock()
        
        z += -wo * y * dt
        x += ( delta + dw ) * y * dt
        y += ( wo * z - ( delta + dw) * x ) * dt
        
        texp += clock() - start
        
        dw += ( np.random.uniform(-wbdy,+wbdy) - dw ) / N
        
        start = clock()
        
        dAp = np.array(
            (
                (
                    0,0,0
                ),(
                    0,0,+dw
                ),(
                    0,-dw,0
                )
            )
        )
        r = np.linalg.inv(Id-dt/2*(Ao+dAp)).dot(Id+dt/2*(Ao+dAo)).dot(r)
        dAo = dAp
        
        timp += clock() - start
        
        t += dt
    print('texp:',texp,'timp:',timp)
    return np.array(ts), np.array(zexps), np.array(zimps)

def get_energy_uni_imp(dt,T,wo,delta,dwo,tau):
    N = tau / dt

    Ao = np.array(
        (
            (
                0,0,-wo
            ),(
                0,0,+delta
            ),(
                +wo,-delta,0
            )
        )
    )

    wbdy = dwo * np.sqrt(6 * N)
    
    t = 0
    
    z = -1.0
    y = 0.0
    x = 0.0

    r = np.array((z,x,y))
    dw = np.random.uniform(-wbdy,+wbdy)
    dAo = np.array(
        (
            (
                0,0,0
            ),(
                0,0,+dw
            ),(
                0,-dw,0
            )
        )
    )

    while t < T:
        dw += ( np.random.uniform(-wbdy,+wbdy) - dw ) / N        
        dAp = np.array(
            (
                (
                    0,0,0
                ),(
                    0,0,+dw
                ),(
                    0,-dw,0
                )
            )
        )
        r = np.linalg.inv(Id-dt/2*(Ao+dAp)).dot(Id+dt/2*(Ao+dAo)).dot(r)
        dAo = dAp        
        t += dt
    return 1/2*(r[0]+1)

# taus = [1e-2,2e-2,5e-2,1e-1,2e-1,5e-1,1e-0,2e-0,5e-0,1e+1]
# for tau in taus:
#     domegaos = [1,2,5,10,20,50,100]
#     energies = []
#     for domegao in domegaos:
#         deltas = np.linspace(0,4,30)
#         energy = 0
#         for delta in deltas:
#             print(tau,domegao,delta)
#             for m in range(M):
#                 energy += get_energy(1e-3 if tau < 5e-2 else dt,np.random.uniform(Tmin,Tmax),omegao,delta,domegao,tau) / M / len(deltas)
#         energies.append(energy)
#     plt.plot(domegaos,energies,label=r'$\tau = {:5.0e}$'.format(tau))
# plt.xlabel(r'$\Delta \omega_o$ (rabi freqs)')
# plt.ylabel(r'average energy ($h \nu$)')
# plt.xscale('log')
# plt.title('excitation vs. rms frequency noise (doppler width = 4x rabi freq, T = 6 rabi cycles)',fontsize=8)
# plt.legend(fontsize=8)
# plt.show()

# taus = [.01,.03,.1,.3,1,3,10]
# first = True
# for index, tau in enumerate(taus):
#     print(tau)
#     domegao = 1 / np.sqrt(T2*tau)
#     deltat = min(tau,omegao) / 100
#     teffs, zeffs = get_trajectory_eff(deltat,Tmax,omegao,delta,domegao,tau)
#     if first:
#         plt.plot(teffs,zeffs,label = 'T2 eff',color=[0.0,0.0,0.0],zorder=2)
#         first = False
#     Ts, Zs = 0.0, 0.0
#     for _ in range(M):
#         Ts, zs = get_trajectory(deltat,Tmax,omegao,delta,domegao,tau)
#         Zs += zs
#     plt.plot(
#         Ts,Zs/M,
#         label = '{:5.0e}'.format(tau),
#         color = (
#             np.ones(3)
#             -
#             1/3*(
#                 (len(taus)-index)
#                 /
#                 len(taus)
#                 +
#                 1
#             )*np.array(
#                 [index%2,1,(index+1)%2]
#             )
#         ),
#         zorder=1
#     )
# plt.xlabel('time (inverse rabi frequencies)')
# plt.ylabel(r'$\langle \sigma_z(t) \rangle$')
# plt.title(r'$T_2$ approximation accuracy')
# plt.legend()
# plt.show()
# trajs = get_trajectory_both(
#     .001,[1,2,5,10,20,50,100],Tmax,omegao,delta,domegao,tau
# )
# for dt, (ts, zs, zrks, zrots, (clockz, clockzrk, clockzrot)) in trajs.items():
#     print(dt, clockz, clockzrk, clockzrot)
#     color = plt.plot(ts,zs,'.')[0].get_color()
#     plt.plot(ts,zrks,color=color,label='{:g}'.format(dt))
# plt.legend()
# plt.xlabel(r'time ($\Omega^{-1}$)')
# plt.ylabel(r'$\sigma_z$')
# plt.title(
#     '\n'.join(
#         (
#             'trajs for diff. dt (lines=w/rot)',
#             '$\\Delta=%g$, $\\Delta \\omega_o = %g$, $\\Delta \\omega_{bw}=%g$' % (
#                 delta,domegao,1/tau
#             )
#         )
#     )
# )
# plt.ylim(ymin=-1.5,ymax=+1.5)
# plt.show()
# trajnorm = 0
# trajuni = 0
# normtime = 0
# unitime = 0
# for _ in range(M):
#     print(_)
#     start = clock()
#     ts, dtraj = get_trajectory(dt,Tmax,omegao,delta,domegao,tau)
#     normtime += clock() - start

#     trajnorm += dtraj / M
    
#     start = clock()
#     ts, dtraj = get_trajectory_uni(dt,Tmax,omegao,delta,domegao,tau)
#     unitime += clock() - start

#     trajuni += dtraj / M
# print(normtime,unitime)
# plt.plot(ts,trajnorm,label='norm ({:d}s)'.format(round(normtime)))
# plt.plot(ts,trajuni,label='uni ({:d}s)'.format(round(unitime)))
# plt.xlabel(r'time ($\Omega^{-1}$)')
# plt.ylabel(r'$\langle \sigma_z \rangle$')
# plt.title('normal noise vs. uniform noise, %d samples' % M)
# plt.legend()
# plt.show()

# taus = [.03,.1,.3,1.,3.,10.]
# domegaos = [.01,.1,.2,.5,1.,2.,5.,10.,20.,50.]
# for tau in taus:
#     fractions = []
#     errfractions = []
#     for domegao in domegaos:
#         fraction = 0
#         fraction2 = 0
#         errors = 0
#         for _ in range(M):
#             f = get_energy_uni_imp(
#                 min(
#                     tau,1/domegao,1/delta,1/omegao
#                 ) / 2,
#                 np.random.uniform(Tmin,Tmax),
#                 omegao,
#                 min(np.abs(np.random.normal(0,delta)),3*delta),
#                 domegao,
#                 tau
#             )
#             if f < 0 or f > 1:
#                 errors += 1
#             fraction += f / M
#             fraction2 += f**2 / M
#         print(tau,domegao,'errors:',errors)
#         fractions.append(fraction)
#         errfractions.append(np.sqrt((fraction2-fraction**2)/M))
#     plt.errorbar(domegaos,fractions,errfractions,label=r'$%g$' % tau)
# plt.xscale('log')
# plt.xlabel(r'RMS noise $\Delta \omega_o$ ($\Omega$)')
# plt.ylabel('excitation fraction')
# plt.ylim(ymin=-.1,ymax=.8)
# plt.legend(title=r'$\tau$ ($\Omega^{-1}$)')
# plt.title(
#     '\n'.join(
#         (
#             'power curves, low noise, no relax approx',
#             r'$\Delta = %g \Omega$, $T = 2 \pi \times %g \Omega^{-1}$' % (delta, Cmax)
#         )
#     )
# )
# plt.savefig('2021-04-23/power-curves-uni-imp-no-approx-long-dt.svg')
# plt.savefig('2021-04-23/power-curves-uni-imp-no-approx-long-dt.png')
# plt.show()

# taus = [.01,.03,.1,.3,1,3,10]
# first = True
# for index, tau in enumerate(taus):
#     print(tau)
#     domegao = 1 / np.sqrt(T2*tau)
#     deltat = min(tau,1/omegao,1/domegao,1/delta) / 10
#     if first:
#         teffs, zeffs = get_trajectory_eff(Tmax,omegao,delta,domegao,tau)
#         plt.plot(teffs,zeffs,label = r'$\frac{1}{\infty}$',color=[0.0,.5,0.0],zorder=2)
#         first = False
#     ts, zs = get_avg_trajectory_uni_imp(M,deltat,Tmax,omegao,delta,domegao,tau)
#     plt.plot(
#         ts,zs,
#         label = '{:g}'.format(tau),
#         color = (
#             np.ones(3)
#             -
#             1/3*(
#                 (len(taus)-index)
#                 /
#                 len(taus)
#                 +
#                 1
#             )*np.array(
#                 [index%2,1,(index+1)%2]
#             )
#         ),
#         zorder=1
#     )
# plt.xlabel('time (inverse rabi frequencies)')
# plt.ylabel(r'$\langle \sigma_z(t) \rangle$')
# plt.title(
#     '\n'.join(
#         (
#             r'$T_2$ approximation accuracy',
#             r'$T_2 = %d \Omega^{-1}$, $\Delta = %g \Omega$' % (T2,delta)
#         )
#     )
# )
# plt.legend(title=r'$\tau$')
# plt.show()

# delta = 1
# Cmin = 15
# Cmax = 25
# Tmin = 2 * np.pi * Cmin
# Tmax = 2 * np.pi * Cmax
# omegaos = np.power(10,np.linspace(-1,1,30))
# domegaos = [.1,.2,.5,1,2,5,10]
# tau = 0.2
# M = 10000
# first = True
# time = 0
# for domegao in domegaos:
#     energies = []
#     for omegao in omegaos:
#         print(domegao,omegao)
#         energy = 0
#         start = clock()
#         for _ in range(M):
#             energy += get_energy_eff(
#                 np.random.uniform(Tmin,Tmax),
#                 omegao,
#                 np.random.normal(0,delta),
#                 domegao,
#                 tau
#             ) / M
#         if first:
#             first = False
#         else:
#             time += clock() - start            
#         energies.append(energy)
#     plt.plot(omegaos,energies,label='%g'%domegao)
# print(time)
# plt.xscale('log')
# plt.xlabel(r'$\Omega$ ($\Delta$)')
# plt.ylabel('excitation fraction')
# plt.title(
#     '\n'.join(
#         (
#             'fluence curves',
#             r'$\tau = %g \Delta^{-1}$, $T = 2 \pi \times %d \Delta^{-1}$' % (tau,(Cmin+Cmax)/2)
#         )
#     )
# )
# plt.legend(title=r'$\Delta \omega_o (\Delta)$')
# plt.show()

# tau = 0.2
# deltao = 4
# omegao = 1
# Cmin = 4
# Cmax = 8
# Tmin = Cmin * 2 * np.pi
# Tmax = Cmax * 2 * np.pi
# M = 1000

# domegaos = [.1,.2,.5,1,2,5,10,20]
# deltas = np.linspace(0,deltao,20)
# for domegao in domegaos:
#     fractions = []
#     for delta in deltas:
#         print(domegao,delta)
#         fraction = 0
#         for _ in range(M):
#             fraction += get_energy_eff(
#                 np.random.uniform(Tmin,Tmax),
#                 omegao,
#                 delta,
#                 domegao,
#                 tau
#             ) / M
#         fractions.append(fraction)
#     plt.plot(deltas,fractions,label='%g'%domegao)
# plt.xlabel(r'$\Delta (\Omega)$')
# plt.ylabel('excitation fraction')
# plt.title(
#     '\n'.join(
#         (
#             'excitation versus doppler detuning',
#             r'$\tau=%g \Omega^{-1}$, $T = 2 \pi \times 6 \Omega^{-1}$' % (tau,)
#         )
#     )
# )
# plt.legend(title=r'$\Delta \omega_o (\Omega)$')
# plt.show()

# Cmin = 4
# Cmax = 8
# Tmin = Cmin * 2 * np.pi
# Tmax = Cmax * 2 * np.pi
# wo = 1
# delta = 0
# dwo = 4
# dt = 1 / np.sqrt(
#     delta**2 + wo**2 + dwo**2
# ) / 10
# ts, zs = get_trajectory_imp_rap(dt,Tmax,wo,delta,dwo)
# plt.plot(ts,zs)
# plt.xlabel(r'time ($\Omega^{-1}$)')
# plt.ylabel(r'$\sigma_z$')
# plt.title(
#     '\n'.join(
#         (
#             'rap demo',
#             r'$\Delta=%d \Omega$, $\Delta \omega_{RAP}=%d \Omega$' % (
#                 delta, dwo
#             )
#         )
#     )
# )
# plt.show()

deltao = 4
omegao = 1
Cmin = 4
Cmax = 8
Tmin = Cmin * 2 * np.pi
Tmax = Cmax * 2 * np.pi
M = 1000
domegao = 1

deltas = np.linspace(0,deltao,20)
fractions = []
for delta in deltas:
    print(domegao,delta)
    fraction = 0
    for _ in range(M):
        fraction += get_energy_imp_rap(
            1 / np.sqrt(
                delta**2 + domegao**2 + omegao**2
            ) / 10,
            np.random.uniform(Tmin,Tmax),
            omegao,
            delta,
            domegao
        ) / M
    fractions.append(fraction)
plt.plot(deltas,fractions)
plt.xlabel(r'$\Delta (\Omega)$')
plt.ylabel('excitation fraction')
plt.title(
    '\n'.join(
        (
            'excitation versus doppler detuning - rap excitation',
            r'$\Delta \omega_{RAP}=%d \Omega$, $T = 2 \pi \times 6 \Omega^{-1}$' % (domegao)
        )
    )
)
plt.show()
