from django import template

register = template.Library()

@register.filter(name='audio_file_path')
def audio_file_path(user_id, filename="file.wav"):
    """
    Constructs an audio file path for a given user ID and filename.
    {{ user_id|audio_file_path:"specific_file" }}
    """
    return f"audio/{user_id}/{filename}.wav"