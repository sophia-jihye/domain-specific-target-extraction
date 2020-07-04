import time, stanfordnlp
from collections import defaultdict
from config import parameters
import pandas as pd
from DependencyGraphHandler import DependencyGraphHandler
from tqdm import tqdm
tqdm.pandas()

data_filepath = parameters.data_filepath
output_time_txt_filepath = parameters.output_time_txt_filepath
lexicon_filepath = parameters.lexicon_filepath
output_pattern_csv_filepath = parameters.output_pattern_csv_filepath
output_error_csv_filepath = parameters.output_error_csv_filepath

def process_targets(content, targets):
    processed_targets = []
    for target in targets:
        for token in content.split():
            if target in token: processed_targets.append(token)
    return list(set(processed_targets))

opinion_word_lexicon = [item for sublist in pd.read_json(lexicon_filepath).values for item in sublist]
def match_opinion_words(content):
    opinion_words = []
    for opinion in opinion_word_lexicon:
        for token in content.split():
            if token == opinion: opinion_words.append(token)
    return list(set(opinion_words))

nlp = stanfordnlp.Pipeline()
def extract_pattern(df, pattern_counter, err_list, dependency_handler):
    cnt = 0
    for _, row in df.iterrows():    
        document = row['content']
        doc = nlp(document)
        for sentence_from_doc in doc.sentences:
            o_t = [(o,t) for o in row['opinion_words'] for t in row['targets']]
            for o_word,t_word in o_t:
                flattened_string = ''.join([sentence_from_doc.words[i].text for i in range(len(sentence_from_doc.words))])
                if o_word not in flattened_string or t_word not in flattened_string:
                    continue

                try: pattern_counter['-'.join([dep_rel for token, pos, dep_rel in dependency_handler.get_pattern(sentence_from_doc, o_word, t_word) if dep_rel != 'root'])] += 1
                except: 
                    err_list.append([row['content'], o_word, t_word, row['opinion_words'], row['target']])
                if cnt % 100 == 0: print('[%dth] Extracting patterns..' % (cnt))
                cnt += 1

def save_results(pattern_counter, err_list):
    pattern_list = [tup for tup in pattern_counter.items()]
    pattern_df = pd.DataFrame(pattern_list, columns =['pattern', 'count'])  
    filepath = output_pattern_csv_filepath % len(pattern_df)
    pattern_df.to_csv(filepath, index = False, encoding='utf-8-sig')
    print('Created %s' % filepath)
    
    err_df = pd.DataFrame(err_list, columns =['content', 'current_opinion_word', 'current_target_word', 'opinion_words', 'targets'])  
    filepath = output_error_csv_filepath % len(err_df)
    err_df.to_csv(filepath, index = False, encoding='utf-8-sig')
    print('Created %s' % filepath)
                    
def main():
    df = pd.read_json(data_filepath)
    df['targets'] = df.apply(lambda x: process_targets(x['content'], x['target']), axis=1) 
    df['opinion_words'] = df.progress_apply(lambda x: match_opinion_words(x['content']), axis=1)
    
    dependency_handler = DependencyGraphHandler()
    pattern_counter, err_list = defaultdict(int), list()
    extract_pattern(df, pattern_counter, err_list, dependency_handler)
    save_results(pattern_counter, err_list)
    
def elapsed_time(start):
    end = time.time()
    elapsed_time = end - start
    elapsed_time_txt = time.strftime("%H:%M:%S", time.gmtime(elapsed_time))
    text_file = open(output_time_txt_filepath, "w", encoding='utf-8')
    content = 'Start: %s, End: %s => Elapsed time: %s\nCreated %s' % (time.strftime("%H:%M:%S", time.gmtime(start)), time.strftime("%H:%M:%S", time.gmtime(end)), elapsed_time_txt, output_time_txt_filepath)
    text_file.write(content)
    text_file.close()
    print('Created %s' % output_time_txt_filepath)
    
if __name__ == '__main__':
    start = time.time()
    main()
    elapsed_time(start)