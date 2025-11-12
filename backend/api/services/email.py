from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string


def send_translation_email(to_email, source_text, source_lang, target_lang, translated_text):
    subject = 'Ваш переклад готовий!'

    # Звичайний текст
    text_content = f"""
    Переклад з {source_lang} на {target_lang}:

    Оригінал:
    {source_text}

    Переклад:
    {translated_text}
    """

    # HTML версія (плюсом)
    # html_content = render_to_string('emails/translation_result.html', {
    #     'source_text': source_text,
    #     'translated_text': translated_text,
    #     'source_lang': source_lang,
    #     'target_lang': target_lang
    # })

    email = EmailMultiAlternatives(subject, text_content, to=[to_email])
    # email.attach_alternative(html_content, "text/html")
    email.send()
