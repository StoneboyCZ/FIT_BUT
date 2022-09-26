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