#!/usr/bin/env python


import sys
import os
import argparse
import glob
import csv
from collections import defaultdict, Counter
from operator import itemgetter
from KafNafParserPy import KafNafParser

VERSION='0.1'
__extensions_allowed__ = ['kaf','naf']  # Set it to None to get all the files within the folder
EXP = 'expression'
TAR = 'target'

# Loads the data from a list of path, or from a folder
# __extensions_allowed controls in case of the folder the extension of files
# To be added. Set it to None to select ALL the files within the folder
def load_data(arguments):
    list_files = []
    if arguments.list_files:
        if not os.path.exists(arguments.list_files):
            print>>sys.stderr,'ERROR: file',arguments.list_files,'not found.'
            sys.exit(-1)
        fic = open(arguments.list_files)
        for line in fic:
            list_files.append(line.strip())
        fic.close()
    elif arguments.folder:
        if not os.path.exists(arguments.folder):
            print>>sys.stderr,'ERROR: folder',arguments.folder,'not found.'
            sys.exit(-1)
        if __extensions_allowed__ is None:
            for file in glob.glob(arguments.folder+'/*'):
                list_files.append(file)
        else:
            for ext in __extensions_allowed__:
                for file in glob.glob(arguments.folder+'/*.'+ext):
                    list_files.append(file)
    return list_files


def process_file(this_file,token_freq):
    xml_obj = KafNafParser(this_file)
    print>>sys.stderr,'Processing file',this_file
    token_for_wid = {}
    order_for_wid = {}
    opinion_expressions = []
    opinion_targets = []
    whole_text = ' '
    for n, token in enumerate(xml_obj.get_tokens()):
        text = token.get_text().lower()
        token_freq[text] += 1
        token_for_wid[token.get_id()] = text
        order_for_wid[token.get_id()] = n
        whole_text += text + ' '
    wids_for_tid = {}
    lemma_for_wid = {}
    pos_for_wid = {}
    for term in xml_obj.get_terms():
        tid = term.get_id()
        wids = term.get_span().get_span_ids()
        wids_for_tid[tid] = wids
        for wid in wids:
            lemma_for_wid[wid] = term.get_lemma()
            pos_for_wid[wid] = term.get_pos()
        
    
    already_counted = {EXP:set(), TAR:set()}
    
    for opinion in xml_obj.get_opinions():   
        for this_type, opinion_obj in [(EXP,opinion.get_expression()),(TAR,opinion.get_target())]:
            if opinion_obj is not None:
                span = opinion_obj.get_span()
                if span is not None:
                    list_wids = []
                    for tid in span.get_span_ids():
                        list_wids.extend(wids_for_tid.get(tid,[]))
                    list_wids.sort(key=lambda wid: order_for_wid[wid])  ##Sorted according the the order of the tokens
                    
                    string_wids = '#'.join(list_wids)
                    opinion_tokens = ' '.join( token_for_wid[wid] for wid in list_wids)
                    opinion_lemmas = ' '.join( lemma_for_wid[wid] for wid in list_wids)
                    opinion_pos    = ' '.join( pos_for_wid[wid]   for wid in list_wids)
                    
                   
                    if string_wids not in already_counted[this_type]:
                        if this_type == EXP:
                            polarity = (opinion_obj.get_polarity()).lower()
                            opinion_expressions.append((opinion_tokens,polarity,opinion_lemmas,opinion_pos))
                        else:
                            opinion_targets.append((opinion_tokens,opinion_lemmas,opinion_pos))
                        already_counted[this_type].add(string_wids)    
      
    del xml_obj
    print>>sys.stderr,'\tNumber of opinion expressions:',len(opinion_expressions)
    print>>sys.stderr,'\tNumber of opinion targets:',len(opinion_targets)
    print>>sys.stderr,'\tNumber of characters of the text:',len(whole_text)
    return opinion_expressions, opinion_targets, whole_text
    
    
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Extract expressions and targets from annotated data')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-l','--list',dest='list_files',help='A file with a list of paths to KAF/NAF files', metavar='file_with_list')
    group.add_argument('-f','--folder', dest='folder',help='A folder with KAF/NAF files', metavar='folder')
    parser.add_argument('-exp_csv', dest='exp_csv_fd',type = argparse.FileType('wb'), help='CSV file to store the expressions', required=True, metavar='expressions_file.csv')
    parser.add_argument('-tar_csv', dest='tar_csv_fd', type = argparse.FileType('wb'), help='CSV file to store the targets', required=True, metavar='targets_file.csv')
    
    arguments = parser.parse_args()
    list_files = load_data(arguments)
    
    
    token_freq = defaultdict(int)            # The complete token frequency               
    all_expressions = []
    all_targets = []
    all_texts = []
    for file in list_files[:]:
        opinion_expressions, opinion_targets, whole_text =  process_file(file,token_freq)
        all_expressions.extend(opinion_expressions)
        all_targets.extend(opinion_targets)
        all_texts.append(whole_text)
        
    
    ## EXPRESSIONS
    distrib_expressions = defaultdict(int)
    lemmas_for_tokens   = defaultdict(list)
    pos_for_tokens      = defaultdict(list)
     
    for tokens, polarity, lemmas, postags in all_expressions:
        this_key = tokens+'#'+polarity
        distrib_expressions[this_key] += 1
        lemmas_for_tokens[tokens].append(lemmas)
        pos_for_tokens[tokens].append(postags)
        

        
    final_expressions = []
    print>>sys.stderr,'Total unique number of expression#polarity:', len(distrib_expressions)
    for exp_pol, rel_freq in distrib_expressions.items():
        exp = exp_pol[:exp_pol.rfind('#')]
        this_over_freq = sum(text.count(' '+exp+' ') for text in all_texts)
        if this_over_freq < rel_freq: ## This is one of the errors where the expression is not continuos in the text
            print>>sys.stderr,'Error expression not continuous:',exp.encode('utf-8'),' Not included in output'
        else:
            ratio = rel_freq/this_over_freq
            final_expressions.append((exp_pol,exp,rel_freq,this_over_freq,ratio))
        
    ##Sorted first by ratio, second by relative frequency and third by number of words
    ##Sorted by
    # 1 minium number of words first
    # 2 ratio 
    # 3 relative frequency
    expression_writer = csv.writer(arguments.exp_csv_fd, delimiter=';', quoting=csv.QUOTE_ALL)
    labels = ['exp#pol','ratio','RelatFreq','OverallFreq','lemmas','postags','FreqWords']
    expression_writer.writerow(labels)
    print 'EXPRESSIONS'
    for exp_pol,exp, rel_freq,this_over_freq,ratio in sorted(final_expressions,key=lambda t: (-len(t[1].split()),t[4],t[2],),reverse=1):
        this_row = []
        this_row.append(exp_pol.encode('utf-8'))
        this_row.append(ratio)
        this_row.append(rel_freq)
        this_row.append(this_over_freq)
        this_row.append((Counter(lemmas_for_tokens[exp]).most_common()[0][0]).encode('utf-8'))
        this_row.append((Counter(pos_for_tokens[exp]).most_common()[0][0]).encode('utf-8'))
        my_str = ' '.join(token.encode('utf8')+'#'+str(token_freq[token]) for token in exp.split())
        this_row.append(my_str)                             
        expression_writer.writerow(this_row)
        
        print 'Expression:',exp_pol.encode('utf-8')
        print '  lemmas:',(Counter(lemmas_for_tokens[exp]).most_common()[0][0]).encode('utf-8')
        print '  pos:',(Counter(pos_for_tokens[exp]).most_common()[0][0]).encode('utf-8')
        print '  rel ',rel_freq
        print '  over',this_over_freq
        print '  ratio',ratio
        print '  freqtokens ',
        for token in exp.split():
            print token.encode('utf8')+': '+str(token_freq[token]),
        print
    arguments.exp_csv_fd.close()
    
    ##########
    #########
                             
    ## TARGETS
    distrib_targets = defaultdict(int)
    lemmas_for_tokens_tar   = defaultdict(list)
    pos_for_tokens_tar      = defaultdict(list)
     
    for tokens, lemmas, postags in all_targets:
        distrib_targets[tokens] += 1
        lemmas_for_tokens_tar[tokens].append(lemmas)
        pos_for_tokens_tar[tokens].append(postags)
        

    print>>sys.stderr,'Total unique number of targets:', len(distrib_targets)

    final_targets = []
    for target, rel_freq in distrib_targets.items():
        this_over_freq = sum(text.count(' '+target+' ') for text in all_texts)
        if this_over_freq < rel_freq: ## This is one of the errors where the expression is not continuos in the text
            print>>sys.stderr,'Error target not continuous:',target.encode('utf-8'),' Not included in output'
        else:
            ratio = rel_freq/this_over_freq
            final_targets.append((target,rel_freq,this_over_freq,ratio))
        
    print
    print 'TARGETS'
    ##Sorted
    # 1 minium number of words first
    # 2 ratio 
    # 3 relative frequency
    target_writer = csv.writer(arguments.tar_csv_fd,delimiter=';', quoting=csv.QUOTE_ALL)
    labels = ['target','ratio','RelatFreq','OverallFreq','lemmas','postags','FreqWords']
    target_writer.writerow(labels)
    for target, rel_freq,this_over_freq,ratio in sorted(final_targets,key=lambda t: (-len(t[0].split()),t[3],t[1],),reverse=1):
        this_row = []
        this_row.append(target.encode('utf-8'))
        this_row.append(ratio)
        this_row.append(rel_freq)
        this_row.append(this_over_freq)
        this_row.append((Counter(lemmas_for_tokens_tar[target]).most_common()[0][0]).encode('utf-8'))
        this_row.append((Counter(pos_for_tokens_tar[target]).most_common()[0][0]).encode('utf-8'))
        my_str = ' '.join(token.encode('utf8')+'#'+str(token_freq[token]) for token in target.split())
        this_row.append(my_str)                             
        target_writer.writerow(this_row)
        
        print 'Target:', target.encode('utf-8')
        print '  lemmas:',(Counter(lemmas_for_tokens_tar[target]).most_common()[0][0]).encode('utf-8')
        print '  pos:',(Counter(pos_for_tokens_tar[target]).most_common()[0][0]).encode('utf-8')
        print '  rel ',rel_freq
        print '  over',this_over_freq
        print '  ratio',ratio
        print '  freqtokens ',
        for token in target.split():
            print token.encode('utf8')+': '+str(token_freq[token]),
        print
    arguments.tar_csv_fd.close()
    sys.exit(0)

  
