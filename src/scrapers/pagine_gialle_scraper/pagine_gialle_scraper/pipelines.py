# src/scrapers/pagine_gialle_scraper/pipelines.py
from itemadapter import ItemAdapter

class PagineGiallePipeline:
    def open_spider(self, spider):
        # Eventuale inizializzazione (es. connessione a DB)
        pass

    def process_item(self, item, spider):
        # Qui eventuale validazione / trasformazione
        return item

    def close_spider(self, spider):
        # Chiusura risorse
        pass