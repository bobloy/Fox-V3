"""
Default ChatterBot settings for Django.
"""
from django.conf import settings
from ... import constants


CHATTERBOT_SETTINGS = getattr(settings, 'CHATTERBOT', {})

CHATTERBOT_DEFAULTS = {
    'name': 'ChatterBot',
    'storage_adapter': 'chatter.source.storage.DjangoStorageAdapter',
    'input_adapter': 'chatter.source.input.VariableInputTypeAdapter',
    'output_adapter': 'chatter.source.output.OutputAdapter',
    'django_app_name': constants.DEFAULT_DJANGO_APP_NAME
}

CHATTERBOT = CHATTERBOT_DEFAULTS.copy()
CHATTERBOT.update(CHATTERBOT_SETTINGS)
