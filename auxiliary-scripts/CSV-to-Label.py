import glob
import os
import csv

for file in glob.glob("*-p.csv"):
    filename = file[0:7] # assume fnt-xxx.lrc file format

    csv_file = open(file, encoding="utf-8")
    reader = csv.reader(csv_file, delimiter ='~')


    label = open(filename + '.txt','w', encoding="utf-8")

    print(filename)

    for row in reader:
        label.write(row[0] + '.000000' + '	' + row[0] + '.000000' + '	' + row[1] + '\n')
    label.close()
    csv_file.close()
