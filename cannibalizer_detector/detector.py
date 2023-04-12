from .scraper import Scraper, getngrams, stemmer, stop_words
from .console_auth import Authenticator, progressbar
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import plotly.express as px



class Detector:
    """ A class to perform all steps of generating keyword cannibalization matrix. 

    """
    def __init__(self):
        self.tfidf_vectorizer = None
        self.manual_json = None
        self.console_json = None
        self.scraper = Scraper()
        self.queries = None
        self.urls = None
        self.scrap_dict = {}


    def load(self, manual_json=None, console_json=None, **kwargs): 
        """ Loads a Detector object with data manually or with credentials for automatic retreival. 

        This method loads the Detector object with the data to perform keyword cannibalization detection. 
        The manual insertion requires the user to know the prominent search keywords while the automatic method,
        requires the user to input the credentials of Google Console API. 

        Parameters
        ----------
        manual_json : dict   
            A dictionary that includes the required data for manual insertion which has the following schema  
            
            - 'query' as a key and a list of search queries as a value.
            - 'urls' as a key and a list of urls as a value.
        console_json : dict

            A dictionary that includes the required data for Google Console API which has the following schema:
            - 'api_name' as a key and the api name as a value.
            - 'api_version' as a key and the api version as a value.
            - 'client_secrets_path' as a key and the path to Google Console Json file as a value.
            - 'site' as a key and the site url as a value. 
        """
        if manual_json is not None:
            self.manual_json = manual_json 
            self.queries = manual_json['queries']
            self.urls = manual_json['urls']

        elif console_json is not None:
            self.console_json = console_json
            console_auth = Authenticator(
                                        api_name            = console_json['api_name'],
                                        api_version         = console_json['api_version'],
                                        client_secrets_path = console_json['client_secrets_path'],
                                        site                = console_json['site'])
            
            df_console = console_auth.retrieve_data()
            self.queries = df_console.iloc[:, 'queries']
            self.urls = df_console.iloc[:, 'ulrs']
        else:
            raise Exception('The detector must be loaded with input data manually or via Google Console API.')


    def scrape(self, url):
        """ Scrapes a given url by using Scrapper().

        Parameters
        ----------
        url : str   
            A string of the url to be scraped.   
            
        Returns
        -------
        self.scraper.scraped_text : str
            the Scrapper object scrapped text. 
        """
        self.scraper.scan(url)
        self.scraper.process_scrap()
        return self.scraper.scraped_text


    def generate_ngrams(self, corpus):
        """ Output a corpus with its generated bi-grams and tri-grams.

        Parameters
        ----------
        corpus : str   
            A string of the text which bi-grams and tri-grams are added.   
        
        Returns
        -------
        ngrams_corpus : str
            the Scrapper object scrapped text. 
        """
        # Bi-grams 
        bigrams = getngrams(corpus.split(' '), 2)
        # Tri-grams
        trigrams = getngrams(corpus.split(' '), 3)
        # Combining ngrams' lists
        ngrams_corpus = ' '.join(corpus.split(' ') + bigrams + trigrams)
        return ngrams_corpus


    def process_query(self, query_text):
        """ Processes a string of search query to a list of stemmed tokens.

        Parameters
        ----------
        query_text : str   
            A string of the search query to be processed.   
        
        Returns
        -------
        query_list : str
            A list of stemmed tokens. 
        """
        query_list = [word for word in query_text.split(' ') if word not in stop_words]
        # query_list = [word for word in query_list if len(phrase) !=0] 
        query_list = [stemmer.stem(word) for word in query_list]
        return query_list


    def create_tfidf_vectorizer(self, corpus_list):
        """ Instantiate and fits an object of sklearn.feature_extraction.text.TfidfVectorizer.

        Parameters
        ----------
        corpus_list : list   
            A list of string corpora each is scraped from a distinct url.   
        """
        self.tfidf_vectorizer = TfidfVectorizer()
        self.tfidf_vectorizer.fit(corpus_list)


    def analyze(self):
        """ Performs the steps needed for generating the keyword cannibalization matrix.

        This method is called after successfully calling the :py:meth:`~cannibalizer_detector.detector.Detector.load()`.
        The method creates an attribute of Detector class called similarity_matrix which is the final output of the 
        detection process. 
        """

        # Scrapping urls
        self.scrap_dict = {} 
        scrap_fails = []
        for i in progressbar(range(len(self.urls)), "Scrapping urls: ", 40):
            try:
                self.scrap_dict[self.urls[i]] = self.scrape(self.urls[i])
            except:
                scrap_fails.append(self.urls[i])
        print(f'Scraper failed to scrape {len(scrap_fails)}.')
        
        # Processing corpora and generating ngrams
        self.corpus_dict = {}
        for url in self.urls:
            if url not in scrap_fails:
                self.corpus_dict[url] = self.generate_ngrams(self.scrap_dict[url])
        
        # Processing queries
        self.query_dict = {}
        for query in self.queries:
            processed_query = self.process_query(query)
            self.query_dict[query] = self.generate_ngrams(' '.join(processed_query))

        # TF-IDF Vectorizer
        self.create_tfidf_vectorizer(list(self.corpus_dict.values()))

        # Obtaining queries' and urls' TF-IDF Matrices
        # Queries' matrices
        self.query_matrix = self.tfidf_vectorizer.transform(list(self.query_dict.values())).toarray()
        # urls matrices
        self.urls_matrix  = self.tfidf_vectorizer.transform(list(self.corpus_dict.values())).toarray()

        # Obtaining similarity matrix 
        self.similarity_matrix = cosine_similarity(self.urls_matrix, self.query_matrix)


    def visualize_matrix(self, normalize=True):
        """ Creates a Heatmap matrix with x-axis and y-axis representing queries and urls, respectively.

        Parameters
        ----------
        normalize : bool, default to True   
            A list of string corpora each is scraped from a distinct url.

        Returns
        -------
        fig : plotly.graph_objs._figure.Figure
            An interactive Plotly Heatmap Matrix.   
        """
        queries = list(self.query_dict.keys())
        urls = list(self.corpus_dict.keys())

        if normalize:
            similarity_matrix = self.similarity_matrix/(self.similarity_matrix.max(axis=0) + np.spacing(0))
            title = 'Normalized Cosine Similarity'
        else:
            similarity_matrix = self.similarity_matrix
            title = 'Cosine Similarity'
        fig = px.imshow(
                img= similarity_matrix,
                color_continuous_scale='OrRd',
                labels=dict(x="Search Queries", y="URLs", color=title),
                x = queries,
                y = ['URL ' + str(num+1) for num in range(len(urls))]
               )
        
        # Printing urls separately for figure visibility
        for c1, c2 in zip(range(len(urls)), urls):
            print("URL %-9s %s" % (c1+1, c2))

        fig.update_xaxes(side="top")
        return fig


