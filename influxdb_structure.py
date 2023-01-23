#https://docs.influxdata.com/influxdb/cloud/reference/key-concepts/data-elements/

influxFieldKeyDict= { # Zahlenwerte
    "temperature_C": None,
    "temperature_K": None,
    "pressure_Pa_rel": None,
    "pressure_Pa_abs": None,
    "resistance_Ohm": None,
    "flow_m3_per_s": None,
    "flow_mol_per_s": None,
    "powerOutage_s": None,
    "uptime_s": None,
    "binary_state": None, # True False
    "humidity_pRH": None,}

influxTagKeyDict= {
    "room": ["B15","B16","B17", "C17"],
    "setup": ['sofia', 'tabea', 'fritz', 'charlie', 'broker'],
    "position": None, # z.B. "N2 exhaust tube" 
    "user": ["pmaerki", "benekrat", "baehler", "lostertag"],
    "quality": ["testDeleteLater", "use"],}

measurementExample = [{
    'measurement': 'pico_emil', # a measurement has one 'measurement'. It is the name of the pcb.
    'fields': {
        'temperature_C': '23.5',
        'humidity_pRH': '88.2',},
    'tags': {
        'room': 'B15',
        "position": "hintenLinks",
        'user': 'pmaerki',},
    },]
        
def assert_valid(measurements):
    for measurement in measurements:
        for field_name in measurement['fields']:
            assert field_name in influxFieldKeyDict, f"field '{field_name}' is not in {influxFieldKeyDict}"
        for tag_name, tag_value in measurement['tags'].items():
            valid_values = influxTagKeyDict[tag_name]
            if valid_values is None:
                continue
            assert tag_value in valid_values, f"{tag_name}={tag_value} is not in {valid_values}"


assert_valid(measurementExample)