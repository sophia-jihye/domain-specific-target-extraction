from collections import defaultdict, namedtuple
import networkx as nx
import re
from config import parameters

Node = namedtuple("Node", ["idx", "token", "pos", "dep", "governor"])
class DependencyGraphHandler:
    def __init__(self):
        self.number_pattern = re.compile('\d+')
        self.errlog_filepath = parameters.errlog_filepath
        
    def write_errlog(self, content):
        filepath = self.errlog_filepath
        text_file = open(filepath, "w", encoding='utf-8')
        text_file.write(content)
        text_file.close()
        print("Error occurred: ", filepath)
        
    def handle_hyphen_or_compound(self, word, delimiter, token2idx, nodes):
        indices = []
        for token in word.split(delimiter):
            indices.extend(token2idx[token])
        root_words = [nodes[i].token for i in indices if nodes[i].governor not in indices]
        return root_words[0]   
    
    def remove_number(self, word):
        return self.number_pattern.sub('', word)
    
    def extract_patterns(self, token2idx, nodes, graph, token2tagdep, start_word, end_word, pattern_type):
        entity1, entity2 = start_word, end_word
        if pattern_type == 'ot':
            if start_word not in token2idx.keys() and '-' in start_word: 
                entity1 = self.handle_hyphen_or_compound(start_word, '-', token2idx, nodes)
            if end_word not in token2idx.keys() and '-' in end_word: 
                entity2 = self.handle_hyphen_or_compound(end_word, '-', token2idx, nodes)
            if end_word not in token2idx.keys() and ' ' in end_word: 
                entity2 = self.handle_hyphen_or_compound(end_word, ' ', token2idx, nodes)
            if end_word not in token2idx.keys() and bool(re.search(r'\d', end_word)):
                entity2 = self.remove_number(end_word)
        elif pattern_type == 'tt':
            if start_word not in token2idx.keys() and '-' in start_word: 
                entity1 = self.handle_hyphen_or_compound(start_word, '-', token2idx, nodes)
            if start_word not in token2idx.keys() and ' ' in start_word: 
                entity1 = self.handle_hyphen_or_compound(start_word, ' ', token2idx, nodes)
            if start_word not in token2idx.keys() and bool(re.search(r'\d', start_word)):
                entity1 = self.remove_number(start_word)
            if end_word not in token2idx.keys() and '-' in end_word: 
                entity2 = self.handle_hyphen_or_compound(end_word, '-', token2idx, nodes)
            if end_word not in token2idx.keys() and ' ' in end_word: 
                entity2 = self.handle_hyphen_or_compound(end_word, ' ', token2idx, nodes)
            if end_word not in token2idx.keys() and bool(re.search(r'\d', end_word)):
                entity2 = self.remove_number(end_word)
        shortest_path = nx.shortest_path(graph, source=entity1, target=entity2)
                
        return [token2tagdep[token] for token in shortest_path]
    
    def next_focused_token_indices(self, current_token_indices, nodes, dep_rel):
        focused_token_indices = set()
        for current_token_idx in current_token_indices:
            if nodes[current_token_idx].dep == dep_rel:
                focused_token_indices.add(nodes[nodes[current_token_idx].governor].idx)
            child_nodes = [nodes[i] for i in range(len(nodes)) if nodes[i].governor==current_token_idx]
            focused_token_indices.update([child_node.idx for child_node in child_nodes if child_node.dep == dep_rel])
        return focused_token_indices

    def next_compound_token_idx(self, current_token_idx, nodes):
        compound_child_nodes = [nodes[i] for i in range(len(nodes)) if nodes[i].governor == current_token_idx and nodes[i].dep.startswith('compound')]
        
        if len(compound_child_nodes) > 0: return compound_child_nodes[0].idx
        return None
    
    def compound(self, new_targets, indices_for_new_targets, nodes):
        to_be_deleted, to_be_added = set(), set()
        for target_idx in indices_for_new_targets:
            
            compound_token_indices = list()
            focused_token_idx = target_idx
            while True:
                focused_token_idx = self.next_compound_token_idx(focused_token_idx, nodes)
                if focused_token_idx is None or focused_token_idx in compound_token_indices: break
                compound_token_indices.append(focused_token_idx)
            compound_token_indices.append(target_idx)

            if len(compound_token_indices) > 1:
                to_be_deleted.add(nodes[target_idx].token)
                to_be_added.add(' '.join([nodes[i].token for i in compound_token_indices]))
        for item in to_be_deleted:
            new_targets.remove(item)
        for item in to_be_added:
            new_targets.add(item)
    
    def extract_targets_using_pattern(self, token2indices, nodes, opinion_words, dep_rels):
        focused_token_indices = set([item for sublist in [token2indices[token] for token in opinion_words] for item in sublist])
        for i in range(len(dep_rels)):
            focused_token_indices = self.next_focused_token_indices(focused_token_indices, nodes, dep_rels[i])
        
        new_targets = set([nodes[i].token for i in focused_token_indices])
        self.compound(new_targets, focused_token_indices, nodes)
        return new_targets