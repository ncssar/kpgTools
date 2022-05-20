# kpgCheck - inspect and compare Kenwood exported htm file(s)

# when reading KPG-D1N html files, read data from the 'Channel Edit' tables, rather
#  than the larger Zone table, since some items appear in the Channel Edit tables
#  but not in the Zone tables, such as PTT ID

import sys
import csv
import time
import os
import logging

logging.basicConfig(
        level=logging.INFO,
        # format='%(asctime)s %(message)s',
        format='%(message)s',
        handlers=[
            logging.FileHandler('kpgCheck.log','w'),
            logging.StreamHandler()
        ]
)

class KWFile():
    def __init__(self,fileName=None,parent=None):
        self.extension=os.path.splitext(fileName)[1].lower()
        self.soup=None
        self.allChannelDicts=[] # list of dictionaries, one per html channel entry (preserve duplicates)
        if self.extension=='.htm':
            with open(fileName,'r') as html_doc:
                logging.info('Parsing '+fileName+'...')
                from bs4 import BeautifulSoup
                self.soup=BeautifulSoup(html_doc,'html.parser')
                logging.info('Parsing complete.')
                for i in [x for x in self.soup.body.children if x.name]:
                    # logging.info('i:'+str(i.name)+':'+str(i.string))
                    # the first channel of each zone will have two h1 Channel Edit lines
                    if i.name=='h1' and i.string=='Channel Edit' and i.find_next().name!='h1':
                        # logging.info('Channel Edit heading found')
                        # logging.info('  next:'+str(i.find_next().name))
                        # logging.info('  next element:'+str(i.next_element.name))
                        # logging.info('  next sibling:'+str(i.next_sibling.name))
                        channelDict={}
                        t1=i.find_next('table') # next table should be 'Channel Edit' table
                        t2=t1.find_next('table') # next table should be 'General' table
                        t3=t2.find_next('table') # next table should be 'Analog' table
                        for t in [t1,t2,t3]:
                            for tr in t.find_all('tr'):
                                tds=tr.find_all('td')
                                if len(tds)==2: # skip the first tr which only has th (heading) tags
                                    [keyTd,valTd]=tds
                                    key=keyTd.string
                                    val=valTd.string
                                    # logging.info('  '+key+' = '+val)
                                    channelDict[key]=val
                        self.allChannelDicts.append(channelDict)
                logging.info('Imported '+str(len(self.allChannelDicts))+' channel entries.')

    def getAllChannelDicts(self):
        return self.allChannelDicts

    
if __name__=="__main__":
    logging.info('kpgCheck.py - Kenwood data conversion, validation, and comparison tool')
    logging.info('  kpgCheck.py last modified: '+time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(os.path.getmtime(__file__))))
    logging.info('  Run time: '+time.strftime('%Y-%m-%d %H:%M:%S',time.localtime()))
    logging.info('  File 1: '+sys.argv[1])
    if len(sys.argv)==3:
        logging.info('  File 2: '+sys.argv[2])
    logging.info('-----------------------------------------')
    if len(sys.argv)<2 or os.path.splitext(sys.argv[1])[1].lower() not in ['.html','.htm']:
        print("ERROR: must specify input .htm or .html filename.")
        sys.exit(-1)
    srcFileName=sys.argv[1]
    [srcBaseName,srcExtension]=os.path.splitext(srcFileName)
    chanFileName=srcBaseName+".csv"
    kw=KWFile(srcFileName)
    kpg=kw.soup.body.h1.string
    if 'KPG-D1N' not in kpg:
        logging.error("ERROR: only KPG-D1N html files are currently supported")
        sys.exit(-1)
    colKey=[
            ['Zone Number','Zone#']
        ,['Zone Name','Zone Name']
        ,['Channel Number','Chan#']
        ,['Channel Name','Channel Name']
        ,['Transmit Frequency [MHz]','TX']
        ,['Receive Frequency [MHz]','RX']
        ,['QT/DQT Encode','Enc']
        ,['QT/DQT Decode','Dec']
        ,['Channel Spacing (Analog) [kHz]','Spacing']
        ,['PTT ID (Analog)','PTT ID']
        ,['Scan Add','Scan Add']
    ]
    logging.info('Generating '+chanFileName+'...')
    with open(chanFileName,'w',newline='') as csvFile:
        csvWriter=csv.writer(csvFile)
        csvWriter.writerow([h[1] for h in colKey]) # header row
        for d in kw.getAllChannelDicts():
            # sort by a list of keys: https://stackoverflow.com/a/21773891
            # row=sorted(d.items(),key=lambda pair: [h[0] for h in colKey].index(pair[0]))
            row=[]
            for h in colKey:
                row.append(d[h[0]])
            csvWriter.writerow(row)
        csvWriter.writerow(["## end"])
    logging.info('Done.')
    logging.info('=========================================')
    logging.info(' Summary of discrepancies:')
    logging.info('=========================================')
    totalLogLines=[]
    totalLogLines.append('-----------------------------------------')
    totalLogLines.append('INTERNAL CONSISTENCY CHECK')
    totalLogLines.append('  Part 1: Report all channel names that appear more than once in the html file, and show any discrepancies:')
    totalLogLines.append('   - channels with the same name should have identical TX/RX/Enc/Dec/Spacing/PTT ID')
    totalLogLines.append('-----------------------------------------')
    channelNameDict={} # dict of lists of dicts
    keysToCompare=[
            'Transmit Frequency [MHz]'
        ,'Receive Frequency [MHz]'
        ,'QT/DQT Encode'
        ,'QT/DQT Decode'
        ,'Channel Spacing (Analog) [kHz]'
        ,'PTT ID (Analog)']
    for d in kw.getAllChannelDicts():
        channelNameDict.setdefault(d['Channel Name'],[]).append(d)
    for channelName in channelNameDict.keys():
        discrepancyFlag=False
        logLines=[]
        l=channelNameDict[channelName]
        count=len(l)
        if count>1:
            # logging.info('Channel "'+channelName+'" appears in multiple entries:')
            logLines.append('Channel "'+channelName+'" appears in multiple entries:')
            for i in range(len(l)):
                d=l[i]
                # logging.info('  Zone '+str(d['Zone Number'])+' ('+d['Zone Name']+')  Channel '+str(d['Channel Number']))
                logLines.append('  Zone '+str(d['Zone Number'])+' ('+d['Zone Name']+')  Channel '+str(d['Channel Number']))
                if i>0:
                    d0=l[0]
                    for key in keysToCompare:
                        if d[key]!=d0[key]:
                            discrepancyFlag=True
                            # logging.info('    *** DISCREPANCY: '+key+': '+d[key]+' is different than '+d0[key]+' in Zone '+str(d0['Zone Number'])+' ('+d0['Zone Name']+')  Channel '+str(d0['Channel Number']))
                            logLines.append('    *** DISCREPANCY: '+key+': '+d[key]+' is different than '+d0[key]+' in Zone '+str(d0['Zone Number'])+' ('+d0['Zone Name']+')  Channel '+str(d0['Channel Number']))
        totalLogLines+=logLines
        if discrepancyFlag:
            for line in logLines:
                logging.info(line)

    # part two: check channels that have all the same TX/RX/Enc/Dec but different name (since same-name is handled in part one)
    totalLogLines.append('-----------------------------------------')
    totalLogLines.append('INTERNAL CONSISTENCY CHECK')
    totalLogLines.append('  Part 2: Report all TX/RX/Enc sets that appear more than once in the html file, and show any discrepancies:')
    totalLogLines.append('   - channels with the same TX/RX/Enc values should have identical name/Dec/Spacing/PTT ID')
    totalLogLines.append('-----------------------------------------')
    tredDict={} # dict of lists of dicts; key syntax = <TX>:<RX>:<Enc>:<Dec>
    keysToCompare=[
            'Channel Name'
        ,'Channel Spacing (Analog) [kHz]'
        ,'PTT ID (Analog)']
    simplexAdditionalKeysToCompare=[
        'QT/DQT Decode'
    ]
    for d in kw.getAllChannelDicts():
        key=str(d['Transmit Frequency [MHz]'])+':'+str(d['Receive Frequency [MHz]'])+':'+str(d['QT/DQT Encode'])
        tredDict.setdefault(key,[]).append(d)
    for tredName in tredDict.keys():
        discrepancyFlag=False
        logLines=[]
        l=tredDict[tredName]
        count=len(l)
        if count>1:
            logLines.append('TX/RX/Enc set '+tredName+' appears in multiple entries:')
            for i in range(len(l)):
                d=l[i]
                logLines.append('  Zone '+str(d['Zone Number'])+' ('+d['Zone Name']+')  Channel '+str(d['Channel Number'])+' ('+d['Channel Name']+')')
                if i>0:
                    d0=l[0]
                    if d['Transmit Frequency [MHz]']==d['Receive Frequency [MHz]']:
                        keyList=keysToCompare+simplexAdditionalKeysToCompare
                    else:
                        keyList=keysToCompare
                    for key in keyList:
                        if d[key]!=d0[key]:
                            discrepancyFlag=True
                            logLines.append('    *** DISCREPANCY: '+key+': '+d[key]+' is different than '+d0[key]+' in Zone '+str(d0['Zone Number'])+' ('+d0['Zone Name']+')  Channel '+str(d0['Channel Number']))
        totalLogLines+=logLines
        if discrepancyFlag:
            for line in logLines:
                logging.info(line)

    logging.info('=========================================')
    logging.info('Detailed log, including discrepancies:')
    for line in totalLogLines:
        logging.info(line)
