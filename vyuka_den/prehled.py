import requests
from requests.auth import HTTPBasicAuth
import getpass
from datetime import datetime

def createSession(id):
    """Function creates a session for communication with IS VUT

    Args:
        id (_type_): BUT personal ID

    Returns:
        _type_: session 
    """
    s = requests.Session()
    password=getpass.getpass(prompt="Password: ", stream=None)
    s.auth = HTTPBasicAuth(id, password)
    
    return s 

def getRooms(s):
    url = 'https://api.vut.cz/api/fit/mistnosti/v4?lang=cs&rozvrhovane=1&aktualni=1'
    data = s.get(url).json()['data']['lokality']
    
    rooms = []
    for l in data:
        if l['lokalita_id'] == 3:
            for a in l['arealy']:
                if a['areal_id'] == 17:
                    for b in a['budovy']:
                        for p in b['podlazi']:
                            for m in p['mistnosti']:
                                room = {
                                    'id':m['mistnost_id'],
                                    'name':m['label']
                                }
                                rooms.append(room)

    return rooms

def getSchedule(s, room, date):
    date_is = f"{date.split('.')[2]}-{date.split('.')[1]}-{date.split('.')[0]}T00:00:00"
    url = f"https://api.vut.cz/api/fit/mistnost/{room}/vyucovani/v3?lang=cs&rok=2022&datum_od={date}&datum_do={date}"
    print(url)
    data = s.get(url).json()['data']
   
    out = []
    if data:
        vyucovani = data['vyucovani']
        for v in vyucovani:
            add = False
            tmp = {}

            tmp['predmet'] = v['v_p_zkratka']
            tmp['predmet_id'] = v['v_aktualni_predmet_id']
            tmp['typ'] = v['v_trj_popis']
            tmp['id'] = v['v_vyucovani_id']
            
            for b in v['bloky']:
                tmp['od'] = b['vb_cas_od'].split('T')[1]
                tmp['do'] = b['vb_cas_do'].split('T')[1]
                for d in b['dny']:
                    if d['vbd_datum'] == date_is and d['vbd_zruseno'] == 0:
                        add = True   

            if add:
                out.append(tmp)
    
    return out
        

ID = 110633
DATE = '17.11.2022' 
s = createSession(ID)
rooms = getRooms(s)

current_time = datetime.now().strftime("%m-%d-%Y_%H%M%S")
with open(f'{DATE}-{current_time}.txt', 'w', encoding='utf-8') as f:
    for r in rooms: 
        print(r)
        schedule = getSchedule(s,r['id'],DATE)
        if len(schedule) > 0: 
            f.write(f"== {r['name']} == \n")
        for sch in schedule:
            url = f"https://www.vut.cz/teacher2/cs/predmet-rozvrh-editace/detail/id/{sch['id']}"
            f.write(f"{sch['predmet']}, {sch['typ']}, {sch['od']} -- {sch['do']}: {url}\n")
