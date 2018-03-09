import glob
import os

for file in glob.glob("*.lrc"):
    filename = file[0:7]

    lrc_file = open(file)
    lrc_lines = lrc_file.readlines()
    lrc_file.close()

    label = open(filename + '.txt','w')

    print(filename)

    for line in lrc_lines[3:]:
        time = line[line.find("[")+1:line.find("]")].replace('.', ':').split(':')
        labeltime = str(int(time[0]) * 60 + int(time[1])) + '.' + time[2] + '0000'
        title = line.split(']',1)[1].rstrip('\n')
        label.write(labeltime + '	' + labeltime + '	' + title + '\n')
    label.close()
