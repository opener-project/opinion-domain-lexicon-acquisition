#!/usr/bin/env python

import sys
import glob
import os
import math
import csv

import math

def mean(values):
    return sum(values)*1.0/len(values)

def stdev(values):
    m = mean(values)
    aux = [v - m for v in values]
    dev = [x*x for x in aux]
    SD = math.sqrt(sum(dev)/len(values))
    return SD


def process_ngrams(folder_indexes, this_len):
    print 'Processing',folder_indexes,'len:',this_len
    sys.stdout.flush()
    
    frequencies = {}
    log_values_for_word = {}
    total_freq_for_rating = {}
    for index_for_rating in glob.glob(folder_indexes+'/index_rating_*'):
        print '  Doing',index_for_rating
        sys.stdout.flush()
        rating = int(index_for_rating[index_for_rating.rfind('_')+1:])
        
        file_index = '%s/ngrams.len_%d.idx.txt' % (index_for_rating,this_len)
        words_for_this_index = set()
        if os.path.exists(file_index):
            fd = open(file_index)
            for line in fd:
                line = line.decode('utf-8').strip()
                fields = line.split(' ')
                fields_tokens = fields[1].split('\t')

                freq = int(fields[0])
                this_string = ' '.join(fields_tokens[0:this_len])
                if this_string not in words_for_this_index:
                    #Because of the POS could be several lines with the same string and different pos
                    #we take the most frequent (the first one)
     
                    if this_string not in frequencies:
                        frequencies[this_string] = [(rating,freq)]
                    else:
                        frequencies[this_string].append((rating,freq))
                        
                    if rating not in total_freq_for_rating:
                        total_freq_for_rating[rating] = freq
                    else:
                        total_freq_for_rating[rating] += freq
                    words_for_this_index.add(this_string)
            fd.close()
    print '  Calculating logs'
    sys.stdout.flush()
    for word, list_frequencies in frequencies.items():
        log_values_for_word[word]=[]
        for rating, freq in list_frequencies:
            total_words_for_rating = total_freq_for_rating[rating]
            value = math.log(freq/float(total_words_for_rating-freq))
            log_values_for_word[word].append((rating,value))

    print '  Calculating the standard deviation'
    #Calculating the stdev for each 
    stdev_for_words = {}
    for word, pairs_rating_value in log_values_for_word.items():
        values = [x for _,x in pairs_rating_value]
        this_stdev = stdev(values)
        stdev_for_words[word]=this_stdev
        
    ##Process the results and end
    ##Calculate the maximum per file we want to store
    total_words = len(stdev_for_words)
    percent = 25
    maximum = int(total_words*25/100)
    
    print '  Saving results'
    fd = open('lexicon_len%d.csv' % (this_len),'wb')
    my_writer = csv.writer(fd,delimiter=';',quoting=csv.QUOTE_MINIMAL)
    cnt = 0
    for word, this_stdev in sorted(stdev_for_words.items(),key=lambda t: t[1], reverse=True):
        this_row = [word.encode('utf-8')]
        values = sorted(log_values_for_word[word],key=lambda t:t[1],reverse=True)
        best_rating = values[0][0]
        this_row.append(str(best_rating))
        this_row.append(str(round(this_stdev,2)))
        
        list_of_stdevs = ""
        for rating, value in values:
            list_of_stdevs+=str(rating)+'='+str(round(value,2))+' '
    
        this_row.append(list_of_stdevs.rstrip())
        my_writer.writerow(this_row)
        cnt += 1
        
        if cnt >= maximum:
            break
        
    fd.close()
    print 'Output CSV in',fd.name
    del frequencies
    del log_values_for_word  
    del total_freq_for_rating
    del stdev_for_words

if __name__ == '__main__':
  #indexes = 'dutch_rating_indexes'
  indexes = 'english_rating_indexes'
  indexes = sys.argv[1]
  for len_ngram in [1,2,3]:
      process_ngrams(indexes,len_ngram)
  