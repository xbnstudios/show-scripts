from datetime import datetime
import sys

STF = "%Y-%m-%d-%H:%M:%S"

res = int((datetime.strptime(sys.argv[2], STF) - datetime.strptime(sys.argv[1], STF)).total_seconds())

print(res)