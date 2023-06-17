import hashlib


hash1 = hashlib.sha256()
hash1.update('peter3 istsdfsdfsfsf ein 5kleines fujusdfsfgsdfsdf')
hash1wert = hash1.digest()

hash2 = hashlib.sha256()
hash2.update('peter3 istsdfsdfsfsf ein 5kleines fujusdfsfgsdfsdf')
hash2wert =hash2.digest()
print(hash1wert == hash2wert)