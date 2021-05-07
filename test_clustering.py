import pickle

clustering = pickle.load(open("/content/drive/MyDrive/nlp/aggclust2.pickle", 'rb'))

import fasttext

embedding = fasttext.load_model("/content/drive/MyDrive/nlp/model.bin")

from pyjarowinkler import distance
from numpy import inner
from numpy.linalg import norm

import unidecode

def devow(form):
    # implicit transliteration and deaccentization
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
    emb1 = embedding[word]
    emb2 = embedding[otherword]
    sim = inner(emb1, emb2) / (norm(emb1) * norm(emb2))
    assert sim >= -1.0001 and sim <= 1.0001, "Cos sim must be between -1 and 1"
    sim = (sim + 1) / 2
    return sim

def jw_safe(srcword, tgtword):
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
    # called distance but is actually similarity
    sim = jw_safe(word, otherword)
    uword = devow(word)
    uotherword = devow(otherword)
    usim = jw_safe(uword, uotherword)    
    sim = (sim+usim)/2
    assert sim >= 0 and sim <= 1, "JW sim must be between 0 and 1"
    return sim

def similarity(word, otherword):
  # jw x cos similarity
  return jwsim(word, otherword) * embsim(word, otherword)

def get_dist(form1, form2):
    # similarity to distance
    return 1-similarity(form1, form2)

def get_stem(form, remerging=False):
  remerge = 2
  stem = form[:int(remerge)]
  return stem

from collections import defaultdict

forms_stemmed = defaultdict(set)
for i in range(len(embedding.words)):
  stem = get_stem(embedding.words[i])
  forms_stemmed[stem].add(embedding.words[i])

threshold = 0.5

def find_cluster_for_form(form, clustering):
    stem = get_stem(form)
    cluster = form  # backoff: new cluster
    if stem in forms_stemmed:
      dists = dict()
      for otherform in forms_stemmed[stem]:
          dists[otherform] = get_dist(form, otherform)
      nearest_form = min(dists, key=dists.get)
      if dists[nearest_form] < threshold:
          cluster = clustering[nearest_form]
          # else leave the default, i.e. a separate new cluster
    return cluster

import pandas as pd

test = pd.read_csv("/content/drive/MyDrive/nlp/test.csv")

test_data = test['wordform'].values.tolist()

test_data_clusters = dict()
for form in test_data:
  test_data_clusters[form] = find_cluster_for_form(form, clustering)

def writeout_clusters(clustering):
    cluster2forms = defaultdict(list)
    for form, cluster in clustering.items():
        cluster2forms[cluster].append(form)
    for cluster in sorted(cluster2forms.keys()):
        print('CLUSTER', cluster)
        for form in cluster2forms[cluster]:
            print(form)
        print()

writeout_clusters(test_data_clusters)
