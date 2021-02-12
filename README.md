# nlp-project

Цель: сделать unsupervised лемматизатор слов якутского языка

План: изучить и попробовать различные методы лемматизации и выбрать из них наилучший.

Данные: тексты из новостных сайтов на якутском языке

1. Rosa R., Žabokrtský Z. Unsupervised Lemmatization as Embeddings-Based Word Clustering //arXiv preprint arXiv:1908.08528. – 2019.
Кластеризация слов. Различные словоформы одного слова группируются под одной меткой, где метка - это лемма. В статье не указывается как они будут выбирать лемму. Т.к. якутский язык является агглютинативным (к слову прикрепляются окончания), то можно будет выбрать самое короткое слово.

2. https://jamesgawley.github.io/Unsupervised-Lemmatization-Model/
Построили модель оценки частоты слов, затем построили лемматизатор,возвращающий все возможные варианты леммы с их вероятностями в соответствии с ее частотой в модели.

3. Chakrabarty A., Choudhury S. R., Garain U. IndiLem@ FIRE-MET-2014: An unsupervised lemmatizer for Indian languages //Proceedings of Forum for Information Retrieval and Evaluation (FIRE 2014). – 2014.
Используется посик по дереву с помощью словаря.
