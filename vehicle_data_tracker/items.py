# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class Vehicle(scrapy.Item):
    """
    Vehicle scrapy item.

    Fields:
        - year
        - make
        - model
        - trim
        - msrp
    """
    year = scrapy.Field()
    make = scrapy.Field()
    model = scrapy.Field()
    trim = scrapy.Field()
    msrp = scrapy.Field()
