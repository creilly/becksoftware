import pyvisa

pmid = 'powermeter'

def open_pm(pmid=pmid):
    return pyvisa.ResourceManager().open_resource(pmid)

def get_power(pm):
    return float(pm.query('READ?'))

def get_idn(pm):
    return pm.query('*IDN?')

def close_pm(pm):
    pm.close()

class PMHandler:
    def __init__(self,pmid=pmid):
        self.pm = open_pm(pmid)

    def __enter__(self):
        return self.pm

    def __exit__(self,*args):
        close_pm(self.pm)

if __name__ == '__main__':
    with PMHandler() as pm:
        while True:
            print('{:.3f}'.format(get_power(pm)))

