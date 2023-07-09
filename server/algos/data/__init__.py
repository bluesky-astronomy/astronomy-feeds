from .astronomy import text

def pad_strings(list_of_strings):
    list_of_strings = list_of_strings + [x + "s" for x in list_of_strings]
    return [" " + x + " " for x in list_of_strings]

astronomy_terms = pad_strings(text)