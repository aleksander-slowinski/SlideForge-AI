"""Planned SQL tracking tests: all use fakes, no real Google/SQL Server."""
from types import SimpleNamespace

import pytest
from pptx import Presentation as PptxPresentation

from models.planner_schemas import PresentationPlanSchema
from models.schemas import PresentationSchema
from services import planned_telemetry_service, telemetry_service
from services.planned_tracking_service import build_tracked_planned_artifact


def plan():
    return PresentationPlanSchema.model_validate({
        'topic': 'Business Intelligence i compliance',
        'presentation_type': 'academic', 'slides_count': 2,
        'sections': [{'section_number': 1, 'title': 'Wstęp', 'goal': 'Cel'}],
        'slides': [{
            'slide_number': i, 'section_number': 1,
            'title': f'Zagadnienie {i}', 'layout': 'title_content',
            'objective': 'Wyjaśnienie', 'content_brief': ['Definicja'],
        } for i in (1, 2)],
    })


def presentation(p):
    return PresentationSchema.model_validate({
        'title': 'Prezentacja testowa', 'topic': p.topic,
        'language': 'pl', 'slides_count': 2,
        'slides': [{
            'slide_number': i, 'title': f'Zagadnienie {i}',
            'layout': 'title_content', 'bullet_points': ['Treść testowa'],
        } for i in (1, 2)],
    })


def renderer(*, data, filename):
    prs = PptxPresentation()
    for _ in range(data.slides_count + 1):
        prs.slides.add_slide(prs.slide_layouts[6])
    prs.save(filename)


def report(_):
    return SimpleNamespace(score=100, warning_count=0, error_count=0)


class FakeGemini:
    def __init__(self, fail=False):
        self.models = self
        self.fail = fail
        self.calls = 0

    def generate_content(self, **kwargs):
        self.calls += 1
        if self.fail:
            raise RuntimeError('API 503')
        return SimpleNamespace(usage_metadata=SimpleNamespace(
            prompt_token_count=11, candidates_token_count=7,
            thoughts_token_count=3, total_token_count=21,
        ))


def setup_sql(monkeypatch, fail_start=False):
    calls = {'batches': [], 'finished': [], 'failed': [],
             'quality': [], 'metrics': [], 'counts': []}

    def start(**_):
        if fail_start:
            raise ConnectionError('SQL down')
        return 812

    monkeypatch.setattr(planned_telemetry_service, 'start_planned_run', start)
    monkeypatch.setattr(planned_telemetry_service, 'record_batch',
                        lambda **kw: calls['batches'].append(kw))
    monkeypatch.setattr(planned_telemetry_service, 'save_planned_counts',
                        lambda **kw: calls['counts'].append(kw))
    monkeypatch.setattr(telemetry_service, 'finish_generation',
                        lambda **kw: calls['finished'].append(kw))
    monkeypatch.setattr(telemetry_service, 'fail_generation',
                        lambda **kw: calls['failed'].append(kw))
    monkeypatch.setattr(telemetry_service, 'save_quality_report',
                        lambda **kw: calls['quality'].append(kw))
    monkeypatch.setattr(telemetry_service, 'save_run_metrics',
                        lambda **kw: calls['metrics'].append(kw))
    return calls


def test_success_records_actual_api_usage(monkeypatch, tmp_path):
    calls = setup_sql(monkeypatch)
    p = plan()
    fake = FakeGemini()

    def generator(*, client, on_batch_event, **_):
        on_batch_event({'kind': 'START', 'batch_index': 1,
                        'slide_from': 1, 'slide_to': 2, 'duration_ms': 0})
        client.models.generate_content(model='fake')
        on_batch_event({'kind': 'GENERATED', 'batch_index': 1,
                        'slide_from': 1, 'slide_to': 2, 'duration_ms': 20})
        return presentation(p)

    artifact = build_tracked_planned_artifact(
        p, output_dir=tmp_path / 'out', checkpoint_root=tmp_path / 'cp',
        client=fake, generate_fn=generator, render_fn=renderer, evaluate_fn=report,
    )
    assert len(artifact.pptx_data) > 500
    assert len(calls['finished']) == 1
    assert len(calls['quality']) == 1
    assert calls['batches'][0]['outcome'] == 'GENERATED'
    assert calls['batches'][0]['api_calls'] == 1
    assert calls['batches'][0]['total_tokens'] == 21
    assert calls['counts'][0]['api_call_count'] == 1
    assert calls['metrics'][0]['metrics'].total_tokens == 21


def test_checkpoint_is_not_api_call(monkeypatch, tmp_path):
    calls = setup_sql(monkeypatch)
    p = plan()
    fake = FakeGemini()

    def checkpoint_generator(*, on_batch_event, **_):
        on_batch_event({'kind': 'CHECKPOINT', 'batch_index': 1,
                        'slide_from': 1, 'slide_to': 2, 'duration_ms': 1})
        return presentation(p)

    build_tracked_planned_artifact(
        p, output_dir=tmp_path/'out', checkpoint_root=tmp_path/'cp',
        client=fake, generate_fn=checkpoint_generator,
        render_fn=renderer, evaluate_fn=report,
    )
    assert fake.calls == 0
    assert calls['batches'][0]['outcome'] == 'CHECKPOINT'
    assert calls['batches'][0]['api_calls'] == 0
    assert calls['counts'][0]['checkpoint_hit_count'] == 1
    assert calls['metrics'][0]['metrics'].total_tokens is None


def test_503_logs_failure_not_success(monkeypatch, tmp_path):
    calls = setup_sql(monkeypatch)
    p = plan()
    fake = FakeGemini(fail=True)

    def failing_generator(*, client, on_batch_event, **_):
        on_batch_event({'kind': 'START', 'batch_index': 1,
                        'slide_from': 1, 'slide_to': 2, 'duration_ms': 0})
        try:
            client.models.generate_content(model='fake')
        except RuntimeError:
            on_batch_event({'kind': 'FAILED', 'batch_index': 1,
                            'slide_from': 1, 'slide_to': 2,
                            'duration_ms': 4, 'http_status': 503})
            raise

    with pytest.raises(RuntimeError, match='503'):
        build_tracked_planned_artifact(
            p, output_dir=tmp_path/'out', checkpoint_root=tmp_path/'cp',
            client=fake, generate_fn=failing_generator,
            render_fn=renderer, evaluate_fn=report,
        )
    assert len(calls['failed']) == 1
    assert len(calls['finished']) == 0
    assert calls['batches'][0]['outcome'] == 'FAILED'
    assert calls['batches'][0]['api_calls'] == 1
    assert calls['counts'][0]['api_call_count'] == 1


def test_sql_down_does_not_block_pptx(monkeypatch, tmp_path):
    calls = setup_sql(monkeypatch, fail_start=True)
    p = plan()

    def generator(**_):
        return presentation(p)

    artifact = build_tracked_planned_artifact(
        p, output_dir=tmp_path/'out', checkpoint_root=tmp_path/'cp',
        generate_fn=generator, render_fn=renderer, evaluate_fn=report,
    )
    assert len(artifact.pptx_data) > 500
    assert calls['finished'] == []
