import fasttext
import functools
import argparse
import sys
from collections import defaultdict, Counter
from sortedcollections import ValueSortedDict
from collections import OrderedDict

from sklearn.metrics import homogeneity_completeness_v_measure

from numpy import inner
from numpy.linalg import norm

import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.model_selection import cross_val_score
from sklearn import svm
from sklearn import linear_model
from sklearn.neural_network import MLPClassifier
from ast import literal_eval as make_tuple
from sklearn.metrics import confusion_matrix
import itertools

from sklearn.cluster import AgglomerativeClustering

from pyjarowinkler import distance

import unidecode

import matplotlib
import matplotlib.pyplot as plt

import logging

import numpy as np

from matplotlib import pyplot as plt
from scipy.cluster.hierarchy import dendrogram
from sklearn.cluster import AgglomerativeClustering

import pickle

import pandas as pd

# OOV_EMB_SIM = 0.9

def plot_dendrogram(model, **kwargs):


    # Children of hierarchical clustering
    children = model.children_

    # Distances between each pair of children
    # Since we don't have this information, we can use a uniform one for plotting
    distance = np.arange(children.shape[0])

    # The number of observations contained in each cluster level
    no_of_observations = np.arange(2, children.shape[0]+2)

    # Create linkage matrix and then plot the dendrogram
    linkage_matrix = np.column_stack([children, distance, no_of_observations]).astype(float)

    # Plot the corresponding dendrogram
    dendrogram(linkage_matrix, **kwargs)

    plt.xticks(rotation=90)
    plt.margins(0.2)
    plt.subplots_adjust(bottom=0.2)

def devow(form):
    '''
    Удаление не начальных гласных
    Используется для вычисления расстояния между словами, делает меру мягче (уделяет меньше внимания различиям, которые имеют меньше влияния)
    '''
    uform = unidecode.unidecode(form)

    # keep first letter
    dform = uform[1:]
    # remove vowels, do not presuppose lowercasing
    dform = dform.replace("у", "")
    dform = dform.replace("ё", "")
    dform = dform.replace("е", "")
    dform = dform.replace("ы", "")
    dform = dform.replace("а", "")
    dform = dform.replace("о", "")
    dform = dform.replace("э", "")
    dform = dform.replace("я", "")
    dform = dform.replace("и", "")
    dform = dform.replace("ю", "")
    dform = dform.replace("ө", "")
    dform = dform.replace("ү", "")
    
    return uform[:1] + dform

def embsim(word, otherword):
    # сходство между эмбеддингами
    emb1 = embedding[word]
    emb2 = embedding[otherword]
    sim = inner(emb1, emb2) / (norm(emb1) * norm(emb2))
    assert sim >= -1.0001 and sim <= 1.0001, "Cos sim must be between -1 and 1"
    sim = (sim + 1) / 2
    return sim

def jw_safe(srcword, tgtword):
    # расстояние Джаро-винклера
    if srcword == '' or tgtword == '':
        # 1 if both empty
        # 0.5 if one is length 1
        # 0.33 if one is length 2
        # ...
        return 1/(len(srcword)+len(tgtword)+1)
    elif srcword == tgtword:
        return 1
    else:
        return distance.get_jaro_distance(srcword, tgtword)

def jwsim(word, otherword):
    # сходство Джаро-Винклера
    sim = jw_safe(word, otherword)
    uword = devow(word)
    uotherword = devow(otherword)
    usim = jw_safe(uword, uotherword)    
    sim = (sim+usim)/2
    assert sim >= 0 and sim <= 1, "JW sim must be between 0 and 1"
    return sim

length = 0.5

def lensim(word, otherword):
    global lenght
    return 1 / (1 + length * abs(len(word) - len(otherword)) )

def similarity(word, otherword, similarity):
    if similarity == 'jw':
        return jwsim(word, otherword)
    elif similarity == 'jwxcos': # расстояние, предложенное авторами в статье
        return jwsim(word, otherword) * embsim(word, otherword)
    elif similarity == 'jwxcosxlen':
        return jwsim(word, otherword) * embsim(word, otherword) * lensim(word, otherword);
    elif similarity == 'len':
        return lensim(word, otherword);
    else:
        # cos
        return embsim(word, otherword)

remerge = 2

def get_stem(form, remerging=False):
  # получаем стемму слова (в нашем случае первые 2 буквы)
  remerge = 2
  stem = form[:int(remerge)]
  return stem


embedding = fasttext.load_model("model.bin")
forms_stemmed = defaultdict(set) # словарь стемма - словоформа
form_freq_rank = dict() # частота 
for i in range(len(embedding.words)):
  stem = get_stem(embedding.words[i])
  forms_stemmed[stem].add(embedding.words[i])
  form_freq_rank[embedding.words[i]] = i


test_data = list() # список всех словоформ
df = pd.read_csv("allforms.csv")

for i in range(len(df['wordform'])):
  test_data.append((df['wordform'][i], df['lemma'][i]))


def get_dist(form1, form2, sim):
    # similarity to distance
    return 1-similarity(form1, form2, sim)

def linkage(cluster1, cluster2, D, measure):
    # критерий связи
    linkages = list()
    for node1 in cluster1:
        for node2 in cluster2:
            linkages.append(D[node1, node2])
    # min avg max
    if measure == 'average':
        return sum(linkages)/len(linkages)
    elif measure == 'single':
        return min(linkages)
    elif measure == 'complete':
        return max(linkages)
    else:
        assert False

def cl(stem, cluster):
    return stem + '___' + str(cluster)

threshold = 0.5

def aggclust(forms_stemmed, measure):
    # form -> cluster
    result = dict()
    global threshold
    for stem in forms_stemmed:
        # vocabulary
        index2word = list(forms_stemmed[stem])
        I = len(index2word)
        
        logging.debug(stem)
        logging.debug(I)
        logging.debug(index2word)
        
        if I == 1:
            result[index2word[0]] = cl(stem, 0)
            continue

        D = np.empty((I, I)) # матрица расстояний
        for i1 in range(I):
            for i2 in range(I):
                D[i1,i2] = get_dist(index2word[i1], index2word[i2], 'jwxcos')
        clustering = AgglomerativeClustering(affinity='precomputed',
                linkage = measure, n_clusters=1)
        clustering.fit(D)

        # default: each has own cluster
        clusters = list(range(I))
        nodes = [[i] for i in range(I)]
        for merge in clustering.children_:
            # check stopping criterion
            if threshold < linkage(nodes[merge[0]], nodes[merge[1]], D, 'average'):
                break
            # perform the merge
            nodes.append(nodes[merge[0]] + nodes[merge[1]])
            # reassign words to new cluster ID
            for i in nodes[-1]:
                clusters[i] = len(nodes) - 1
        for i, cluster in enumerate(clusters):
            result[index2word[i]] = cl(stem, cluster)
    return result

def writeout_clusters(clustering):
    # запись кластеров в файл
    cluster2forms = defaultdict(list)
    for form, cluster in clustering.items():
        cluster2forms[cluster].append(form)
    f = open("3/clusters.txt", "w", encoding='utf-8')
    for cluster in sorted(cluster2forms.keys()):
        # print('CLUSTER', cluster)
        f.write('CLUSTER: ' + str(cluster) + '\n')
        for form in cluster2forms[cluster]:
            # print(form)
            f.write(str(form) + '\n')
        # print()
        f.write('\n')
    sys.stdout.flush()
    f.close()

clusterset = set()

def rename_clusters(clustering):
    # переименовывание кластеров
    cluster2forms = defaultdict(list)
    for form, cluster in clustering.items():
        cluster2forms[cluster].append(form)

    cluster2newname = dict()
    for cluster, forms in cluster2forms.items():
        form2len = dict()
        form2rank = dict()
        for form in forms:
            # assert form in form_freq_rank
            # form2rank[form] = form_freq_rank[form]
            form2len[form] = len(form)
        # most_frequent_form = min(form2rank, key=form2rank.get)
        # cluster2newname[cluster] = most_frequent_form
        # clusterset.add(most_frequent_form)
        min_len_form = min(form2len, key=form2len.get)
        cluster2newname[cluster] = min_len_form
        clusterset.add(min_len_form)

    new_clustering = dict()
    for form, cluster in clustering.items():
        new_clustering[form] = cluster2newname[cluster]

    return new_clustering

# now 1 nearest neighbour wordform;
# other option is nearest cluster in avg linkage
# (probably similar result but not necesarily)
def find_cluster_for_form(form, clustering, oov):
    # поиск кластера для словоформы
    global threshold
    stem = get_stem(form)
    cluster = form  # backoff: new cluster
    if oov == "guess" and stem in forms_stemmed:
        dists = dict()
        for otherform in forms_stemmed[stem]:
            dists[otherform] = get_dist(form, otherform, 'jwxcos')
        nearest_form = min(dists, key=dists.get)
        if dists[nearest_form] < threshold:
            cluster = clustering[nearest_form]
            # else leave the default, i.e. a separate new cluster
    return cluster

def homogeneity(clustering, writeout=False):
    golden = list()
    predictions = list()
    lemmatization_corrects = 0
    found_clusters = dict()  # caching
    lemma2clusters2forms = defaultdict(lambda: defaultdict(set))

    f = open('3/good.txt', 'w', encoding='utf-8')
    for form, lemma in test_data:
        golden.append(lemma)
        if form in clustering:
            cluster = clustering[form]
        else:
            if form not in found_clusters:
                found_clusters[form] = find_cluster_for_form(form, clustering, 'guess')
            cluster = found_clusters[form]
        if lemma in clustering:
            lemmacluster = clustering[lemma]
        else:
            if lemma not in found_clusters:
                found_clusters[lemma] = find_cluster_for_form(lemma, clustering, 'guess')
            lemmacluster = found_clusters[lemma]

        predictions.append(cluster)
        lemma2clusters2forms[lemma][cluster].add(form)
        if cluster == lemmacluster:
            lemmatization_corrects += 1
        if writeout:
            oov = 'OOVform: ' if form in found_clusters else ''
            lemmaoov = 'OOVlemma ' if lemma in found_clusters else ''
            dist = get_dist(form, lemma, 'jwxcos')
            good = 'GOOD' if cluster == lemmacluster else 'BAD'
            # print(oov, form, '->', cluster, good,
            #         '{:.4f}'.format(dist), lemmaoov, lemma, '->', lemmacluster)
            f.write(str(oov) + str(form) + ' -> ' + str(cluster) + ' ' + str(good) + ' ' +
                    str('{:.4f}'.format(dist)) + ' ' + str(lemmaoov) + str(lemma) + ' -> ' + str(lemmacluster) + '\n')
    f.close()
    if writeout:
        f = open('3/lemma.txt', 'w', encoding='utf-8')
        # print('PER LEMMA WRITEOUT')
        f.write('PER LEMMA WRITEOUT\n')
        f.write('stem\tcluster\tforms\n')
        for lemma in lemma2clusters2forms:
            # print('LEMMA:', lemma)
            f.write('LEMMA: ' + str(lemma) + '\n')
            for cluster in lemma2clusters2forms[lemma]:
                # print(get_stem(cluster), cluster, ':', lemma2clusters2forms[lemma][cluster])
                f.write(str(get_stem(cluster)) + ' ' + str(cluster) + ': ' + str(lemma2clusters2forms[lemma][cluster]) + '\n')
            # print()
            f.write('\n')
        f.close()

    hcv = homogeneity_completeness_v_measure(golden, predictions)
    acc = lemmatization_corrects/len(golden)
    return (*hcv, acc)

def baseline_clustering(test_data, basetype):
    result = dict()
    for form, lemma in test_data:
        for word in (form, lemma):
            stem = get_stem(word)
            if basetype == 'formlemma':
                result[word] = cl(stem, word)
            elif basetype == 'stemlemma':
                result[word] = cl(stem, 0)
            elif basetype == 'upper':
                result[word] = cl(stem, lemma)
            elif basetype == 'stem5':
                result[word] = cl(stem, word[:5])
            logging.debug(basetype + ': ' + word + ' -> ' + result[word])
    return result

known = 0
unknown = 0
for form, _ in test_data:
    if form in embedding:
        known += 1
    else:
        unknown += 1
print('OOV rate:', unknown, '/', (known+unknown), '=',
        (unknown/(known+unknown)*100))

print('Type', 'homogeneity', 'completenss', 'vmeasure', 'accuracy', sep='\t')
for basetype in ('formlemma', 'stemlemma', 'stem5', 'upper'):
    clustering = baseline_clustering(test_data, basetype)
    hcva = homogeneity(clustering)
    print(basetype, *hcva, sep='\t')

clustering = aggclust(forms_stemmed, 'average')

logging.info('Rename clusters')
renamed_clustering = rename_clusters(clustering)

writeout_clusters(renamed_clustering)

hcva = homogeneity(renamed_clustering, writeout=True)
print('Homogeneity', 'completenss', 'vmeasure', 'accuracy', sep='\t')
print(*hcva, sep='\t')

with open('3/aggclust2.pickle', 'wb') as f:
    pickle.dump(renamed_clustering, f)
