import lid
from lid import lidserver
import lidmotor
import beckhttpserver as bhs
import os

while True:        
    try:
        phi_o = float(input('enter current angle, engaged in FORWARDS direction: '))
        break
    except ValueError:
        print('invalid input.')
        continue
with lidmotor.LidMotorHandler() as lmh:    
    bhs.run_beck_server(lid.PORT,os.path.dirname(__file__),lidserver.LidApp,lmh,phi_o,_debug=True)