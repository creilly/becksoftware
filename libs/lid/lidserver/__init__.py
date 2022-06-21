import beckhttpserver as bhs
import lidmotor

class LidApp(bhs.BeckApp):
    def __init__(self,lidmotor_handle: lidmotor.LidMotor,phi_o):        
        self.lmh = lidmotor_handle
        self.lp = lidmotor.LidPositioner(self.lmh,phi_o)        
        self.backlashing = False
        self.phi_p = None

    @bhs.command('calibrate-lid')
    def calibrate_lid(self,phi_o):
        self.lp.calibrate_angle(phi_o)

    @bhs.command('set-lid')
    def set_lid(self,phi):                
        if self.backlashing:
            raise bhs.BeckError('set lid command forbidden during backlash correction!')
        if self._get_moving():
            raise bhs.BeckError('set lid command forbidden while lid is moving!')        
        dphi = phi - self.lp.get_angle()        
        if dphi < 0:
            print('negative move requested, backlash compensating...')       
            phi_next = phi                 
            phi = phi-self.lp.get_backlash()
        self.lp.set_angle(phi,wait=False)
        if dphi < 0:
            self.backlashing = True
            self.phi_p = phi_next            

    @bhs.command('get-lid')
    def get_lid(self):        
        return self.lp.get_angle()

    def _get_moving(self):
        return not self.lmh.position_reached()

    @bhs.command('get-moving')
    def get_moving(self):
        return self.backlashing or self._get_moving()

    @bhs.command('stop-lid')
    def stop_lid(self):
        return self.lmh.stop_motor()

    @bhs.command('get-phi-min')
    def get_phi_min(self):        
        return self.lp.get_phi_min()

    @bhs.command('get-phi-max')
    def get_phi_max(self):
        return self.lp.get_phi_max()

    @bhs.command('set-phi-min')
    def set_phi_min(self,phi_min):
        return self.lp.set_phi_min(phi_min)

    @bhs.command('set-phi-max')
    def set_phi_max(self,phi_max):
        return self.lp.set_phi_max(phi_max)

    def loop(self):        
        if self.backlashing:
            if self.lmh.position_reached():                
                self.backlashing = False
                self.set_lid(self.phi_p)
                self.phi_p = None