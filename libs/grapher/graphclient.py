import beckhttpclient as bhc
import numpy as np

HOST = bhc.get_host()
PORT = 8000

def send_command(command,parameters):
    return bhc.send_command(HOST,PORT,command,parameters)

def add_folder(folder):
    return send_command('add-folder',{'folder':folder})

def add_dataset(folder,name,fields,metadata=None):
    return send_command('add-dataset',{'folder':folder,'name':name,'fields':fields,'metadata':metadata})

def add_data(path,data):
    return send_command('add-data',{'path':path,'data':data})

def add_data_multiline(path,data):
    return send_command('add-data-multiline',{'path':path,'data':data})

def get_data(path):
    return send_command('get-data',{'path':path})        

def get_data_np(path):
    return list(map(np.array,get_data(path)))

def get_metadata(path):
    return send_command('get-metadata',{'path':path})

def get_created(path):
    return send_command('get-created',{'path':path})

def get_fields(path):
    return send_command('get-fields',{'path':path})

def get_dir(folder):
    return send_command('get-dir',{'folder':folder})

def get_day_folder():
    return send_command('get-day-folder',{})

if __name__ == '__main__':
    from time import sleep
    import math
    import numpy as np
    np.random.seed()
    folder = get_day_folder()
    path = add_dataset(
        folder,
        'apples',
        ['oranges (pieces)','bananas (bunches)','pecans (bushels)']
    )
    for i in range(2000):
        print(i)
        add_data(
            path,
            [
                i,
                i**2 * (1 + np.random.random()/10),
                math.sin(2*3.14159*i/100) + np.random.random()/10
            ]
        )
        sleep(.05)
    
