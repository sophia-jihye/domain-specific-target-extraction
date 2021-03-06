import stanfordnlp, re
from config import parameters
import pandas as pd
from DependencyGraph import DependencyGraph
from nltk import pos_tag

class PatternHandler:
    def __init__(self):
        self.special_char_pattern = re.compile('([,.+]+.?\d*)')
        self.nlp = stanfordnlp.Pipeline()
        self.noun = ['NN', 'NNS', 'NNP']
        self.doublespace_pattern = re.compile('\s+')
    
    def leave_noun_only(self, term_list):
        term_list = [self.doublespace_pattern.sub(' ', self.special_char_pattern.sub(' ', item)) for item in term_list if item != '']   # 'sound + quality'
        term_list = [term for term, pos in pos_tag(term_list) if pos in self.noun and len(term) > 1]
        return term_list
        
    def process_targets(self, content, targets):
        content = self.special_char_pattern.sub(' ', content)   # dvds -> dvds (o) dvds.(x)
        processed_targets = []
        for target in targets:
            candidate_token = None

            if len(target.split()) > 1:   # compound target
                compound_target_with_spaces = ' ' + target + ' '
                content_with_spaces = ' ' + content + ' '
                if compound_target_with_spaces in content_with_spaces:
                    candidate_token = target
            else:   # unigram target
                for token in content.split():
                    if target == token:   # price -> price (o) lower-priced (x)
                        candidate_token = token
                        break
                    if target in token: candidate_token = token   # rip -> ripping

            if candidate_token is not None: processed_targets.append(candidate_token) # transfter (MISSPELLED) -> (DROP)

        processed_targets = self.leave_noun_only(processed_targets)
        return list(set(processed_targets))
    
    def sentence_contains_token(self, word_objects, o_word, t_word):
        flattened_string = ''.join([word_objects[i].text for i in range(len(word_objects))])
        if o_word not in flattened_string or t_word not in flattened_string:
            return False
        return True
    
    def extract_patterns_ot(self, df, pattern_counter, err_list, dependency_handler):
        cnt = 0
        for _, row in df.iterrows():    
            document = row['content']
            doc = self.nlp(document)
            for sentence_from_doc in doc.sentences:
                sentence_graph = DependencyGraph(sentence_from_doc)
                o_t = [(o,t) for o in row['opinion_words'] for t in row['targets']]
                for o_word, t_word in o_t:
                    if self.sentence_contains_token(sentence_graph.word_objects, o_word, t_word) == False: continue
                    if o_word == t_word: continue
                        
                    try: 
                        extracted_patterns = dependency_handler.extract_patterns(sentence_graph.token2indices, sentence_graph.nodes, sentence_graph.graph, sentence_graph.token2tagdep, o_word, t_word, 'ot')
                        pattern_counter['-'.join([dep_rel for token, pos, dep_rel in extracted_patterns if dep_rel != 'root'])] += 1
                        parse_error = False
                    except: parse_error = True
                        
                    err_list.append([row['content'], o_word, t_word, parse_error, row['opinion_words'], row['targets'], row['raw_targets']])
                    if cnt % 300 == 0: print('[%04dth] Extracting patterns..' % (cnt))
                    cnt += 1
                    
    def extract_patterns_tt(self, df, pattern_counter, err_list, dependency_handler):
        cnt = 0
        for _, row in df.iterrows():    
            document = row['content']
            doc = self.nlp(document)
            for sentence_from_doc in doc.sentences:
                sentence_graph = DependencyGraph(sentence_from_doc)
                t_t = [(t1,t2) for t1 in row['targets'] for t2 in row['targets'] if t1!=t2] 
                for start_word, end_word in t_t:
                    if self.sentence_contains_token(sentence_graph.word_objects, start_word, end_word) == False: continue
                    if start_word == end_word: continue
                        
                    try: 
                        extracted_patterns = dependency_handler.extract_patterns(sentence_graph.token2indices, sentence_graph.nodes, sentence_graph.graph, sentence_graph.token2tagdep, start_word, end_word, 'tt')
                        pattern_counter['-'.join([dep_rel for token, pos, dep_rel in extracted_patterns if dep_rel != 'root'])] += 1
                        parse_error = False
                    except: parse_error = True
                        
                    err_list.append([row['content'], start_word, end_word, parse_error, row['opinion_words'], row['targets'], row['raw_targets']])
                    if cnt % 300 == 0: print('[%04dth] Extracting patterns..' % (cnt))
                    cnt += 1
                    
    def extract_targets(self, doc, start_words, dep_rels, dependency_handler, predicted_targets=[]):
        targets = set()
        for sentence_from_doc in doc.sentences:
            sentence_graph = DependencyGraph(sentence_from_doc)
            targets.update(dependency_handler.extract_targets_using_pattern(sentence_graph.token2indices, sentence_graph.nodes, start_words, dep_rels))

        targets = list(targets)
        targets = self.leave_noun_only(targets)
        targets.extend(predicted_targets)
        return list(set(targets))
    
    def extract_targets_dp(self, double_propagation, doc, opinion_words, predicted_targets=[]):
        if len(predicted_targets) > 0: 
            targets = predicted_targets
        else:
            targets = set()
            for sentence_from_doc in doc.sentences:
                sentence_graph = DependencyGraph(sentence_from_doc)
                targets.update(double_propagation.extract_targets_R11(opinion_words, sentence_graph.token2indices, sentence_graph.nodes))
                targets.update(double_propagation.extract_targets_R12(opinion_words, sentence_graph.token2indices, sentence_graph.nodes))

            targets = list(targets)
            targets = self.leave_noun_only(targets)
        return list(set(targets))