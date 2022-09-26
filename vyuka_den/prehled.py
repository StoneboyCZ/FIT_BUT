from datetime import datetime
import os
import sys

# https://towardsdatascience.com/understanding-python-imports-init-py-and-pythonpath-once-and-for-all-4c5249ab6355
PROJECT_ROOT = os.path.abspath(os.path.join(
                  os.path.dirname(__file__), 
                  os.pardir)
)
sys.path.append(PROJECT_ROOT)

import utils

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
s = utils.createSession(ID)
rooms = utils.getRooms(s)

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
