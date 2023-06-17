import time

pointer_len = 5
array = [0] * pointer_len
for i in range(pointer_len):
    array[i] = i
    print(i)
pointer = 0
while True:
    time.sleep(1)
    pointer = (pointer + 1) % pointer_len
    print(array[pointer])

