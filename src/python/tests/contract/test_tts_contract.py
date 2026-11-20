"""Contract tests for the TextToSpeech port."""

from jarvis.fakes.tts import FakeTextToSpeech
from jarvis.ports.tts import TextToSpeech


def test_fake_tts_implements_port() -> None:
    tts: TextToSpeech = FakeTextToSpeech()
    assert isinstance(tts, TextToSpeech)


def test_speak_records_text() -> None:
    tts = FakeTextToSpeech()
    tts.speak("Hello world")
    assert tts.spoken == ["Hello world"]


def test_stop_sets_stopped() -> None:
    tts = FakeTextToSpeech()
    tts.stop()
    assert tts.stopped is True
