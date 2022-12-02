import beckhttpserver as bhs
import lidmotor
import rotaryencoder

class LidApp(bhs.BeckApp):
    def __init__(
        self,
        lidmotor_handle: lidmotor.LidMotor,
        rotary_encoder_handle,
        phi_o
    ):        
        self.lmh = lidmotor_handle
        self.reh = rotary_encoder_handle
        self.lp = lidmotor.LidPositioner(self.lmh,phi_o)
        self.backlash = self.lp.get_backlash()
        self.backlash_buffer = 0.50
        self.backlashing = False
        self.backlashing_phis = []   

    @bhs.command('get-encoder')
    def get_encoder(self):
        return rotaryencoder.get_position(self.reh)

    @bhs.command('calibrate-lid')
    def calibrate_lid(self,phi_o):
        self.lp.calibrate_angle(phi_o)

    @bhs.command('set-lid')
    def set_lid(self,phi):           
        if self.backlashing:
            raise bhs.BeckError('set lid command forbidden during backlash correction!')        
        if self._get_moving():
            raise bhs.BeckError('set lid command forbidden while lid is moving!') 
        phio = self.lp.get_angle()
        dphi = phi - phio
        if dphi < 0:            
            print('negative move requested, backlash compensating...')       
            self.backlashing = True
            self.backlashing_phis = [
                phio-self.backlash,
                phi-self.backlash*(1+self.backlash_buffer),
                phi-self.backlash*self.backlash_buffer,
                phi
            ]            
            phi = self.backlashing_phis.pop(0)
        self.lp.set_angle(phi,wait=False)

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
                if self.backlashing_phis:
                    phi = self.backlashing_phis.pop(0)
                    self.lp.set_angle(phi,wait=False)                    
                else:
                    self.backlashing = False