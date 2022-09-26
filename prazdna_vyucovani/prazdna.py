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

def getSchedule(s, room):
    url = f"https://api.vut.cz/api/fit/mistnost/{room}/vyucovani/v3?lang=cs&rok=2022&typ_semestru_id=2"
    print(url)
    data = s.get(url).json()['data']
   
    out = []
    if data:
        vyucovani = data['vyucovani']
        for v in vyucovani:
            tmp = {}

            tmp['predmet'] = v['v_p_zkratka']
            tmp['predmet_id'] = v['v_aktualni_predmet_id']
            tmp['typ'] = v['v_trj_popis']
            tmp['id'] = v['v_vyucovani_id']
            
            if v['v_povolit_registraci'] == 0 or v['v_pocet_studentu'] == 0:
                tmp['pocet_studentu'] = v['v_pocet_studentu']
                tmp['povolit_registraci'] = v['v_povolit_registraci'] 
                for b in v['bloky']:
                    tmp['od'] = b['vb_cas_od'].split('T')[1]
                    tmp['do'] = b['vb_cas_do'].split('T')[1]
                    tmp['den'] = utils.DAYS[b['vb_den_id']]    
                out.append(tmp)
    
    return out
    

ID = 110633
s = utils.createSession(ID)
rooms = utils.getRooms(s)
with open('out.txt', 'w', encoding='utf-8') as f:
    for r in rooms:
        print(r)
        schedule = getSchedule(s,r['id'])
        if len(schedule) > 0: 
            f.write(f"== {r['name']} == \n")
            for sch in schedule:
                print(sch)
                url = f"https://www.vut.cz/teacher2/cs/predmet-rozvrh-editace/detail/id/{sch['id']}"
                f.write(f"{sch['predmet']}, {sch['typ']}, {sch['den']} {sch['od']} -- {sch['do']}, reg {sch['povolit_registraci']}, stud {sch['pocet_studentu']} {url}\n")
                
