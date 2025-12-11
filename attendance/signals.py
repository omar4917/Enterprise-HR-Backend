from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import (
    Employee,
    VoiceSetting,
    TextMessageSetting,
    ContextSetting,
    VoiceNameOverride,
    VoicePhraseOverride,
    EmployeeVoicePreference,
)
from .utils.sync_helpers import trigger_database_sync_async


@receiver(post_save, sender=Employee)
def employee_saved(sender, instance, **kwargs):
    if kwargs.get("raw"):
        return
    trigger_database_sync_async()


@receiver(post_delete, sender=Employee)
def employee_deleted(sender, instance, **kwargs):
    trigger_database_sync_async()


def _trigger_settings_sync(raw_flag):
    if raw_flag:
        return
    trigger_database_sync_async()


@receiver(post_save, sender=VoiceSetting)
def voice_setting_saved(sender, instance, **kwargs):
    _trigger_settings_sync(kwargs.get("raw"))


@receiver(post_save, sender=TextMessageSetting)
def text_setting_saved(sender, instance, **kwargs):
    _trigger_settings_sync(kwargs.get("raw"))


@receiver(post_save, sender=ContextSetting)
def context_setting_saved(sender, instance, **kwargs):
    _trigger_settings_sync(kwargs.get("raw"))


@receiver(post_save, sender=VoiceNameOverride)
def voice_name_override_saved(sender, instance, **kwargs):
    _trigger_settings_sync(kwargs.get("raw"))


@receiver(post_save, sender=VoicePhraseOverride)
def voice_phrase_override_saved(sender, instance, **kwargs):
    _trigger_settings_sync(kwargs.get("raw"))


@receiver(post_save, sender=EmployeeVoicePreference)
def employee_voice_preference_saved(sender, instance, **kwargs):
    _trigger_settings_sync(kwargs.get("raw"))


@receiver(post_delete, sender=VoiceNameOverride)
def voice_name_override_deleted(sender, instance, **kwargs):
    trigger_database_sync_async()


@receiver(post_delete, sender=VoicePhraseOverride)
def voice_phrase_override_deleted(sender, instance, **kwargs):
    trigger_database_sync_async()


@receiver(post_delete, sender=EmployeeVoicePreference)
def employee_voice_preference_deleted(sender, instance, **kwargs):
    trigger_database_sync_async()
