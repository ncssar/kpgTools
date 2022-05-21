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

def getSynonyms(name,synonymsList):
    found=False
    rval=[name] # default return value: no synonyms, a.k.a. the name itself is the only item in the synonym set
    for l in synonymsList:
        if isinstance(l,list) and name in l:
            if found:
                logging.error('ERROR during synonym checking: '+name+' appears in more than one synonym set:')
                logging.error('  '+str(rval))
                logging.error('  '+str(l))
            found=True
            rval=l
    return rval

if __name__=="__main__":
    logging.info('kpgCheck.py - Kenwood data conversion, validation, and comparison tool')
    logging.info('  kpgCheck.py last modified: '+time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(os.path.getmtime(__file__))))
    logging.info('  Run time: '+time.strftime('%Y-%m-%d %H:%M:%S',time.localtime()))
    file1=sys.argv[1]
    fileNames=[file1]
    logging.info('  File 1: '+file1)
    if len(sys.argv)==3:
        file2=sys.argv[2]
        fileNames=[file1,file2]
        logging.info('  File 2: '+file2)
    synonymsFile='synonyms.txt'
    if os.path.isfile(synonymsFile):
        logging.info('  Channel name synonyms file: '+synonymsFile)

    # read synonyms file
    synonymsList=[] # list of lists
    with open(synonymsFile,'r') as f:
        synLines=f.readlines()
    for line in synLines:
        if not line.startswith('#'):
            try:
                parse=line.split('" "')
                parse=[x.replace('"','') for x in parse]
                parse=[x.replace('\n','') for x in parse]
                synonymsList.append(parse)
            except:
                logging.error('Error during parse of '+synonymsFile+' while reading line:')
                logging.error('  '+line)
                sys.exit(-1)
    # logging.info('synonymsList='+str(synonymsList))
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

    if len(sys.argv)<2 or os.path.splitext(sys.argv[1])[1].lower() not in ['.html','.htm']:
        print("ERROR: must specify input .htm or .html filename.")
        sys.exit(-1)

    totalLogLines=[]
    kw=[] # list of one or two KWFile objects
    chanFileNames=[]
    for fileNum in range(len(fileNames)):
        srcFileName=fileNames[fileNum]
        [srcBaseName,srcExtension]=os.path.splitext(srcFileName)
        chanFileNames.append(srcBaseName+".csv")
        logging.info('=========================================')
        logging.info('Processing File '+str(fileNum+1))
        kw.append(KWFile(srcFileName))
        kpg=kw[fileNum].soup.body.h1.string
        logging.info('Generating '+chanFileNames[fileNum]+'...')
        if 'KPG-D1N' not in kpg:
            logging.error("ERROR: only KPG-D1N html files are currently supported")
            sys.exit(-1)
        with open(chanFileNames[fileNum],'w',newline='') as csvFile:
            csvWriter=csv.writer(csvFile)
            header=['id']
            for col in colKey:
                header.append(col[1])
            csvWriter.writerow(header)
            rowNum=1
            for d in kw[fileNum].getAllChannelDicts():
                # sort by a list of keys: https://stackoverflow.com/a/21773891
                # row=sorted(d.items(),key=lambda pair: [h[0] for h in colKey].index(pair[0]))
                row=[rowNum]
                for h in colKey:
                    row.append(d[h[0]])
                csvWriter.writerow(row)
                rowNum+=1
            csvWriter.writerow(["## end"])
        logging.info('Done.')
        logging.info('=========================================')
        logging.info('File '+str(fileNum+1)+': '+fileNames[fileNum])
        logging.info('INTERNAL CONSISTENCY CHECKS - Summary of discrepancies:')
        logging.info('=========================================')
        totalLogLines.append('-----------------------------------------')
        totalLogLines.append('INTERNAL CONSISTENCY CHECK for File '+str(fileNum+1)+' : '+fileNames[fileNum])
        totalLogLines.append('  Part 1: Report all channel names that appear more than once in the html file, and show any discrepancies:')
        totalLogLines.append('   - channels with the same name should have identical TX/RX/Enc/Dec/Spacing/PTT ID')
        totalLogLines.append('-----------------------------------------')
        channelNameDict={} # dict of lists of dicts
        thisPartDiscrepancyFlag=False
        keysToCompare=[
            'Transmit Frequency [MHz]'
            ,'Receive Frequency [MHz]'
            ,'QT/DQT Encode'
            ,'QT/DQT Decode'
            ,'Channel Spacing (Analog) [kHz]'
            ,'PTT ID (Analog)']
        for d in kw[fileNum].getAllChannelDicts():
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
                thisPartDiscrepancyFlag=True
                for line in logLines:
                    logging.info(line)
        if not thisPartDiscrepancyFlag:
            totalLogLines.append('No discrepancies found for this check.')

        # part two: check channels that have all the same TX/RX/Enc/Dec but different name (since same-name is handled in part one)
        totalLogLines.append('-----------------------------------------')
        totalLogLines.append('INTERNAL CONSISTENCY CHECK for File '+str(fileNum+1)+' : '+fileNames[fileNum])
        totalLogLines.append('  Part 2: Report all TX/RX/Enc sets that appear more than once in the html file, and show any discrepancies:')
        totalLogLines.append('   - channels with the same TX/RX/Enc values should have identical name (or synonym)/Dec/Spacing/PTT ID')
        totalLogLines.append('-----------------------------------------')
        tredDict={} # dict of lists of dicts; key syntax = <TX>:<RX>:<Enc>:<Dec>
        thisPartDiscrepancyFlag=False
        keysToCompare=[
            'Channel Name'
            ,'Channel Spacing (Analog) [kHz]'
            ,'PTT ID (Analog)']
        simplexAdditionalKeysToCompare=[
            'QT/DQT Decode'
        ]
        for d in kw[fileNum].getAllChannelDicts():
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
                            if str(d[key]).lower()!=str(d0[key]).lower():
                                # if key=='Channel Name':
                                #     logLines.append('  chan='+d[key]+'   synonyms='+str(getSynonyms(d0[key],synonymsList)))
                                if key=='Channel Name' and d[key] in getSynonyms(d0[key],synonymsList):
                                    logLines.append('    ** Channel name '+d[key]+' is different than '+d0[key]+' in Zone '+str(d0['Zone Number'])+' ('+d0['Zone Name']+')  Channel '+str(d0['Channel Number'])+' but they are legal synonyms')
                                else:
                                    discrepancyFlag=True
                                    logLines.append('    *** DISCREPANCY: '+key+': '+d[key]+' is different than '+d0[key]+' in Zone '+str(d0['Zone Number'])+' ('+d0['Zone Name']+')  Channel '+str(d0['Channel Number']))
            totalLogLines+=logLines
            if discrepancyFlag:
                thisPartDiscrepancyFlag=True
                for line in logLines:
                    logging.info(line)
        if not thisPartDiscrepancyFlag:
            totalLogLines.append('No discrepancies found for this check.')
        
        # part three: all simplex channels should have dec=None or dec=enc
        totalLogLines.append('-----------------------------------------')
        totalLogLines.append('INTERNAL CONSISTENCY CHECK for File '+str(fileNum+1)+' : '+fileNames[fileNum])
        totalLogLines.append('  Part 3: All simplex channels should have dec=None or dec=enc')
        totalLogLines.append('-----------------------------------------')
        thisPartDiscrepancyFlag=False
        for d in kw[fileNum].getAllChannelDicts():
            logLines=[]
            discrepancyFlag=False
            if d['Transmit Frequency [MHz]']==d['Receive Frequency [MHz]']:
                enc=d['QT/DQT Encode']
                dec=d['QT/DQT Decode']
                if dec!='None' and dec!=enc:
                    discrepancyFlag=True
                    logLines.append('Simplex channel enc/dec check:')
                    logLines.append('  Zone '+str(d['Zone Number'])+' ('+d['Zone Name']+')  Channel '+str(d['Channel Number'])+' ('+d['Channel Name']+')')
                    logLines.append('    *** DISCREPANCY: Enc = '+str(enc)+'  Dec = '+str(dec))
            totalLogLines+=logLines
            if discrepancyFlag:
                thisPartDiscrepancyFlag=True
                for line in logLines:
                    logging.info(line)
        if not thisPartDiscrepancyFlag:
            totalLogLines.append('No discrepancies found for this check.')

    ############################################
    # compare files if second file is specified
    ############################################
    if len(kw)>1:
        logging.info('=========================================')
        logging.info('File 1 vs File 2: comparison of generated .csv files')
        logging.info(' File 1 .csv: '+chanFileNames[0])
        logging.info(' File 2 .csv: '+chanFileNames[1])
        logging.info('=========================================')

        from csv_diff import load_csv, compare
        import json
        csv1=load_csv(open(chanFileNames[0]),key='id')
        csv2=load_csv(open(chanFileNames[1]),key='id')
        diff=compare(csv1,csv2)
        # logging.info(json.dumps(diff,indent=3))
        for changeDict in diff['changed']:
            d=csv1[changeDict['key']]
            logging.info('Zone '+d['Zone#']+' ('+d['Zone Name']+')  Channel '+d['Chan#']+' ('+d['Channel Name']+') : ')
            for changeKey in changeDict['changes']:
                changeVal=changeDict['changes'][changeKey]
                logging.info('  '+changeKey+' : '+changeVal[0]+' (File 1) vs. '+changeVal[1]+' (File 2)')

        logging.info(' ')
        logging.info('Attempting to launch WinMerge on the generated .csv files...')
        winmerge=r'C:\Program Files (x86)\WinMerge\WinMergeU.exe'
        if os.path.isfile(winmerge):
            import subprocess
            subprocess.Popen([r'C:\Program Files (x86)\WinMerge\WinMergeU.exe',chanFileNames[0],chanFileNames[1]])

        # dl1=kw[0].getAllChannelDicts()
        # dl2=kw[1].getAllChannelDicts()
        # for d in dl1:
        #     key=str(d['Zone Number'])+d['Zone Name']+str(d['Channel Number'])+d['Channel Name']




    logging.info('=========================================')
    logging.info(' ')
    logging.info('Detailed log, including discrepancies:')
    for line in totalLogLines:
        logging.info(line)
