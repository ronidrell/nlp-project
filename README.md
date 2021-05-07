# Лемматизация слов якутского языка с помощью аггломеративной кластеризации

## Датасет
Датасет для обучения модели fasttext был взят из якутской Википедии и новостных источников.
Тестовые данные были написаны вручную и имеют вид словоформа-лемма.

Использованные данные находятся в папке data

## Дополнительные требования

Дополнительные библиотеки можно установить через:

`pip install -r requirements.txt`

## Обучение модели fasttext

`git clone https://github.com/facebookresearch/fastText.git`

`% cd fastText`

`make`

`./fasttext cbow -input /content/drive/MyDrive/ddata/korpus3_isprav.txt -output /content/drive/MyDrive/nlp/model -epoch 10 -dim 100`

## Кластеризация

Основной код: 

`python nlp_project.py`

Код для тестовой кластеризации: 

`python test_clustering.py`

## Литература

Rosa R., Žabokrtský Z. Unsupervised Lemmatization as Embeddings-Based Word Clustering //arXiv preprint arXiv:1908.08528. – 2019.
