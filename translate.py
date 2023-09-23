from deep_translator import GoogleTranslator

in_lang = "en"
out_lang = "ru"


def translate_text(text):
    if in_lang == out_lang:
        return text

    translated = GoogleTranslator(source=in_lang, target=out_lang).translate(text=text)
    if translated is None:
        return text
    return translated
