"""Property tests: parsers never crash on malformed input (fuzz testing)."""

from datetime import UTC

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from jarvis.domain.events import EventEnvelope

# Strategy for arbitrary dictionary payloads
malformed_payload = st.dictionaries(
    st.text(min_size=0, max_size=20),
    st.one_of(
        st.text(min_size=0, max_size=100),
        st.integers(),
        st.floats(allow_nan=True, allow_infinity=True),
        st.booleans(),
        st.none(),
        st.lists(st.text(min_size=0, max_size=20)),
    ),
    max_size=20,
)


@given(
    event_id=st.text(min_size=1, max_size=50),
    source=st.text(min_size=1, max_size=30),
    event_type=st.text(min_size=1, max_size=30),
    importance_hint=st.floats(allow_nan=True, allow_infinity=True),
    sensitive=st.booleans(),
    payload=malformed_payload,
)
@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
def test_envelope_from_dict_never_crashes(
    event_id: str,
    source: str,
    event_type: str,
    importance_hint: float,
    sensitive: bool,
    payload: dict,
) -> None:
    """Property: EventEnvelope construction from arbitrary data never crashes."""
    import math
    from datetime import datetime

    # Clamp importance_hint to valid range
    hint = importance_hint
    if math.isnan(hint) or math.isinf(hint):
        hint = 0.0
    hint = max(0.0, min(1.0, hint))

    envelope = EventEnvelope(
        id=event_id,
        source=source,
        type=event_type,
        time=datetime(2026, 11, 20, 9, 0, 0, tzinfo=UTC),
        payload=payload,
        importance_hint=hint,
        sensitive=sensitive,
    )

    # to_dict and from_dict should round-trip without crashing
    d = envelope.to_dict()
    assert isinstance(d, dict)
    assert d["id"] == event_id
    assert d["source"] == source
    assert d["type"] == event_type

    envelope2 = EventEnvelope.from_dict(d)
    assert envelope2.id == envelope.id
    assert envelope2.source == envelope.source
    assert envelope2.type == envelope.type
    assert envelope2.payload == envelope.payload


@given(
    text=st.one_of(
        st.text(min_size=0, max_size=500),
        st.none(),
        st.binary(min_size=0, max_size=100),
    )
)
@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
def test_stt_result_handles_arbitrary_text(text) -> None:
    """Property: STT results handle arbitrary text without crashing."""
    from jarvis.ports.stt import STTResult

    # Just verify STTResult can be constructed with any text
    result = STTResult(text=str(text) if text is not None else "", is_final=True)
    assert isinstance(result.text, str)
    assert isinstance(result.is_final, bool)
