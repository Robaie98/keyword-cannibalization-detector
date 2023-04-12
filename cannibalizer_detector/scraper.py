import re
from bs4 import BeautifulSoup
import bs4
import urllib3 
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer


# NLP utils
stop_words  = stopwords.words('english')
token_regex = re.compile(r"\w+(?:'\w+)?|[^\w\s]")
spaces_regex = re.compile(r'(?u)\\+[a-z]')
stemmer = PorterStemmer()


# NLP functions
def visible_tags(element:bs4.element.NavigableString):
    # Removes unwanted html tags and their content
    if element.parent.name in ['style', 'script', '[document]']:
        return False
    return True

def tokenize(text:str):
    # Tokenizes text and remove stop words
    return [word for word in token_regex.findall(text.lower()) if word not in stop_words]

def getngrams(token_list:list, n:int):
    # Obtains n-grams by moving concatenation of tokens in a list
    indices = range(len(token_list))
    max_index = max(indices)
    ngrams = [' '.join(token_list[i:min(i+n, max_index)]) for i in indices]
    ngrams = [ngram for ngram in ngrams if len(ngram.split(' '))== n]
    return ngrams



class Scraper:
    """ A class for scrapping webpages and extracting a corpus of text.  
    
    """
    def __init__(self):
        self.url = None
        self.url_soup = None
        self.url_tilte = None
        self.urld_description = None
        self.url_word_count = None
        self.scraped_text = None 
        

    def scan(self, url:str):
        """Checks the url format requirements and obtains an html file of the url.

        Parameters
        ----------
        url: str
            The url to the scraped webpage. 
        """
        self.url = url
        valid_prefixes = []

        # only allow http:// https:// and //
        for s in ['http://', 'https://', '//',]:
            valid_prefixes.append(self.url.startswith(s))
        if True not in valid_prefixes:
            self.warn(f'{self.url} does not appear to have a valid protocol.')
            return

        self.url = url
        http = urllib3.PoolManager()
        r = http.request('GET', url)
        self.url_soup = r


    def process_scrap(self): 
        """Processes the html content of the scrapped webpage to a corpus of stemmed tokens. 

        """
        # Removing comments to improve BeutifulSoup performance
        clean_html = re.sub(r'<!--.*?-->', r'', str(self.url_soup.data), flags=re.DOTALL)
        
        # Parsing html content
        soup = BeautifulSoup(clean_html.lower(), 'html.parser') 
        clean_text = soup.findAll(text=True)
        clean_text = [word for word in filter(visible_tags, clean_text)]
        clean_text = ' '.join([word.strip().lower() for word in clean_text])

        # Cleaning, stemming, and tokenization
        clean_text = re.sub(spaces_regex, '', clean_text)
        clean_text = [word for word in token_regex.findall(clean_text) if word not in stop_words]
        clean_text = [''.join(phrase) for phrase in clean_text if len(phrase) !=0] 
        clean_text = [stemmer.stem(word) for word in clean_text]
        self.scraped_text = ' '.join(clean_text)
