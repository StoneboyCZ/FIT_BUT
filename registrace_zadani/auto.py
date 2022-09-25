'''
    AUTOR: Petr Veigend (iveigend@fit.vut.cz)
    VERZE: 1.5
    
    Tento skript pouziva REST API IS VUT pro:
    a] ziskani CSV se seznamem rozvhovych jednotek zadaneho typu pro zadany predmet (v souboru s nazvem {idpredmetu}-{casvygenerovani}.csv), ktery je vytvoren v adresari programu
    b] automaticke prevedeni studentu zapsanych do vyucovani do zadani vytvorenych pomoci CSV z bodu a]

    Prace se skriptem:
    1] vyucujici vygeneruje CSV se seznamem zadani, ktere odpovidaji rozvrhu 
       Pokud nejsou nastaveni vyucujici, skript pouzije osobni cislo uzivatele. Tj. je doporuceno pred pouzitim nastavit vyucujici !!! 
    2] vyucujici importuje CSV do predem vytvoreneho hodnoceni v ramci predmetu (modul Vypisovani zadani)
    3] vyucujici provede automatickou registraci studentu na zadani podle registraci vyucivani (parametr --reg). Opetovne spusteni skriptu provede aktualizaci. 
    POZOR: pokud student jiz ziskal v ramci zadani hodnoceni, neni odlhaseni ze zadani podporovano a je nutne ho prihlasit/odhlasit rucne

    CHANGELOG
    - upraveno pro pouziti v ramci noveho repozitare
    - upravena logika pro prohazovani studentu mezi zadanimi (zmeny se nove provadi najednou, nikoli po zadanich - predejde se tim problemum s kapacitou)
'''

import os
import sys

# https://towardsdatascience.com/understanding-python-imports-init-py-and-pythonpath-once-and-for-all-4c5249ab6355
PROJECT_ROOT = os.path.abspath(os.path.join(
                  os.path.dirname(__file__), 
                  os.pardir)
)
sys.path.append(PROJECT_ROOT)

import requests
import argparse
from datetime import datetime
import utils

######## SETTINGS: nastavte pred pouzitim skriptu ############
DEBUG = False # False - pracuje s ostrou databazi, True - pracuje s testovaci databazi (testovaci Apollo)
VUTID = 110633 # osobni cislo - integer
COURSE_ID = 230979 # id predmetu, se kterym budete pracovat - integer
SCHEDULE_UNIT_TYPE = 'Laboratorní cvičení' # typ rozvhove jednotky, pro kterou chcete generovat seznam zadani (seznam rozvrhovych jednotek) - viz https://www.vut.cz/teacher2/cs/predmet-rozvrh-editace? --> Seznam rozvrhových jednotek, nastavte podle potreby
ACTIVITY_ID = 113165 # ID hodnoceni, ve kterem budete chtit zadani vytvorit (zobrazte si spravny sloupec ve strukture hodnoceni https://www.vut.cz/teacher2/cs/predmet-struktura-hodnoceni)

## dalsi parametry pro zadani - pred vygenerovanim CSV je nutne nastavit
TEXT = "Hodnocení laboratoří IEL" # povinna polozka 
TEXT_EN = "Points from IEL laboratories" # popis zadani anglicky 
LITERATURE = "" # literatura
URL = "" # odkaz na dalsi informace
QUESTIONS = 6 # pocet otazek (pokud se bude zadani skladat z vice casti - vice cviceni.. zadejte)
LANG = 'cs' # moznosti cs a en; urcuje, jestli bude generovaný název termínu česky nebo anglicky
###############################################################

DAYS = {
    1:'Pondělí',
    2:'Úterý',
    3:'Středa',
    4:'Čtvrtek',
    5:'Pátek'
}

DAYS_EN = {
    1:'Monday',
    2:'Tuesday',
    3:'Wednesday',
    4:'Thursday',
    5:'Friday'
}


def getCourseSchedule(s, courseID, unitType):
    """Gets a schedule for a course specified by its ID.

    Args:
        s (_type_): initialized session
        courseID (_type_): course ID

    Returns:
        _type_: schedule of the specified course
    """
    if DEBUG:
        url = f'https://api.vut.cz:1443/api/fit/aktualni_predmet/{courseID}/vyucovani/v3?lang=cs'
    else:    
        url = f'https://api.vut.cz/api/fit/aktualni_predmet/{courseID}/vyucovani/v3?lang=cs'
    
    data = s.get(url).json()['data']['vyucovani']

    out = []
    for unit in data:
        if unit['v_trj_popis'] == unitType and unit['v_povolit_registraci'] == 1: # filter only the selected schedule units
            out.append(unit)
    return out
    

def getSupervisorID(s, scheduleID, VUTid):
    """Gets the ID of a teacher set as a supervisor for a schedule unit.

    Args:
        s (_type_): initialized session
        scheduleID (_type_): ID of the schedule unit
        VUTid (_type_): BUT ID used as a fallback

    Returns:
        _type_: ID for the first teacher set for the schedule unit.
    """
    if DEBUG:
        url = f'https://api.vut.cz:1443/api/fit/vyucovani/{scheduleID}/vyucujici/v3'
    else:    
        url = f'https://api.vut.cz/api/fit/vyucovani/{scheduleID}/vyucujici/v3'
    
    r = s.get(url).json()['data']

    if not r: # no supervisor, use BUT ID of the user
        return VUTid
    else: # supervisor
        vyucovani = r['vyucovani'][0]
        vyucujici = vyucovani['vyucujici'][0]['osoba_id']
        return vyucujici

def getRooms(s, scheduleID):
    """Returns the string containing the names of all rooms associated with the schedule unit.

    Args:
        s (_type_): initialized session
        scheduleID (_type_): ID of the schedule unit

    Returns:
        _type_: string containing names of all rooms associated with the schedule unit
    """
    if DEBUG:
        url = f'https://api.vut.cz:1443/api/fit/vyucovani/{scheduleID}/mistnosti/v3'
    else:    
        url = f'https://api.vut.cz/api/fit/vyucovani/{scheduleID}/mistnosti/v3'    
        
    r = s.get(url).json()['data']['vyucovani'][0]['mistnosti']

    out = ''
    for i,room in enumerate(r):
        out+=f"{room['mistnost_label']}"
        if i < len(r)-1:
            out+= ','
    return out

def getAssigments(s, courseID, activityID):
    """Returns the created assigments (zadani) for the specified activity

    Args:
        s (_type_): initialized session
        courseID (_type_): course ID
        activityID (_type_): activity ID

    Returns:
        _type_: A dictionary containing the information about all assigments created for the activity. 
    """
    if DEBUG:
        url = f'https://api.vut.cz:1443/api/fit/aktualni_predmet/{courseID}/zadani/v3'
    else:    
        url = f'https://api.vut.cz/api/fit/aktualni_predmet/{courseID}/zadani/v3'        
    
    r = s.get(url).json()['data']

    if not r: # no activities
        return []
    else:
        out = []
        zkousky = r['predmety'][0]['aktualni_predmety'][0]['zkousky']
        for z in zkousky:
            if z['zkouska_projekt_id'] == activityID:
                for a in z['zadani']:
                    e = {}
                    e['id'] = a['zadani_id']
                    e['nazev'] = a['zadani_nazev']
                    e['vedouci'] = a['vedouci_id'] 
                    out.append(e)
                break
        return out


def parseScheduleData(unit, VUTid, lang):
    """Function parses the schedule unit data.

    Args:
        unit (_type_): schedule unit data
        VUTid (_type_): BUT ID, used as a fallback in one of the functions

    Returns:
        _type_: Parsed schedule unit data.
    """
    e = {}
    e['vyucovani_id'] = unit['v_vyucovani_id']
    e['max_pocet_resitelu'] = unit['v_max_pocet_studentu']
    
    # get the supervisor id
    e['vedouci_id'] = getSupervisorID(s,e['vyucovani_id'], VUTid)
    e['mistnost'] = getRooms(s, e['vyucovani_id'])

    bloky = unit['bloky']
    for b in bloky:
        e['den'] = DAYS[b['vb_den_id']]
        e['den_en'] = DAYS_EN[b['vb_den_id']]
        cas = b['vb_cas_od'].split('T')[1]
        e['cas_od'] = f"{cas.split(':')[0]}:{cas.split(':')[1]}"

        for d in b['dny']:
            if d['vbd_zruseno'] == 0:
                datum = d['vbd_datum'].split('T')[0]
                e['datum_od'] = f"{datum.split('-')[2]}.{datum.split('-')[1]}.{datum.split('-')[0]}"
                e['datum_od_en'] = f"{datum.split('-')[0]}-{datum.split('-')[1]}.{datum.split('-')[2]}"
                break # because we just need to find the first one, that is not cancelled
    
    
    if lang == 'cs':
        e['nazev'] = f"{e['den']} {e['cas_od']} v {e['mistnost']} od {e['datum_od']}" # Pondělí 12:00 v N105 od 19.09.2022
    else:
        e['nazev'] = f"{e['den_en']} {e['cas_od']} in {e['mistnost']} from {e['datum_od']}" # Monday 12:00 in N105 from 2022-09-19
    return e


def generateCSV(s, courseID, scheduleType, VUTid, params):
    """Function generates CSV.

    Args:
        s (_type_): initialized session
        courseID (_type_): course ID
        scheduleType (_type_): type of the schedule unit that we are working with
        VUTid (_type_): BUT ID (fallback in one of the functions)
        params (_type_): additional parameters
    """
    r = getCourseSchedule(s, courseID,scheduleType)  
    data = []
    for unit in r:
        e = parseScheduleData(unit,VUTid,params['jazyk']) # parse the schedule data
        e.update(params) # static parameters
        data.append(e) 

    # generate the csv (out.csv)
    now = datetime.now()
    current_time = now.strftime("%H%M%S")
    fn = f'{courseID}-{current_time}.csv'
    with open (fn, 'w', encoding='utf-8') as f:
        f.write('nazev,nazev_en,text,text_en,literatura,url,pocet_otazek,vedouci_id,max_pocet_resitelu\n')
        for d in data:
            f.write(f"\"{d['nazev']}\",,{d['text']},{d['text_en']},{d['literatura']},{d['url']},{d['pocet_otazek']},{d['vedouci_id']},{d['max_pocet_resitelu']}\n")


def getStudentsForSchedule(s, courseID, scheduleID):
    """Function returns the IDs of students that are registered to the specified schedule unit.

    Args:
        s (_type_): initialized session
        courseID (_type_): ID of the course
        scheduleID (_type_): ID of the schedule unit

    Returns:
        _type_: _description_
    """
    if DEBUG:
        url = f'https://api.vut.cz:1443/api/fit/aktualni_predmet/{courseID}/vyucovani/{scheduleID}/studenti/v3'
    else:    
        url = f'https://api.vut.cz/api/fit/aktualni_predmet/{courseID}/vyucovani/{scheduleID}/studenti/v3'        
    
    studenti = s.get(url).json()['data']['predmety'][0]['aktualni_predmety'][0]['vyucovani'][0]['studenti']
    out = []
    
    for s in studenti:
        student = {}
        student['id'] = s['per_id']
        student['el_index_id'] = s['el_index_id']
        out.append(student)
    '''  
    for s in studenti:
        out.append(s['el_index_id'])
    '''
    return out

def getStudentsForAssigment(s, courseID, assigmentID):
    """Function returns the list of student IDs that are currently registered in the assigment.

    Args:
        s (_type_): initialized session
        courseID (_type_): ID of the course
        assigmentID (_type_): ID of the assigment

    Returns:
        _type_: _description_
    """
    if DEBUG:
        url = f'https://api.vut.cz:1443/api/fit/aktualni_predmet/{courseID}/zadani/{assigmentID}/studenti/v3'
    else:    
        url = f'https://api.vut.cz/api/fit/aktualni_predmet/{courseID}/zadani/{assigmentID}/studenti/v3' 

    data = s.get(url).json()['data']

    if not data:
        return []
    else:
        studenti = data['studenti']
        students = []
        for s in studenti:
            student = {}
            student['id'] = s['per_id']
            student['el_index_id'] = s['el_index_id']
            student['pocet_bodu'] = s['pocet_bodu']
            students.append(student)
        return students
        

def matchAssigmentToSchedule(s, courseID, scheduleType, assigment,lang):
    """Function matches the assigment to the the schedule window/

    Args:
        s (_type_): initialized session
        courseID (_type_): course ID
        scheduleType (_type_): type of the schedule window
        assigment (_type_): the information about the assigment

    Returns:
        _type_: id of the schedule window or None
    """
    schedule = getCourseSchedule(s, courseID,scheduleType)
    # find the window matching the assigment
    out = None
    for unit in schedule:
        e = parseScheduleData(unit, 0,lang)
        #if e['nazev'] == assigment['nazev']: # match the entire name of the assigment
        if e['nazev'] in assigment['nazev']: # match just a part of the name, more flexible
            return e['vyucovani_id']
    return out    


def updateStudentAssigment(s,operation,courseID, assigmentID,student):
    if DEBUG:
        url = f'https://api.vut.cz:1443/api/fit/aktualni_predmet/{courseID}/zadani/{assigmentID}/el_index/{student}/v4'
    else:    
        url = f'https://api.vut.cz/api/fit/aktualni_predmet/{courseID}/zadani/{assigmentID}/el_index/{student}/v4'    

    print(url)

    if operation == 'REMOVE':
        r = s.delete(url)

    if operation == 'ADD':
        payload = {
            'POTVRZENI_REGISTRACE':1,
            'ZVYSIT_KAPACITU':0    
        }
        header = {"Content-Type": "application/json"}
        r = s.post(url, json=payload, headers=header)
    
    return r.status_code
        
def updateAssigment(s, courseID, assigment, studentsAssigment, studentsScheduleUnit):
    updates = []
    studentsScheduleIDs = [d['el_index_id'] for d in studentsScheduleUnit]
    
    # if there are no students on the assigment, just add all students from the schedule unit
    if len(studentsAssigment) == 0: # new students
        print('Zadani je prazdne, prihlasuji postupne vsechny studenty z rozvrhove jednotky.')
        for student in studentsScheduleUnit:
            status = updateStudentAssigment(s,'ADD',courseID,assigment['id'],student['el_index_id'])    
            if status == requests.codes.bad:
                print(f"ERR: Chyba pri vkladani studenta {student['id']} do zadani.")
            else:
                print(f"OK: Student {student['id']} vlozen do zadani.")
    else: # students already on assigment
        # iterate over all students in the assigment
        for student in studentsAssigment:     
            
            if student['el_index_id'] not in studentsScheduleIDs: # if a student cancelled the schedule registration, we can remove him from the assigment
                if student['pocet_bodu'] is None: # is allowed only if there is no grade
                    #updateStudentAssigment(s,'REMOVE',courseID,assigment['id'],student['el_index_id'])
                    updates.append({
                        'student_id':student['id'],
                        'el_index_id':student['el_index_id'],
                        'assigment':assigment['id'],
                        'operation':'REMOVE'
                    })

                    print(f"OK: Student {student['id']} bude odstranen ze zadani - zmena rozvrhove jednotky.")
                else:
                    print(f"ERR: Studenta {student['id']} nelze ze zadani odstranit - ma zadano hodnoceni. Je treba ho odstranit rucne.")
            
        # are there any students that are registered in the schedule unit and not registered in the assigment?
        studentsAssigmentIDs = [d['el_index_id'] for d in studentsAssigment]
        newStudentsIDs = [item for item in studentsScheduleIDs if item not in studentsAssigmentIDs]
        
        for st in studentsScheduleUnit:
            if st['el_index_id'] in newStudentsIDs:
                updates.append({
                    'student_id':st['id'],
                    'el_index_id':st['el_index_id'],
                    'assigment':assigment['id'],
                    'operation':'ADD'
                })
                print(f"OK: Student {st['id']} se prihlasil nove, bude provedena registrace do zadani.")

        return updates
def handleAssigment(s, assigment, courseID):
    print(f'Zadani: {assigment}')

    # get students that are currently registrered on the assigment
    studentsAssigment = getStudentsForAssigment(s,courseID,assigment['id'])
    # get students from the window
    studentsScheduleUnit = getStudentsForSchedule(s,courseID,assigment['vyucovani_id'])

    # update the students on the assigment (register them to the empty assigment or fetch changes)
    return updateAssigment(s, courseID, assigment, studentsAssigment, studentsScheduleUnit)

def performUpdates(s,courseID, updates):
    print('Provadim zmeny')
    for u in updates:
        print(f"OK: Student {u['student_id']}, zadani {u['assigment']}, operace {u['operation']}")
        updateStudentAssigment(s,u['operation'],courseID,u['assigment'],u['el_index_id'])

##############################################################################################

# process the cmd arguments
parser = argparse.ArgumentParser(description='Zpracovani registraci studentu na zadani.')
parser.add_argument(
    '--csv', 
    action='store_true',
    help='vygeneruje csv'
    )
parser.add_argument(
    '--reg', 
    action='store_true',
    help='provede registraci na vyucovani'
    )

args = parser.parse_args()
s = utils.createSession(VUTID)
if args.csv:
    params = {}
    params['text'] = TEXT
    params['text_en'] = TEXT_EN
    params['literatura'] = LITERATURE
    params['url'] = URL
    params['pocet_otazek'] = QUESTIONS
    params['jazyk'] = LANG

    csv = generateCSV(s, COURSE_ID, SCHEDULE_UNIT_TYPE, VUTID, params)

elif args.reg:
    # ziskat seznam zadani pro hodnoceni
    assigments = getAssigments(s, COURSE_ID, ACTIVITY_ID)

    updates = []

    for a in assigments:
        # match the created assigment to the schedule window
        a['vyucovani_id'] = matchAssigmentToSchedule(s,COURSE_ID,SCHEDULE_UNIT_TYPE,a,LANG)
        if a['vyucovani_id'] == None:
            print('ERR: Nepodarilo se namapovat zadani a rozvrhovou jednotku. Pravdepodobne je zadan spatny typ rozvrhove jednotky v konstante SCHEDULE_UNIT_TYPE.')
        else:
            # handle students on the assigment
            update = handleAssigment(s,a, COURSE_ID)
            if update:
                for u in update:
                    updates.append(u)       

    # were there any updates that have to be performed?
    if len(updates) > 0:
        sortedUpdates = sorted(updates, key=lambda d: d['operation'],reverse=True)
        performUpdates(s,COURSE_ID,sortedUpdates)
