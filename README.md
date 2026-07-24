parameters taken:
ROOM.WALL.SHELF.BOOK.PAGE
room -> base-32 alphanumeric string (0-9a-v)
wall -> 1-4
shelf -> 1-5
book -> 1-32

page number is ignored at first,
a tuple of (ROOM, WALL, SHELF, BOOK) is converted into a global book index

book index to book contents:
uses huge number modular arith in b32 with constants from a file 'numbers'
N -> largest possible b32 with 1,312,000 digits (book length)
C -> random large num (coprime to N)
I -> multiplicative  inverse of C mod N

forward mapping:
bookContentValue = (bookIndex * C) % N

reverse mapping (idts i'll use this right now):
bookIndex = (bookContentValue * I ) % N

content gen:
bookContentValue will be a huge 1.3 mil-ish b-32 number ,
each digit maps to a 32-char alphabet.

then that is sliced into 410 pages and returned by PAGE param.