"""
Static support functions and global variables for use in any of the web crawlers and the app.

"""

# from items import Vehicle

STANDARD_FIELDS = ['year', 'make', 'model', 'trim', 'msrp']

MAKES_LIST = {
    'name_list': ['Acura', 'Audi', 'BMW', 'Buick', 'Cadillac', 'Chevrolet', 'Stellantis (FCA)', 'Chrysler', 'Ford',
                  'Genesis', 'GMC', 'Honda', 'Hyundai', 'Nissan Group (includes Infiniti)', 'Jaguar/Land Rover',
                  'Kia', 'Lexus', 'Lincoln', 'Mazda', 'Mercedes-Benz', 'Mini', 'Mitsubishi',
                  'Porsche', 'Subaru', 'Tesla', 'Toyota', 'Volkswagen', 'Volvo'],

    'available': {'Acura': 'acura.py', 'Audi': 'audi.py', 'BMW': 'bmw.py', 'Buick': 'buick.py',
                  'Cadillac': 'cadillac.py', 'Chevrolet': 'chevrolet.py',  # 'Chrysler': 'chrysler.py',
                  'Stellantis (FCA)': 'fca.py', 'Ford': 'ford.py', 'Genesis': 'genesis.py', 'GMC': 'gmc.py',
                  'Honda': 'honda.py', 'Hyundai': 'hyundai.py', 'Nissan Group (includes Infiniti)': 'nissan.py',
                  'Jaguar/Land Rover': 'tata.py', 'Kia': 'kia.py', 'Lexus': 'lexus.py',
                  'Lincoln': 'lincoln.py', 'Mazda': 'mazda.py', 'Mercedes-Benz': 'mercedes.py',
                  'Mini': 'mini.py', 'Mitsubishi': 'mitsubishi.py', 'Porsche': 'porsche.py',
                  'Subaru': 'subaru.py', 'Tesla': 'tesla.py', 'Toyota': 'toyota.py',
                  'Volkswagen': 'vw.py', 'Volvo': 'volvo.py'},

    'groups': {'fca': ('alfa romeo', 'chrysler', 'dodge', 'fiat', 'jeep', 'ram'),
               'nissan': ('nissan', 'infiniti'),
               'tata': ('jaguar', 'land rover')},

    'unavailable': []

}


def remove_html_tags(text: str):
    """
    Creates a copy of a string with any html tags removed.

    :param text: a string containing html tags
    :return: a new string with characters from <i>text</i> that weren't contained in html tags
    """
    hasTags = '<' in text
    strippedText = text.strip()

    while hasTags:
        start = strippedText.find('<')
        end = strippedText.find('>') + 1
        tag = strippedText[start:end]
        strippedText = strippedText.replace(tag, '')
        hasTags = '<' in strippedText
    return strippedText


# def check_duplicate_vehicles(v1: Vehicle, v2: Vehicle):
#     return v1['year'] == v2['year'] and v1['make'] == v2['make'] and v1['model'] == v2['model'] and \
#            v1['trim'] == v2['trim']# and v1['msrp'] == v2['msrp']
