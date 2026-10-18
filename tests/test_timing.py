"""`duration`, `speed`, `loop` and `fps` all have to mean something exact."""

from __future__ import annotations

import pytest
from PIL import Image

from headpat_gif import petpet
from headpat_gif._compose import MIN_DELAY_MS
from support import frame_delays

CYCLE_MS = 150  # the overlay_gif fixture: 3 frames x 50ms


@pytest.mark.parametrize("duration", [0.2, 0.35, 0.5, 1.0, 2.0, 3.7])
def test_total_length_is_exactly_the_requested_duration(
    subject: Image.Image, overlay_gif: bytes, duration: float
) -> None:
    gif = petpet(subject, overlay_gif, duration=duration)

    assert gif.duration_ms == round(duration * 1000)
    assert sum(frame_delays(gif.to_bytes())) == gif.duration_ms


def test_without_a_duration_the_gif_is_exactly_one_cycle(
    subject: Image.Image, overlay_gif: bytes
) -> None:
    gif = petpet(subject, overlay_gif)

    assert gif.cycle_ms == CYCLE_MS
    assert gif.duration_ms == CYCLE_MS
    assert sum(frame_delays(gif.to_bytes())) == CYCLE_MS


@pytest.mark.parametrize(("speed", "expected"), [(2.0, 80), (4.0, 40), (0.5, 300), (1.0, 150)])
def test_speed_scales_the_cycle_not_the_total(
    subject: Image.Image, overlay_gif: bytes, speed: float, expected: int
) -> None:
    gif = petpet(subject, overlay_gif, duration=2.0, speed=speed)

    assert gif.cycle_ms == expected
    assert gif.duration_ms == 2000


def test_a_longer_duration_is_padded_with_one_resting_frame(
    subject: Image.Image, overlay_gif: bytes
) -> None:
    gif = petpet(subject, overlay_gif, duration=1.0, loop=False)
    delays = frame_delays(gif.to_bytes())

    assert sum(delays) == 1000
    assert delays[-1] == 1000 - CYCLE_MS
    assert len(delays) == 5  # 4 sampled cycle frames + the resting tail


def test_loop_is_on_by_default_and_keeps_petting(
    subject: Image.Image, overlay_gif: bytes
) -> None:
    gif = petpet(subject, overlay_gif, duration=1.0)
    delays = frame_delays(gif.to_bytes())

    assert sum(delays) == 1000
    # No long resting frame: every frame belongs to one of the repeated cycles.
    assert max(delays) <= 50
    assert len(delays) > 5


def test_looping_fits_a_whole_number_of_cycles_into_the_duration(
    subject: Image.Image, overlay_gif: bytes
) -> None:
    # 1000ms / 150ms per pat is 6.67 pats, so the cycle is stretched slightly to
    # fit six whole pats: the GIF then loops with no visible jump.
    gif = petpet(subject, overlay_gif, duration=1.0)
    delays = frame_delays(gif.to_bytes())

    assert sum(delays) == 1000
    # A whole number of pats, each sampled into four frames.
    assert len(delays) % 4 == 0
    assert len(delays) // 4 == 7  # 1000ms / 150ms rounds to seven pats
    # Every frame boundary lands on the 10ms grid a GIF delay is stored in.
    assert all(delay % 10 == 0 for delay in delays)


def test_loop_repeats_the_cycle_instead_of_resting(subject: Image.Image, overlay_gif: bytes) -> None:
    gif = petpet(subject, overlay_gif, duration=1.0, loop=True)
    delays = frame_delays(gif.to_bytes())

    assert sum(delays) == 1000
    assert max(delays) <= 50
    assert len(delays) > 5


def test_loop_is_ignored_without_a_duration(subject: Image.Image, overlay_gif: bytes) -> None:
    assert petpet(subject, overlay_gif, loop=True).duration_ms == CYCLE_MS


def test_a_duration_shorter_than_one_cycle_truncates_it(
    subject: Image.Image, overlay_gif: bytes
) -> None:
    gif = petpet(subject, overlay_gif, duration=0.1)

    assert gif.duration_ms == 100
    assert gif.cycle_ms == CYCLE_MS
    assert sum(frame_delays(gif.to_bytes())) == 100


@pytest.mark.parametrize("fps", [10, 25, 50])
def test_every_delay_stays_above_the_viewer_clamp(
    subject: Image.Image, overlay_gif: bytes, fps: int
) -> None:
    delays = frame_delays(petpet(subject, overlay_gif, duration=1.0, fps=fps).to_bytes())

    assert min(delays) >= MIN_DELAY_MS


def test_fps_controls_the_sampling_step(subject: Image.Image, overlay_gif: bytes) -> None:
    coarse = frame_delays(petpet(subject, overlay_gif, duration=1.0, fps=10).to_bytes())
    fine = frame_delays(petpet(subject, overlay_gif, duration=1.0, fps=50).to_bytes())

    assert fine.count(20) > coarse.count(20)
    assert len(fine) > len(coarse)


def test_a_single_frame_cycle_still_produces_a_valid_gif(
    subject: Image.Image, overlay_gif: bytes
) -> None:
    # speed high enough to squash a 150ms cycle into one 20ms step.
    gif = petpet(subject, overlay_gif, duration=0.5, speed=8.0, fps=50)

    assert gif.cycle_ms == MIN_DELAY_MS
    assert sum(frame_delays(gif.to_bytes())) == 500
