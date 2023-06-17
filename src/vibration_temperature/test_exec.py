
def read_config(board_name = ''):
    local_ns = {}
    execfile('config.py', local_ns)
    return local_ns.get('pico_tags').get(board_name)

pico_tags = read_config(board_name = 'pico_rahel')
print(pico_tags)
