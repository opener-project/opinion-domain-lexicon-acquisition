#!/usr/bin/env python

import sys
import operator
import math
import string
import os
import argparse
import csv

from collections import defaultdict
from lib.ngram_frequency_index import Cngram_index_enquirer

__this_folder__ = os.path.dirname(os.path.realpath(__file__))
STOP_WORDS_FOLDER='resources/stop_words'

def guess_polarity(enquirer, polarity_word,seeds, patterns_polarity_guessing,verbose):
    hits_as_positive = []
    hits_as_negative = []
    for seed, polarity_seed in seeds:
        #polarity_seed can be + or -
        
        for pattern_type, pattern in patterns_polarity_guessing:
            #pattern_type can be = or !
            #pattern something like [A] and [B]
            this_query = pattern.replace('[A]',seed)
            this_query = this_query.replace('[B]',polarity_word)
            hits = 0
            results = query(enquirer,this_query)
            if len(results) != 0:
                hits = results[0][2]

            this_query = pattern.replace('[A]',polarity_word)
            this_query = this_query.replace('[B]',seed)
            hits2 = 0
            results = query(enquirer,this_query)
            if len(results) != 0:
                hits2 = results[0][2]
            
            #Where to store the hits..
            if (polarity_seed == '+' and pattern_type == '=') or ( polarity_seed == '-' and pattern_type == '!'):
                hits_as_positive.extend([hits,hits2])
            elif (polarity_seed == '-' and pattern_type == '=') or ( polarity_seed == '+' and pattern_type == '!'):
                hits_as_negative.extend([hits,hits2])
                         
    ##Calculate the averages:
    avg_as_positive = sum(hits_as_positive) * 1.0 / len(hits_as_positive)
    avg_as_negative = sum(hits_as_negative) * 1.0 / len(hits_as_negative)
    
    guessed_pol = 'neutral'
    if avg_as_positive > avg_as_negative:
        guessed_pol = 'positive'
    elif avg_as_negative > avg_as_positive:
        guessed_pol = 'negative'
        
    if verbose:
        print 'Guessed polarity for ',polarity_word.encode('utf-8')
        print '\tAvg hits as positive: ',avg_as_positive
        print '\tAvg hits as negative: ',avg_as_negative
        print '\tAssigned polarity ',guessed_pol
    return guessed_pol

def load_stop_words(language):
    stop_words = set()
    stop_word_filename = os.path.join(__this_folder__,STOP_WORDS_FOLDER,language+'.txt')
    if os.path.exists(stop_word_filename):
        fic = open(stop_word_filename)
        for line in fic:
            stop_words.add(line.strip().decode('utf-8'))    ## File expected to be UTF-8
        fic.close()
    else:
        print>>sys.stderr,'Stop words file',stop_word_filename,'not found.\n Stopwords filtering not used'
    return stop_words


def query(enquirer, query,min_freq=1):
    found = []
    items = enquirer.query(query,only_match = True)
    if items == None or len(items)==0:
        return []
    
    for n, item in enumerate(items):
        token_str = item.get_word()
        list_pos = ''.join(item.get_pos())  ##We create a string out of a list, like GDA
        hits = item.get_hits()
        if hits >= min_freq:
            found.append((token_str,list_pos, hits))
    return found


def valid_pos(this_pos, allowed_list_pos):
    is_valid = False
    for allowed_pos in allowed_list_pos:
        if allowed_pos in this_pos:
            is_valid = True
            break
    return is_valid
        
def filter_targets(map_targets, stop_words, allowed_list_pos):  #set allowed_list_pos to None to allow all pos
    filtered_targets = []
    for (target, pos), list_values in map_targets.items():
        if allowed_list_pos is None:
            is_valid_pos = True
        else:
            is_valid_pos = valid_pos(pos,allowed_list_pos) 
        if is_valid_pos:
            if target not in stop_words:
                if target not in string.punctuation:
                    val = sum(v for num_iter,idx_pattern, v in list_values)
                    if val > 0:
                        filtered_targets.append((target,pos,list_values))
    
    return filtered_targets  
    #return sorted(filtered_targets,key=lambda this_tuple: sum(v for _,_,v in this_tuple[2]), reverse=True)


def filter_expressions(map_expressions, stop_wordsm, allowed_list_pos): #set allowed_list_pos to None to allow all pos
    filtered_exps = []
    for (exp,pos), list_values in map_expressions.items():
        if allowed_list_pos is None:
            is_valid_pos = True
        else:
            is_valid_pos = valid_pos(pos,allowed_list_pos) 

        if is_valid_pos:
            if exp not in stop_words:
                if exp not in string.punctuation:
                    val = sum(v for num_iter,idx_pattern, v in list_values)
                    if val > 0:
                        filtered_exps.append((exp,pos,list_values))
    return filtered_exps
    #return sorted(filtered_exps, key=lambda this_tuple: sum(v for _,_,v in this_tuple[2]), reverse=True)
                                                                          

if __name__ == '__main__':
    ## ARGUMENTS
    argument_parser = argparse.ArgumentParser(description='Creates expression and target lexicons from domain raw data')
    required = argument_parser.add_argument_group('Required arguments')
    required.add_argument('-index',dest='index_folder',metavar='index_folder',help='Folder with ngram indexes', required=True)
    required.add_argument('-seeds','-s',dest='seed_fd', metavar='file_with_seeds', type= argparse.FileType('rb'), help='File with seeds, one per line', required=True)
    required.add_argument('-patterns','-p',dest='patterns_fd', metavar='file_with_patterns', type= argparse.FileType('rb'), help='File with patterns, one per line (example-> "a [Exp] [Tar]")', required=True)
    required.add_argument('-p_pol',dest='patterns_pol_guess_fd', metavar='file_with_patterns', type= argparse.FileType('rb'), help='File with patterns for guessing the polarity, one per line (example-> "# [A] and [B]")', required=True)
    required.add_argument('-lex_pol',dest='lexpol_fd', metavar='pol_lex', type= argparse.FileType('wb'), help='File to store the POLARITY lexicon', required=True)
    required.add_argument('-lex_tar',dest='lextar_fd', metavar='pol_tar', type= argparse.FileType('wb'), help='File to store the TARGET lexicon', required=True)
     
    argument_parser.add_argument('-lang,','-l', dest='lang', metavar="lang_code", help='Force to use this lang, otherwise the language from the indexs is used')
    argument_parser.add_argument('-no_verbose', dest='verbose', action='store_false', help='No verbose log information')
    argument_parser.add_argument('-min_freq','-mf', dest='min_freq', type=int,default=1,metavar='integer',help='Minimum frequency allowed for a query (default 1)')
    argument_parser.add_argument('-target_pos',dest='tar_pos',default='N',metavar='list of tags "N R G"', help='Allowed pos tags for targets (default "N" nouns) Use ALL for all possible pos')
    argument_parser.add_argument('-expression_pos',dest='exp_pos',default='G',metavar='list of tags "N R G"', help='Allowed pos tags for expressions (default "G" adjectives) Use ALL for all possible pos')
    argument_parser.add_argument('-max_iter',dest='max_iter', type=int, default=5, metavar='integer', help='Maximum number of iterations (default 5)')
    arguments = argument_parser.parse_args()
    ### END ARGUMENTS ###
    
    enquirer = Cngram_index_enquirer(arguments.index_folder)
    if arguments.verbose:
        print 'Ngram index loaded from',arguments.index_folder
        print 'Minimum frequency allowed for query:',arguments.min_freq
        
    my_lang = arguments.lang
    if my_lang is None:
        my_lang = enquirer.get_language()
        if arguments.verbose: print 'Using language from the index:', my_lang
    else:
        if arguments.verbose: print 'Using language from parameters:',my_lang
  
    stop_words = load_stop_words(my_lang)
    if arguments.verbose: print 'Loaded',len(stop_words),'stop words'
    
    ## Reading allowed pos tags
    if arguments.tar_pos == 'ALL':
        print 'Allowed pos tags for targets: ALL'
        allowed_tar_pos = None
    else:
        allowed_tar_pos = arguments.tar_pos.split(' ')
        print 'Allowed pos tags for targets:', allowed_tar_pos
    
    if arguments.exp_pos == 'ALL':
        print 'Allowed pos tags for expressions: ALL'
        allowed_exp_pos = None
    else:
        allowed_exp_pos = arguments.exp_pos.split(' ')
        print 'Allowed pos tags for expressions', allowed_exp_pos       
    ##################
        
    
    ###################
    ## Load the seeds #
    ###################
    seeds = []
    for line in arguments.seed_fd:
        if line[0] != '#':
            fields = line.strip().decode('utf-8').split(' ')
            seeds.append((' '.join(fields[:-1]),fields[1]))
    arguments.seed_fd.close()
    
    if arguments.verbose:
        print 'Loaded',len(seeds),'seeds ('+str(seeds)+')'
    #################
    
    ######################
    ## Load the patterns #
    ######################
    patterns = []
    for line in arguments.patterns_fd:
        patterns.append(line.strip().decode('utf-8'))
    arguments.patterns_fd.close()
    if arguments.verbose:
        print 'Loaded',len(patterns),'patterns'
    ######################
    
    
    ######################
    ## Load the patterns for polarity guessing#
    #######
    patterns_polarity_guessing = []
    for line in arguments.patterns_pol_guess_fd:
        if line[0] != '#':
            line = line.strip().decode('utf-8')
            this_type = line[0]
            this_pat = line[2:]
            patterns_polarity_guessing.append((this_type,this_pat))
    arguments.patterns_pol_guess_fd.close()
    if arguments.verbose:
        print 'Loaded',len(patterns_polarity_guessing),'patterns for guessing the polarity'
    
    ############################################
    ############################################
    ### STARTING THE PROPAGATION ###############
    ############################################
    ############################################

    all_expressions = {}
    new_expressions = []
    for seed, polarity in seeds:
        all_expressions[seed] = [(0,0,10)]
        new_expressions.append((seed,10))
    all_targets = {}
    
    
    num_iter = 0

    while True:
        if arguments.verbose: print 'Iteration num:',num_iter
        if num_iter > arguments.max_iter:
            break
        
        ##############################################################
        ## TARGET PART #
        ##############################################################
        targets = defaultdict(list)  ## targets['hotel'] = [1.0, 3.2, 0.34]
        if arguments.verbose: print '  Finding targets'
        for ns, (seed,value_seed) in enumerate(new_expressions):
            if arguments.verbose: print '    Seed ',ns,'of',len(new_expressions),':', seed.encode('utf-8')
            for idx_pattern, pattern in enumerate(patterns):
                pattern = pattern.replace('[EXP]',seed)
                pattern = pattern.replace('[TAR]','*')
                if arguments.verbose: print '      Pattern:',pattern.encode('utf-8')
                
                possible_targets = query(enquirer,pattern,arguments.min_freq)
                
            
                for target, postags, value in possible_targets:
                    #The value for this target depends on:
                    # -> the value of the seed where it comes from
                    # -> the iteration
                    # -> the number of hits
                    value_for_target = math.log10(value * value_seed / (num_iter+1))
                    targets[(target,postags)].append((num_iter,idx_pattern,value_for_target))
                del possible_targets

        
        filtered_targets = filter_targets(targets, stop_words,allowed_tar_pos)  # List of (token, val)
        del targets
        ##############################################################
               
        new_targets = []
        for target, pos, list_values in filtered_targets:
            #The value for the target will be the sum of all the values:
            value_for_new_target = sum(v for _,_,v in list_values)
            if target in all_targets:
                all_targets[target].extend(list_values)
            else:
                if target not in all_expressions:
                    all_targets[target] = list_values
                    new_targets.append((target,value_for_new_target))
                
    
        ##############################################################
        ## EXPRESSION PART #
        ##############################################################   
        if arguments.verbose: print '  Expression'
        expressions = defaultdict(list)
        for nt, (target,value_target) in enumerate(new_targets):
            if arguments.verbose: print '  Target',nt,'of',len(new_targets),':',target.encode('utf-8')
            for pattern in patterns:
                pattern = pattern.replace('[EXP]','*')
                pattern = pattern.replace('[TAR]',target)
                if arguments.verbose: print '    Pattern:', pattern.encode('utf-8')        
                possible_exps = query(enquirer,pattern,arguments.min_freq)
                
                for exp, postag, value_exp in possible_exps:
                    #print value_exp,value_target,num_iter+1
                    value_exp = math.log10(value_exp * value_target / (num_iter+1))
                    expressions[(exp,postag)].append((num_iter,idx_pattern,value_exp))
        filtered_expressions = filter_expressions(expressions, stop_words, allowed_exp_pos)
        
        new_expressions = []
        for exp, postag, list_values in filtered_expressions:
            value_for_new_exp = sum(v for _,_,v in list_values)
            if exp in all_expressions:
                all_expressions[exp].extend(list_values)
            else:
                if exp not in all_targets:
                    all_expressions[exp] = list_values
                    new_expressions.append((exp,value_for_new_exp))
        
        
        if False and arguments.verbose: 
            print 'Iteration number:', num_iter
            print '    New targets on this iteration'
            for n, target in enumerate(new_targets):
                print '      tar_'+str(n),target #.encode('utf-8')
            print
            print '    New expressions on this iteration'
            for n, exp in enumerate(new_expressions):
                print '      exp_'+str(n),exp#.encode('utf-8')
            print
               
        if len(new_expressions) == 0:  #End of propagation
            break
        
        num_iter += 1

    polarity_writer = csv.writer(arguments.lexpol_fd, delimiter=';', quoting=csv.QUOTE_MINIMAL)
    this_row = ['expression','polarity','overall_confidence','avg_confidence']
    polarity_writer.writerow(this_row)
    target_writer = csv.writer(arguments.lextar_fd, delimiter=';', quoting=csv.QUOTE_MINIMAL)
    this_row = ['target','overall_confidence','avg_confidence']
    target_writer.writerow(this_row)
   
    #######
    print '#'*50
    print 'FINAL LEXICONS'
    print '  EXPRESSIONS'
    #Value is a triple
    for n, (exp, values) in enumerate(sorted(all_expressions.items(),key=lambda pair: sum(v for _,_,v in pair[1]), reverse=True)):
        this_row = []
        total_values = 0
        count_idx_pattern = defaultdict(int)

        for num_iter, idx_pattern, val in values:
            total_values += val
            count_idx_pattern[idx_pattern] += 1
            
        this_row.append( exp.encode('utf-8'))
        print '\t','exp_'+str(n), exp.encode('utf-8')
        polarity = guess_polarity(enquirer, exp, seeds, patterns_polarity_guessing,arguments.verbose or True) 
        print '\t   Guessed polarity:',polarity
        this_row.append(polarity)
        print '\t   Total values:',len(values)
        print '\t   Sum values (sorted by this):',total_values
        this_row.append(str(total_values))
        print '\t   Avg total freq',total_values*1.0/len(values)
        this_row.append(str(total_values*1.0/len(values)))
        for idx,cnt in sorted(count_idx_pattern.items(),key=lambda t: -t[1]):
            print '\t    ', patterns[idx], cnt
        sys.stdout.flush()
        polarity_writer.writerow(this_row)
        #for num_iter, pattern, val in values:
        #    print '\t    iternum:',num_iter,' pattern:',pattern
            
    print '  TARGETS'
    for n, (tar, values) in enumerate(sorted(all_targets.items(),key=lambda pair: sum(v for _,_,v in pair[1]), reverse=True)):
        total_values = 0
        count_idx_pattern = defaultdict(int)

        for num_iter, idx_pattern, val in values:
            total_values += val
            count_idx_pattern[idx_pattern] += 1
        this_row = [tar.encode('utf-8')]
        print '\t','tar'+str(n), tar.encode('utf-8')
        print '\t   Total values:',len(values)
        print '\t   Sum values (sorted by this):',total_values
        this_row.append(str(total_values))
        print '\t   Avg total freq',total_values*1.0/len(values)
        this_row.append(str(total_values*1.0/len(values)))
        for idx,cnt in sorted(count_idx_pattern.items(),key=lambda t: -t[1]):
            print '\t    ', patterns[idx], cnt
        #for num_iter, pattern, val in values:
        #    print '\t    iternum:',num_iter,' pattern:',pattern
        target_writer.writerow(this_row)

    print '#'*50   
        
    arguments.seed_fd.close()
    arguments.lexpol_fd.close()
    arguments.lextar_fd.close()
    print 'CSV OUTPUT LEXICONS:'
    print '\tPolarity lexicon:',arguments.lexpol_fd.name
    print '\tTarget lexicon:',arguments.lextar_fd.name
    
    sys.exit(0)
        
  