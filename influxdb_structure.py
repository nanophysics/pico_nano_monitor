# https://docs.influxdata.com/influxdb/cloud/reference/key-concepts/data-elements/

influxFieldKeyDict = {  # Zahlenwerte
    "temperature_C": None,
    "temperature_K": None,
    "pressure_Pa_rel": None,
    "pressure_Pa_abs": None,
    "resistance_Ohm": None,
    "voltage_V": None,
    "current_A": None,
    "flow_m3_per_s": None,
    "flow_mol_per_s": None,
    "powerOutage_s": None,
    "outage_trace_V": None,
    "power_W": None,
    "uptime_s": None,
    "number_i": None,
    "binary_state": None,  # True False
    "vibration_peak_AU": None,  # Integer
    "vibration_average_AU": None,  # Integer
    "humidity_pRH": None,
    "flow_ln_per_min": None, # only for He flow sensor
    "total_ln": None, # only for He flow sensor
    "anforderung": None,  # True False, temporaer, loeschen 2025
    "zwangsladung": None,  # True False, temporaer, loeschen 2025
}

influxTagKeyDict = {
    "room": ["A", "C15", "C17", "C18", "B15", "B16", "B17", "D24", "E9"],
    "setup": [
        "bigmom",
        "zeus",
        "titan",
        "tarzan",
        "emma",
        "bertram",
        "nele",
        "dobby",
        "bud",
        "charly",
        "anna",
        "werner",
        "sofia",
        "tabea",
        "fritz",
        "charlie",
        "broker",
        "HPT_nitrogen_tank",
    ],
    "position": None,  # z.B. "N2 exhaust tube"
    "user": ["pmaerki", "benekrat", "baehler", "lostertag", "hannav"],
    "quality": ["testDeleteLater", "use"],
}

measurementExample = [
    {
        "measurement": "pico_emil",  # a measurement has one 'measurement'. It is the name of the pcb.
        "fields": {
            "temperature_C": "23.5",
            "humidity_pRH": "88.2",
        },
        "tags": {
            "setup": "zeus",
            "room": "B15",
            "position": "hintenLinks",
            "user": "pmaerki",
        },
    },
]


def assert_valid(measurements):
    for measurement in measurements:
        for field_name in measurement["fields"]:
            assert (
                field_name in influxFieldKeyDict
            ), f"field '{field_name}' is not in {influxFieldKeyDict}"
        for tag_name, tag_value in measurement["tags"].items():
            valid_values = influxTagKeyDict[tag_name]
            if valid_values is None:
                continue
            assert (
                tag_value in valid_values
            ), f"{tag_name}={tag_value} is not in {valid_values}"


assert_valid(measurementExample)


if __name__ == "__main__":
    print(measurementExample)
