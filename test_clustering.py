import pickle
import fasttext
from pyjarowinkler import distance
from numpy import inner
from numpy.linalg import norm
import unidecode
from collections import defaultdict
import pandas as pd
from sklearn.metrics import homogeneity_completeness_v_measure

clustering = pickle.load(open("/content/drive/MyDrive/nlp/aggclust2.pickle", 'rb'))

embedding = fasttext.load_model("/content/drive/MyDrive/nlp/model.bin")

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
 
def homogeneity(clustering):
    golden = list()
    predictions = list()
    lemmatization_corrects = 0
    found_clusters = dict()  # caching
    lemma2clusters2forms = defaultdict(lambda: defaultdict(set))

    for form, lemma in test_data:
        golden.append(lemma)
        if form in clustering:
            cluster = clustering[form]
        else:
            if form not in found_clusters:
                found_clusters[form] = find_cluster_for_form(form, clustering)
            cluster = found_clusters[form]
        if lemma in clustering:
            lemmacluster = clustering[lemma]
        else:
            if lemma not in found_clusters:
                found_clusters[lemma] = find_cluster_for_form(lemma, clustering)
            lemmacluster = found_clusters[lemma]

        predictions.append(cluster)
        lemma2clusters2forms[lemma][cluster].add(form)
        if cluster == lemmacluster:
            lemmatization_corrects += 1

    hcv = homogeneity_completeness_v_measure(golden, predictions)
    acc = lemmatization_corrects/len(golden)
    return (*hcv, acc)


test = pd.read_csv("data/allforms.csv")

test_data = list()
for i in range(len(df['wordform'])):
  test_data.append((df['wordform'][i], df['lemma'][i]))

hcva = homogeneity(clustering)
print('Homogeneity', 'completenss', 'vmeasure', 'accuracy', sep='\t')
print(*hcva, sep='\t')

