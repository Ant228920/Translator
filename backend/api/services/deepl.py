import deepl
from django.conf import settings
from ..models import Translation, LANGUAGE_CHOICES
from django.utils import timezone


def translate_and_save(user, source_text, source_lang, target_lang, payment=None):
    deepl_lang_map = {
        'en': 'EN',
        'uk': 'UK',
        'de': 'DE',
        'fr': 'FR',
        'pl': 'PL'
    }

    try:
        target_deepl_lang = deepl_lang_map[target_lang.lower()]
        source_deepl_lang = deepl_lang_map.get(source_lang.lower(), None)

        translator = deepl.Translator(settings.DEEPL_API_KEY)
        result = translator.translate_text(
            source_text,
            target_lang=target_deepl_lang,
            source_lang=source_deepl_lang
        )

        translation = Translation.objects.create(
            user=user,
            payment=payment,
            source_text=source_text,
            translated_text=result.text,
            source_lang=source_lang,
            target_lang=target_lang,
            created_at=timezone.now()
        )

        return translation

    except Exception as e:
        print(f"Translation error: {e}")
        translation = Translation.objects.create(
            user=user,
            payment=payment,
            source_text=source_text,
            translated_text=f"[Помилка перекладу: {str(e)}]",
            source_lang=source_lang,
            target_lang=target_lang,
            created_at=timezone.now()
        )
        return translation