# src/scrapers/pagine_gialle_scraper/items.py
import scrapy

class PagineGialleItem(scrapy.Item):
    nome = scrapy.Field()
    indirizzo = scrapy.Field()
    citta = scrapy.Field()
    provincia = scrapy.Field()
    cap = scrapy.Field()
    telefono = scrapy.Field()
    email = scrapy.Field()
    sito_web = scrapy.Field()
    categoria = scrapy.Field()
    descrizione = scrapy.Field()
    latitudine = scrapy.Field()
    longitudine = scrapy.Field()
    region = scrapy.Field()
    paese = scrapy.Field()
    category = scrapy.Field()
    pagina = scrapy.Field()